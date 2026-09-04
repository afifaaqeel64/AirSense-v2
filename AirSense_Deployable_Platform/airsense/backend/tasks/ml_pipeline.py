"""
ML Pipeline tasks — feature engineering, training, evaluation, promotion.
Can run standalone (Celery) or triggered by Airflow DAG.
"""
import asyncio, uuid, time
from datetime import datetime
from typing import Dict, Optional
import pandas as pd
import numpy as np
from tasks.celery_app import app
import structlog

log = structlog.get_logger()

def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def build_feature_matrix(raw_records: list) -> pd.DataFrame:
    """Convert raw DB records to ML feature matrix."""
    df = pd.DataFrame(raw_records)
    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").set_index("timestamp")

    # Fill gaps with forward fill then backfill
    for col in ["pm25","pm10","no2","so2","co","o3","aqi","temperature","humidity","wind_speed","wind_direction"]:
        if col in df.columns:
            df[col] = df[col].ffill().bfill()

    # Temporal features
    df["hour"]        = df.index.hour
    df["day_of_week"] = df.index.dayofweek
    df["month"]       = df.index.month
    df["is_weekend"]  = (df["day_of_week"] >= 5).astype(int)
    df["is_rush_hour"]= df["hour"].isin([7,8,9,17,18,19]).astype(int)
    df["is_burning_season"] = df["month"].isin([10,11]).astype(int)  # Crop burning
    df["hour_sin"]    = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"]    = np.cos(2 * np.pi * df["hour"] / 24)
    df["month_sin"]   = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"]   = np.cos(2 * np.pi * df["month"] / 12)

    # Lag features
    for col in ["pm25","pm10","no2","aqi"]:
        if col in df.columns:
            for lag in [1,2,3,6,12,24,48]:
                df[f"{col}_lag_{lag}h"] = df[col].shift(lag)
            for win in [3,6,12,24,48]:
                df[f"{col}_roll_mean_{win}h"] = df[col].rolling(win, min_periods=1).mean()
                df[f"{col}_roll_std_{win}h"]  = df[col].rolling(win, min_periods=1).std().fillna(0)

    # Wind cyclical
    if "wind_direction" in df.columns:
        df["wind_sin"] = np.sin(np.radians(df["wind_direction"]))
        df["wind_cos"] = np.cos(np.radians(df["wind_direction"]))

    # Derived features
    if "temperature" in df.columns and "pm25" in df.columns:
        df["temp_change_3h"]      = df["temperature"].diff(3).fillna(0)
        df["pm25_temp_interaction"]= df["pm25"] * df["temperature"]
    if "humidity" in df.columns and "pm25" in df.columns:
        df["pm25_humidity_ratio"] = df["pm25"] / (df["humidity"].clip(lower=1))
    if "wind_speed" in df.columns and "pm25" in df.columns:
        df["low_wind_high_pm"]    = ((df["wind_speed"] < 2) & (df["pm25"] > 100)).astype(int)

    # Drop rows with too many NaN
    df = df.dropna(thresh=int(len(df.columns) * 0.6))
    log.info("features_built", rows=len(df), cols=len(df.columns))
    return df

@app.task(name="tasks.ml_pipeline.run_full_pipeline")
def run_full_pipeline(city: str = "lahore"):
    """Orchestrate full retrain: features → train → evaluate → promote."""
    run_id = str(uuid.uuid4())
    log.info("pipeline_started", city=city, run_id=run_id)

    results = {}
    results["aqi"]      = _train_aqi_model(city, run_id)
    results["forecast"] = _train_forecast_model(city, run_id)
    results["health"]   = _train_health_model(city, run_id)
    results["anomaly"]  = _train_anomaly_model(city, run_id)

    log.info("pipeline_complete", city=city, results=results)
    return results

def _train_aqi_model(city: str, run_id: str) -> dict:
    """XGBoost AQI predictor — main prediction model."""
    import mlflow, mlflow.xgboost
    import xgboost as xgb
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment(f"aqi-predictor-{city}")

    records = _run_async(_get_training_data(city))
    if len(records) < 100:
        log.warning("insufficient_data", model="aqi", count=len(records))
        return {"status": "skipped", "reason": "insufficient_data"}

    df = build_feature_matrix(records)
    if df.empty:
        return {"status": "skipped", "reason": "empty_features"}

    EXCLUDE = ["aqi","aqi_category","city","station_id","source","pm25_flagged",
               "is_interpolated","data_quality_score"]
    feature_cols = [c for c in df.columns if c not in EXCLUDE and df[c].dtype in [np.float64, np.int64, float, int]]
    X = df[feature_cols].fillna(0)
    y = df["aqi"].fillna(method="ffill").dropna()
    X = X.loc[y.index]

    params = {
        "n_estimators": 500, "max_depth": 6, "learning_rate": 0.05,
        "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 3,
        "gamma": 0.1, "reg_alpha": 0.1, "reg_lambda": 1.0,
        "tree_method": "hist", "objective": "reg:squarederror",
    }

    tscv = TimeSeriesSplit(n_splits=5)
    cv_scores = []
    for train_idx, val_idx in tscv.split(X):
        model = xgb.XGBRegressor(**params, early_stopping_rounds=30, verbosity=0)
        model.fit(X.iloc[train_idx], y.iloc[train_idx],
                  eval_set=[(X.iloc[val_idx], y.iloc[val_idx])], verbose=False)
        preds = model.predict(X.iloc[val_idx])
        cv_scores.append({
            "rmse": float(np.sqrt(mean_squared_error(y.iloc[val_idx], preds))),
            "mae":  float(mean_absolute_error(y.iloc[val_idx], preds)),
            "r2":   float(r2_score(y.iloc[val_idx], preds)),
        })

    avg_rmse = np.mean([s["rmse"] for s in cv_scores])
    avg_mae  = np.mean([s["mae"]  for s in cv_scores])
    avg_r2   = np.mean([s["r2"]   for s in cv_scores])

    with mlflow.start_run(run_name=f"{city}-xgb-{run_id[:8]}") as run:
        mlflow.log_params(params)
        mlflow.log_metric("cv_rmse", avg_rmse)
        mlflow.log_metric("cv_mae",  avg_mae)
        mlflow.log_metric("cv_r2",   avg_r2)
        mlflow.log_metric("training_rows", len(X))
        mlflow.log_metric("feature_count", len(feature_cols))

        final_model = xgb.XGBRegressor(**params, verbosity=0)
        final_model.fit(X, y)

        model_info = mlflow.xgboost.log_model(
            final_model, artifact_path="model",
            registered_model_name=f"aqi-predictor-{city}"
        )

        result = {"status": "success", "run_id": run.info.run_id,
                  "rmse": avg_rmse, "mae": avg_mae, "r2": avg_r2,
                  "rows": len(X), "features": len(feature_cols)}
        _try_promote(f"aqi-predictor-{city}", run.info.run_id, avg_rmse, city)
        _record_training(run.info.run_id, f"aqi-predictor-{city}", city, result)
        return result

def _train_forecast_model(city: str, run_id: str) -> dict:
    """Gradient boosting multi-step forecaster (24h horizon)."""
    import mlflow
    from sklearn.multioutput import MultiOutputRegressor
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import mean_squared_error

    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment(f"forecaster-{city}")

    records = _run_async(_get_training_data(city, days=60))
    if len(records) < 200:
        return {"status": "skipped", "reason": "insufficient_data"}

    df = build_feature_matrix(records)
    if df.empty:
        return {"status": "skipped", "reason": "empty_features"}

    # Build multi-step targets: AQI at t+1, t+2, ..., t+24
    for h in range(1, 25):
        df[f"target_h{h}"] = df["aqi"].shift(-h)
    df = df.dropna()

    feature_cols = [c for c in df.columns if not c.startswith("target_") and
                    c not in ["aqi_category","city","station_id","source","aqi"] and
                    df[c].dtype in [np.float64, np.int64, float, int]]
    target_cols  = [f"target_h{h}" for h in range(1,25)]

    X = df[feature_cols].fillna(0)
    Y = df[target_cols]

    split = int(len(X) * 0.8)
    X_tr, X_val = X.iloc[:split], X.iloc[split:]
    Y_tr, Y_val = Y.iloc[:split], Y.iloc[split:]

    base = GradientBoostingRegressor(n_estimators=200, max_depth=4, learning_rate=0.05)
    model = MultiOutputRegressor(base, n_jobs=-1)
    model.fit(X_tr, Y_tr)

    preds = model.predict(X_val)
    rmse  = float(np.sqrt(mean_squared_error(Y_val, preds)))

    with mlflow.start_run(run_name=f"{city}-forecast-{run_id[:8]}") as run:
        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("training_rows", len(X_tr))
        import mlflow.sklearn
        mlflow.sklearn.log_model(model, "model",
                                  registered_model_name=f"forecaster-{city}")
        result = {"status": "success", "run_id": run.info.run_id, "rmse": rmse}
        _try_promote(f"forecaster-{city}", run.info.run_id, rmse, city)
        return result

def _train_health_model(city: str, run_id: str) -> dict:
    """Health risk classifier: Good/Moderate/Unhealthy/Hazardous."""
    import mlflow, mlflow.sklearn
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import LabelEncoder

    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment(f"health-risk-{city}")

    records = _run_async(_get_training_data(city))
    df = build_feature_matrix(records)
    if df.empty or "aqi" not in df.columns:
        return {"status": "skipped"}

    def aqi_to_risk(aqi):
        if aqi <=  50: return "Good"
        if aqi <= 100: return "Moderate"
        if aqi <= 150: return "Unhealthy_Sensitive"
        if aqi <= 200: return "Unhealthy"
        if aqi <= 300: return "Very_Unhealthy"
        return "Hazardous"

    df["risk_label"] = df["aqi"].apply(aqi_to_risk)
    le = LabelEncoder()
    y  = le.fit_transform(df["risk_label"])
    feature_cols = [c for c in df.columns if c not in ["aqi","aqi_category","risk_label",
                    "city","station_id","source"] and df[c].dtype in [np.float64,np.int64]]
    X = df[feature_cols].fillna(0)

    model = RandomForestClassifier(n_estimators=200, max_depth=10, n_jobs=-1, random_state=42)
    scores = cross_val_score(model, X, y, cv=3, scoring="accuracy")
    model.fit(X, y)
    acc = float(scores.mean())

    with mlflow.start_run(run_name=f"{city}-health-{run_id[:8]}") as run:
        mlflow.log_metric("accuracy", acc)
        mlflow.sklearn.log_model(model, "model",
                                  registered_model_name=f"health-risk-{city}")
        mlflow.log_dict(dict(enumerate(le.classes_)), "label_classes.json")
        return {"status": "success", "accuracy": acc}

def _train_anomaly_model(city: str, run_id: str) -> dict:
    """Isolation Forest anomaly detector."""
    import mlflow, mlflow.sklearn
    from sklearn.ensemble import IsolationForest

    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment(f"anomaly-{city}")

    records = _run_async(_get_training_data(city, days=30))
    df = build_feature_matrix(records)
    if df.empty:
        return {"status": "skipped"}

    feature_cols = ["pm25","pm10","no2","aqi","temperature","humidity","hour","month"]
    feature_cols = [c for c in feature_cols if c in df.columns]
    X = df[feature_cols].fillna(0)

    model = IsolationForest(contamination=0.05, n_estimators=100, random_state=42)
    model.fit(X)
    anomaly_rate = float((model.predict(X) == -1).mean())

    with mlflow.start_run(run_name=f"{city}-anomaly-{run_id[:8]}") as run:
        mlflow.log_metric("anomaly_rate", anomaly_rate)
        mlflow.sklearn.log_model(model, "model",
                                  registered_model_name=f"anomaly-{city}")
        _try_promote(f"anomaly-{city}", run.info.run_id, anomaly_rate, city)
        return {"status": "success", "anomaly_rate": anomaly_rate}

async def _get_training_data(city: str, days: int = 90) -> list:
    from app.db.timescale import get_measurements_for_training
    return await get_measurements_for_training(city=city, days=days)

def _try_promote(model_name: str, run_id: str, metric: float, city: str):
    """Promote model to Production if it improves over current production."""
    import mlflow
    try:
        client = mlflow.tracking.MlflowClient()
        versions = client.search_model_versions(f"name='{model_name}'")
        new_ver  = [v for v in versions if v.run_id == run_id]
        if not new_ver:
            return
        new_version = new_ver[0].version

        prod_versions = client.get_latest_versions(model_name, stages=["Production"])
        if prod_versions:
            prod_run = client.get_run(prod_versions[0].run_id)
            prod_metric = prod_run.data.metrics.get("cv_rmse") or prod_run.data.metrics.get("rmse", float("inf"))
            if metric >= prod_metric * (1 - 0.01):
                log.info("model_not_promoted", name=model_name, new=metric, prod=prod_metric)
                client.transition_model_version_stage(model_name, new_version, "Archived")
                return

        client.transition_model_version_stage(model_name, new_version, "Production",
                                               archive_existing_versions=True)
        from app.core.metrics import MODEL_RMSE, LAST_TRAIN_TS
        MODEL_RMSE.labels(model_name=model_name, city=city).set(metric)
        LAST_TRAIN_TS.labels(model_name=model_name, city=city).set(time.time())
        log.info("model_promoted", name=model_name, version=new_version, metric=metric)
    except Exception as e:
        log.error("promotion_failed", model=model_name, error=str(e))

def _record_training(run_id, model_name, city, result: dict):
    async def _insert():
        import asyncpg
        from app.core.config import settings
        conn = await asyncpg.connect(settings.DATABASE_URL.replace("postgresql+asyncpg://","postgresql://"))
        try:
            await conn.execute("""
                INSERT INTO ml_training_log
                    (run_id, model_name, city, cv_rmse, cv_mae, cv_r2,
                     training_rows, feature_count, status, completed_at, promoted)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,NOW(),$10)
                ON CONFLICT (run_id) DO NOTHING
            """, run_id, model_name, city,
                result.get("rmse"), result.get("mae"), result.get("r2"),
                result.get("rows"), result.get("features"),
                result.get("status","success"), result.get("status") == "success")
        finally:
            await conn.close()
    _run_async(_insert())

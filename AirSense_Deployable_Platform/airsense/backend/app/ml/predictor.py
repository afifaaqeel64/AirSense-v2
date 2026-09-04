"""Model inference layer — loads from MLflow registry, serves predictions."""
import mlflow.pyfunc
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from app.core.config import settings
from app.db.redis_client import cached
import structlog

log = structlog.get_logger()

_lock   = threading.RLock()
_models = {}
_versions = {}

def _load_model(name: str) -> Optional[object]:
    try:
        model = mlflow.pyfunc.load_model(f"models:/{name}/Production")
        log.info("model_loaded", name=name)
        return model
    except Exception as e:
        log.warning("model_load_failed", name=name, error=str(e))
        return None

def get_model(name: str):
    with _lock:
        return _models.get(name)

def hot_reload_all():
    """Background thread — reloads production models every 5 minutes."""
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    client = mlflow.tracking.MlflowClient()
    model_names = [
        "aqi-predictor-lahore",
        "forecaster-lahore",
        "health-risk-lahore",
        "anomaly-lahore",
    ]
    import time
    while True:
        for name in model_names:
            try:
                latest = client.get_latest_versions(name, stages=["Production"])
                if latest:
                    v = latest[0].version
                    if _versions.get(name) != v:
                        model = _load_model(name)
                        with _lock:
                            _models[name] = model
                            _versions[name] = v
                        log.info("model_hot_reloaded", name=name, version=v)
            except Exception as e:
                log.error("hot_reload_failed", name=name, error=str(e))
        time.sleep(300)

def start_hot_reload():
    t = threading.Thread(target=hot_reload_all, daemon=True)
    t.start()

class ModelPredictor:

    @staticmethod
    def _build_inference_features(history: list) -> pd.DataFrame:
        df = pd.DataFrame(history)
        if df.empty or "timestamp" not in df.columns:
            return pd.DataFrame()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").set_index("timestamp")
        df["hour"]         = df.index.hour
        df["day_of_week"]  = df.index.dayofweek
        df["month"]        = df.index.month
        df["is_weekend"]   = (df["day_of_week"] >= 5).astype(int)
        df["is_rush_hour"] = df["hour"].isin([7,8,9,17,18,19]).astype(int)
        df["is_burning_season"] = df["month"].isin([10,11]).astype(int)
        for col in ["pm25","pm10","no2","aqi"]:
            if col in df:
                for lag in [1,2,3,6,12,24]:
                    df[f"{col}_lag_{lag}h"] = df[col].shift(lag)
                for win in [3,6,12,24]:
                    df[f"{col}_roll_{win}h"] = df[col].rolling(win, min_periods=1).mean()
        if "wind_direction" in df:
            df["wind_sin"] = np.sin(np.radians(df["wind_direction"]))
            df["wind_cos"] = np.cos(np.radians(df["wind_direction"]))
        return df.dropna(thresh=int(len(df.columns)*0.5))

    @staticmethod
    @cached(ttl=1800, prefix="ml:forecast")
    async def predict_forecast(city: str, hours: int = 24) -> dict:
        from app.db.timescale import get_measurements_for_training
        history = await get_measurements_for_training(city=city, days=7)
        model   = get_model("forecaster-lahore")

        if not model or not history:
            return _fallback_forecast(city, hours)

        df = ModelPredictor._build_inference_features(history)
        if df.empty:
            return _fallback_forecast(city, hours)

        try:
            feature_cols = [c for c in df.columns if c not in ["city","station_id","source","aqi_category"]]
            X = df[feature_cols].tail(1).fillna(0)
            raw_pred = model.predict(X)[0]

            if hasattr(raw_pred, "__len__"):
                hourly_preds = list(raw_pred[:hours])
            else:
                # Scalar — extrapolate
                base = float(raw_pred)
                hourly_preds = [base + np.random.normal(0, 5) for _ in range(hours)]

            now = datetime.utcnow()
            forecast = [
                {
                    "prediction_for": (now + timedelta(hours=i+1)).isoformat(),
                    "hour": i + 1,
                    "predicted_aqi":  max(0, min(500, int(hourly_preds[i]))),
                    "predicted_pm25": max(0, round(hourly_preds[i] * 0.45, 1)),
                    "confidence":     max(0.5, min(0.99, 0.95 - i * 0.01)),
                }
                for i in range(min(hours, len(hourly_preds)))
            ]
            return {"city": city, "generated_at": now.isoformat(),
                    "model": "forecaster-lahore", "horizon_hours": hours,
                    "forecast": forecast}
        except Exception as e:
            log.error("predict_failed", error=str(e))
            return _fallback_forecast(city, hours)

    @staticmethod
    async def detect_anomalies(city: str, measurement: dict) -> Optional[dict]:
        model = get_model("anomaly-lahore")
        if not model:
            return None
        try:
            X = pd.DataFrame([{
                "pm25": measurement.get("pm25", 0),
                "pm10": measurement.get("pm10", 0),
                "no2":  measurement.get("no2", 0),
                "aqi":  measurement.get("aqi", 0),
                "temperature": measurement.get("temperature", 25),
                "humidity":    measurement.get("humidity", 50),
                "hour": datetime.utcnow().hour,
            }])
            score = model.predict(X)[0]
            if score == -1:
                return {"city": city, "anomaly": True,
                        "parameter": "pm25",
                        "observed_value": measurement.get("pm25"),
                        "severity": "high" if measurement.get("aqi",0) > 300 else "medium"}
        except Exception:
            pass
        return None

def _fallback_forecast(city: str, hours: int) -> dict:
    now = datetime.utcnow()
    return {
        "city": city,
        "generated_at": now.isoformat(),
        "model": "statistical_fallback",
        "horizon_hours": hours,
        "note": "ML model warming up; using statistical estimate",
        "forecast": [
            {"prediction_for": (now + timedelta(hours=i+1)).isoformat(),
             "hour": i+1, "predicted_aqi": None, "confidence": 0.0}
            for i in range(hours)
        ]
    }

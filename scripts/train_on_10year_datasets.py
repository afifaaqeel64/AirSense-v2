"""
AirSense Pakistan: Train & Benchmark ML Models on 10-Year Datasets (2015-2025).
Evaluates Regression, XGBoost, Random Forest, Gradient Boosting, and Isolation Forest
across 96,432 continuous hours per city (2015-2025).
"""

import os
import sys
import pandas as pd
import numpy as np

from pathlib import Path

AIRSENSE_ROOT = str(Path(__file__).resolve().parent.parent)
if AIRSENSE_ROOT not in sys.path:
    sys.path.insert(0, AIRSENSE_ROOT)

from ml.features.feature_pipeline import FeaturePipeline, CANONICAL_FEATURE_NAMES
from ml.targets.target_builder import TargetBuilder
from ml.models.estimators import get_model_instance
from ml.validation.walk_forward import calculate_metrics

DATA_DIR = os.path.join(AIRSENSE_ROOT, "data", "datasets")
MODELS_DIR = os.path.join(AIRSENSE_ROOT, "data", "models", "10year_models")
os.makedirs(MODELS_DIR, exist_ok=True)

CITIES = ["islamabad", "karachi", "lahore"]

def train_10year_benchmark(city_key: str, horizon: int = 1):
    csv_file = os.path.join(DATA_DIR, f"airsense_10year_{city_key}_2015_2025.csv")
    if not os.path.exists(csv_file):
        print(f"File not found: {csv_file}")
        return
        
    df_raw = pd.read_csv(csv_file)
    df_raw["hour_start"] = pd.to_datetime(df_raw["hour_start"])
    df_raw = df_raw.sort_values("hour_start").reset_index(drop=True)
    
    print(f"\n========================================================")
    print(f"10-YEAR CONTINUOUS BENCHMARK: {city_key.upper()} (2015-2025, HORIZON: +{horizon}h)")
    print(f"Total Continuous Hours: {len(df_raw):,}")
    print(f"Date Span: {df_raw['hour_start'].min()} to {df_raw['hour_start'].max()}")
    print(f"Mean PM2.5: {df_raw['pm2_5_mean'].mean():.2f} ug/m3 (Min: {df_raw['pm2_5_mean'].min():.1f}, Max: {df_raw['pm2_5_mean'].max():.1f})")
    print(f"========================================================")
    
    # Feature Engineering
    df_features = FeaturePipeline.compute_features(df_raw)
    df_dataset = TargetBuilder.attach_targets(df_features, df_raw, horizon=horizon)
    df_dataset = df_dataset.dropna(subset=["target_pm2_5"]).reset_index(drop=True)
    
    feature_cols = [c for c in CANONICAL_FEATURE_NAMES if c in df_dataset.columns]
    
    # Split: Train on 2015-2022 (approx 80%), Test on out-of-sample 2023-2025 (approx 20%)
    split_idx = int(len(df_dataset) * 0.75)
    train_df = df_dataset.iloc[:split_idx]
    test_df = df_dataset.iloc[split_idx:]
    
    X_train, y_train = train_df[feature_cols], train_df["target_pm2_5"]
    X_test, y_test = test_df[feature_cols], test_df["target_pm2_5"]
    
    print(f"Train samples (2015-2022): {len(X_train):,} ({train_df['hour_start'].min().date()} to {train_df['hour_start'].max().date()})")
    print(f"Test samples (2023-2025):  {len(X_test):,} ({test_df['hour_start'].min().date()} to {test_df['hour_start'].max().date()})")
    
    model_families = ["regression", "xgboost", "random_forest", "gradient_boosting", "isolation_forest"]
    results = []
    
    for family in model_families:
        try:
            model = get_model_instance(family, random_seed=42)
            model.fit(X_train, y_train)
            
            # Save artifact
            artifact_path = os.path.join(MODELS_DIR, f"10yr_{city_key}_{family}_h{horizon}.joblib")
            model.save(artifact_path)
            
            preds_train = model.predict(X_train)
            preds_test = model.predict(X_test)
            
            if family == "isolation_forest":
                anomaly_labels_test = model.predict_anomaly_labels(X_test)
                anomaly_count = (anomaly_labels_test == -1).sum()
                anomaly_pct = (anomaly_count / len(X_test)) * 100.0
                results.append({
                    "Model Family": model.name,
                    "Train R2": "N/A (Unsupervised)",
                    "Train RMSE": "N/A",
                    "Train MAE": "N/A",
                    "Test R2": f"Anomalies: {anomaly_pct:.1f}%",
                    "Test RMSE": f"{anomaly_count} Outliers",
                    "Test MAE": f"Contam: {model.contamination:.2f}",
                    "Test MAPE": "Outlier Detection"
                })
            else:
                m_train = calculate_metrics(y_train.to_numpy(), preds_train)
                m_test = calculate_metrics(y_test.to_numpy(), preds_test)
                
                results.append({
                    "Model Family": model.name,
                    "Train R2": f"{m_train.get('r2', 0.0):.4f}",
                    "Train RMSE": f"{m_train.get('rmse', 0.0):.2f}",
                    "Train MAE": f"{m_train.get('mae', 0.0):.2f}",
                    "Test R2": f"{m_test.get('r2', 0.0):.4f}",
                    "Test RMSE": f"{m_test.get('rmse', 0.0):.2f}",
                    "Test MAE": f"{m_test.get('mae', 0.0):.2f}",
                    "Test MAPE": f"{m_test.get('mape', 0.0):.2f}%"
                })
        except Exception as e:
            print(f"Error training {family}: {e}")
            
    df_res = pd.DataFrame(results)
    print("\n" + df_res.to_string(index=False))

if __name__ == "__main__":
    for c in CITIES:
        train_10year_benchmark(c, horizon=1)

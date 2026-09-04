"""
AirSense Pakistan — Train and Benchmark ML Models on Actual Ground-Truth Station Datasets.
Trains the ML model suite on real regulatory-grade BAM-1020 ground monitoring station
records (Islamabad, Karachi, Lahore) from 2019 to 2025.
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
MODELS_DIR = os.path.join(AIRSENSE_ROOT, "data", "models", "actual_ground_truth")
os.makedirs(MODELS_DIR, exist_ok=True)

CITIES = ["islamabad", "karachi", "lahore"]

def train_city_ground_truth(city_key: str, horizon: int = 1):
    csv_file = os.path.join(DATA_DIR, f"actual_ground_truth_{city_key}_pm25_weather.csv")
    if not os.path.exists(csv_file):
        print(f"File not found: {csv_file}")
        return
        
    df_raw = pd.read_csv(csv_file)
    df_raw["hour_start"] = pd.to_datetime(df_raw["hour_start"])
    df_raw = df_raw.sort_values("hour_start").reset_index(drop=True)
    
    print(f"\n========================================================")
    print(f"TRAINING ON ACTUAL GROUND-TRUTH SENSOR: {city_key.upper()} (HORIZON: +{horizon}h)")
    print(f"Station: {df_raw['station_name'].iloc[0]}")
    print(f"Observation Period: {df_raw['hour_start'].min()} to {df_raw['hour_start'].max()}")
    print(f"Total Valid Hours: {len(df_raw):,}")
    print(f"Mean Ground PM2.5: {df_raw['pm2_5_mean'].mean():.2f} ug/m3 (Min: {df_raw['pm2_5_mean'].min():.1f}, Max: {df_raw['pm2_5_mean'].max():.1f})")
    print(f"========================================================")
    
    # Feature Engineering
    df_features = FeaturePipeline.compute_features(df_raw)
    df_dataset = TargetBuilder.attach_targets(df_features, df_raw, horizon=horizon)
    df_dataset = df_dataset.dropna(subset=["target_pm2_5"]).reset_index(drop=True)
    
    feature_cols = [c for c in CANONICAL_FEATURE_NAMES if c in df_dataset.columns]
    
    # Split 80% Train, 20% Test chronologically
    split_idx = int(len(df_dataset) * 0.8)
    train_df = df_dataset.iloc[:split_idx]
    test_df = df_dataset.iloc[split_idx:]
    
    X_train, y_train = train_df[feature_cols], train_df["target_pm2_5"]
    X_test, y_test = test_df[feature_cols], test_df["target_pm2_5"]
    
    print(f"Train samples: {len(X_train):,} ({train_df['hour_start'].min().date()} to {train_df['hour_start'].max().date()})")
    print(f"Test samples:  {len(X_test):,} ({test_df['hour_start'].min().date()} to {test_df['hour_start'].max().date()})")
    
    model_families = ["regression", "xgboost", "random_forest", "gradient_boosting", "isolation_forest"]
    results = []
    
    for family in model_families:
        try:
            model = get_model_instance(family, random_seed=42)
            model.fit(X_train, y_train)
            
            # Save artifact
            artifact_path = os.path.join(MODELS_DIR, f"actual_{city_key}_{family}_h{horizon}.joblib")
            model.save(artifact_path)
            
            preds_train = model.predict(X_train)
            preds_test = model.predict(X_test)
            
            if family == "isolation_forest":
                # Anomaly detection evaluation
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
    
    # Top meteorological feature correlations
    print(f"\n--- Physical Meteorological Drivers of PM2.5 in {city_key.upper()} ---")
    corr = df_dataset[feature_cols + ["target_pm2_5"]].corr()["target_pm2_5"].drop("target_pm2_5")
    print(corr.abs().sort_values(ascending=False).head(12).to_string())

if __name__ == "__main__":
    for c in CITIES:
        train_city_ground_truth(c, horizon=1)

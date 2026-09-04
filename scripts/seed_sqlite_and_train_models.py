"""
AirSense Pakistan — Seed SQLite Database and Train ML Model Suite.
Loads the fetched PM2.5 + meteorological dataset into SQLite,
runs feature engineering, and trains/evaluates the ML models.
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import uuid

from pathlib import Path

# Add AirSense root to path dynamically for portability
AIRSENSE_ROOT = str(Path(__file__).resolve().parent.parent)
if AIRSENSE_ROOT not in sys.path:
    sys.path.insert(0, AIRSENSE_ROOT)

from ml.features.feature_pipeline import FeaturePipeline, CANONICAL_FEATURE_NAMES
from ml.targets.target_builder import TargetBuilder
from ml.models.estimators import get_model_instance
from ml.validation.walk_forward import WalkForwardSplitter, calculate_metrics

DB_PATH = os.path.join(AIRSENSE_ROOT, "data", "airsense.db")
DATASET_CSV = os.path.join(AIRSENSE_ROOT, "data", "datasets", "pakistan_multicity_pm25_meteorological_combined.csv")
MODELS_DIR = os.path.join(AIRSENSE_ROOT, "data", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

def seed_sqlite_database():
    print(f"Connecting to SQLite DB at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Ensure campuses exist
    campuses_data = [
        ("58f9526c-ec0a-40da-9908-4407cf557870", "ISB_CAMPUS", "Islamabad Campus", "Islamabad", "Pakistan", 33.6844, 73.0479, "Asia/Karachi", "active", "verified", "Munim Qureshi", str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc))),
        ("3dd29b2e-98cc-4328-a28f-28e994b7c2a4", "KHI_CAMPUS", "Karachi Campus", "Karachi", "Pakistan", 24.8607, 67.0011, "Asia/Karachi", "active", "verified", "Areesha Aqeel", str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc))),
        ("1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "LHR_CAMPUS", "Lahore Smog Center", "Lahore", "Pakistan", 31.5204, 74.3587, "Asia/Karachi", "active", "verified", "AirSense Central", str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc)))
    ]
    cur.executemany("""
        INSERT OR REPLACE INTO campuses (id, code, name, city, country, latitude, longitude, timezone, status, location_status, contact_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, campuses_data)
    
    # 2. Ensure stations exist
    stations_data = [
        ("stn_isb_01", "58f9526c-ec0a-40da-9908-4407cf557870", "ISB-CAMPUS-01", "Islamabad BIC Rooftop Station", "Main Academic Block Rooftop", 33.6844, 73.0479, 540.0, str(datetime.now(timezone.utc)), "active", 60, "1.0.0", str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc))),
        ("stn_khi_01", "3dd29b2e-98cc-4328-a28f-28e994b7c2a4", "KHI-CAMPUS-01", "Karachi BIC Rooftop Station", "Campus Administration Rooftop", 24.8607, 67.0011, 20.0, str(datetime.now(timezone.utc)), "active", 60, "1.0.0", str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc))),
        ("stn_lhr_01", "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "LHR-SMOG-01", "Lahore Urban Air Monitoring Station", "Urban Core Rooftop", 31.5204, 74.3587, 217.0, str(datetime.now(timezone.utc)), "active", 60, "1.0.0", str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc)), str(datetime.now(timezone.utc)))
    ]
    cur.executemany("""
        INSERT OR REPLACE INTO stations (id, campus_id, station_code, station_name, installation_location, latitude, longitude, elevation_m, installation_date, status, sampling_interval_seconds, firmware_version, last_seen_at, monitoring_started_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, stations_data)
    
    conn.commit()
    print("Campuses and Stations initialized.")
    
    # 3. Load Hourly Observations from CSV
    if not os.path.exists(DATASET_CSV):
        print(f"Dataset CSV not found at {DATASET_CSV}. Please run fetch script first.")
        conn.close()
        return
        
    df = pd.read_csv(DATASET_CSV)
    print(f"Loaded {len(df)} rows from {DATASET_CSV}")
    
    station_map = {
        "ISB_CAMPUS": ("58f9526c-ec0a-40da-9908-4407cf557870", "stn_isb_01"),
        "KHI_CAMPUS": ("3dd29b2e-98cc-4328-a28f-28e994b7c2a4", "stn_khi_01"),
        "LHR_CAMPUS": ("1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "stn_lhr_01")
    }
    
    records_to_insert = []
    now_str = str(datetime.now(timezone.utc))
    
    for idx, row in df.iterrows():
        camp_code = row.get("campus_code", "ISB_CAMPUS")
        camp_id, stn_id = station_map.get(camp_code, station_map["ISB_CAMPUS"])
        obs_id = f"obs_{camp_code.lower()}_{idx}"
        
        records_to_insert.append((
            obs_id,
            camp_id,
            stn_id,
            "cams_era5_reanalysis",
            str(row["hour_start"]),
            float(row.get("pm1_mean", 0.0)) if pd.notna(row.get("pm1_mean")) else None,
            float(row.get("pm2_5_mean", 0.0)) if pd.notna(row.get("pm2_5_mean")) else None,
            float(row.get("pm2_5_median", 0.0)) if pd.notna(row.get("pm2_5_median")) else None,
            float(row.get("pm10_mean", 0.0)) if pd.notna(row.get("pm10_mean")) else None,
            float(row.get("pm10_median", 0.0)) if pd.notna(row.get("pm10_median")) else None,
            float(row.get("temperature_mean", 0.0)) if pd.notna(row.get("temperature_mean")) else None,
            float(row.get("humidity_mean", 0.0)) if pd.notna(row.get("humidity_mean")) else None,
            float(row.get("pressure_mean", 0.0)) if pd.notna(row.get("pressure_mean")) else None,
            bool(row.get("rain_detected", 0)),
            float(row.get("rain_fraction", 0.0)),
            float(row.get("wind_speed_mean", 0.0)) if pd.notna(row.get("wind_speed_mean")) else None,
            float(row.get("wind_direction_circular_mean", 0.0)) if pd.notna(row.get("wind_direction_circular_mean")) else None,
            60,
            60,
            100.0,
            1.0,
            float(row.get("high_humidity_fraction", 0.0)),
            bool(row.get("has_interpolation", 0)),
            bool(row.get("is_model_eligible", 1)),
            "cams_era5_hourly_gold",
            "1.0.0",
            now_str,
            now_str,
            now_str
        ))
        
    cur.execute("DELETE FROM hourly_observations")
    cur.executemany("""
        INSERT INTO hourly_observations (
            id, campus_id, station_id, source, hour_start,
            pm1_mean, pm2_5_mean, pm2_5_median, pm10_mean, pm10_median,
            temperature_mean, humidity_mean, pressure_mean,
            rain_detected, rain_fraction, wind_speed_mean, wind_direction_circular_mean,
            contributing_count, expected_count, completeness_pct, average_quality_score,
            high_humidity_fraction, has_interpolation, is_model_eligible,
            eligibility_reason, aggregation_version, generated_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records_to_insert)
    
    conn.commit()
    print(f"Successfully seeded {len(records_to_insert)} hourly observations into airsense.db")
    conn.close()

def train_and_evaluate_city_models(city_key: str = "islamabad", horizon: int = 1):
    print(f"\n========================================================")
    print(f"TRAINING AIRSENSE ML SUITE — CITY: {city_key.upper()} (HORIZON: +{horizon}h)")
    print(f"========================================================")
    
    city_csv = os.path.join(DATASET_CSV if city_key == "combined" else os.path.join(AIRSENSE_ROOT, f"data/datasets/{city_key}_pm25_meteorological_hourly_2023_2026.csv"))
    df_raw = pd.read_csv(city_csv)
    df_raw["hour_start"] = pd.to_datetime(df_raw["hour_start"], utc=True)
    df_raw = df_raw.sort_values("hour_start").reset_index(drop=True)
    
    # 1. Feature Engineering
    print("Computing feature pipeline...")
    df_features = FeaturePipeline.compute_features(df_raw)
    df_dataset = TargetBuilder.attach_targets(df_features, df_raw, horizon=horizon)
    df_dataset = df_dataset.dropna(subset=["target_pm2_5"]).reset_index(drop=True)
    
    feature_cols = [c for c in CANONICAL_FEATURE_NAMES if c in df_dataset.columns]
    print(f"Total dataset samples: {len(df_dataset)}, Feature count: {len(feature_cols)}")
    print(f"Features: {feature_cols}")
    
    # Train / Test split (80% chronological train, 20% test)
    split_idx = int(len(df_dataset) * 0.8)
    train_df = df_dataset.iloc[:split_idx]
    test_df = df_dataset.iloc[split_idx:]
    
    X_train, y_train = train_df[feature_cols], train_df["target_pm2_5"]
    X_test, y_test = test_df[feature_cols], test_df["target_pm2_5"]
    
    print(f"Train samples: {len(X_train)} ({train_df['hour_start'].min()} to {train_df['hour_start'].max()})")
    print(f"Test samples:  {len(X_test)} ({test_df['hour_start'].min()} to {test_df['hour_start'].max()})")
    
    model_families = ["persistence", "slr", "mlr", "decision_tree", "random_forest"]
    
    # Check optional packages
    try:
        import xgboost
        model_families.append("xgboost")
    except ImportError:
        pass
        
    try:
        import lightgbm
        model_families.append("lightgbm")
    except ImportError:
        pass
        
    results = []
    
    for family in model_families:
        try:
            model = get_model_instance(family, random_seed=42)
            model.fit(X_train, y_train)
            
            # Save artifact
            artifact_path = os.path.join(MODELS_DIR, f"{city_key}_{family}_h{horizon}.joblib")
            model.save(artifact_path)
            
            preds_train = model.predict(X_train)
            preds_test = model.predict(X_test)
            
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
    
    # Feature correlations with PM2.5
    print(f"\n--- Top Feature Correlations with PM2.5 ({city_key.upper()}) ---")
    corr = df_dataset[feature_cols + ["target_pm2_5"]].corr()["target_pm2_5"].drop("target_pm2_5")
    print(corr.abs().sort_values(ascending=False).head(15).to_string())
    
    return df_res

if __name__ == "__main__":
    seed_sqlite_database()
    train_and_evaluate_city_models("islamabad", horizon=1)
    train_and_evaluate_city_models("karachi", horizon=1)
    train_and_evaluate_city_models("lahore", horizon=1)

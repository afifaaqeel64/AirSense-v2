"""AirSense Pakistan Feature Engineering Pipeline."""

import hashlib
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

FEATURE_VERSION = "1.0.0"

CANONICAL_FEATURE_NAMES = [
    "pm2_5_lag_1", "pm2_5_lag_2", "pm2_5_lag_3", "pm2_5_lag_6", "pm2_5_lag_12", "pm2_5_lag_24",
    "pm10_lag_1", "pm10_lag_2", "pm10_lag_3", "pm10_lag_6", "pm10_lag_12", "pm10_lag_24",
    "pm2_5_roll_3h_mean", "pm2_5_roll_6h_mean", "pm2_5_roll_3h_std", "pm2_5_roll_6h_std",
    "pm10_roll_3h_mean", "pm10_roll_6h_mean",
    "hour_of_day", "day_of_week", "is_weekend", "month", "is_morning_peak", "is_evening_peak",
    "temperature_c", "humidity_pct", "pressure_hpa", "rain_flag",
    "wind_speed_m_s", "wind_dir_sin", "wind_dir_cos",
    "quality_score", "high_humidity_fraction", "has_interpolation", "completeness_pct"
]


class FeaturePipeline:
    @classmethod
    def compute_features(cls, df_hourly: pd.DataFrame) -> pd.DataFrame:
        """Transforms a chronologically sorted hourly observations DataFrame into past-only feature vectors."""
        if df_hourly.empty:
            return pd.DataFrame(columns=["hour_start"] + CANONICAL_FEATURE_NAMES)

        df = df_hourly.sort_values("hour_start").copy()

        # PM2.5 Lags
        for lag in [1, 2, 3, 6, 12, 24]:
            df[f"pm2_5_lag_{lag}"] = df["pm2_5_mean"].shift(lag)
            df[f"pm10_lag_{lag}"] = df["pm10_mean"].shift(lag)

        # Past-only Rolling Statistics (min_periods=1)
        df["pm2_5_roll_3h_mean"] = df["pm2_5_mean"].shift(1).rolling(window=3, min_periods=1).mean()
        df["pm2_5_roll_6h_mean"] = df["pm2_5_mean"].shift(1).rolling(window=6, min_periods=1).mean()
        df["pm2_5_roll_3h_std"] = df["pm2_5_mean"].shift(1).rolling(window=3, min_periods=1).std().fillna(0.0)
        df["pm2_5_roll_6h_std"] = df["pm2_5_mean"].shift(1).rolling(window=6, min_periods=1).std().fillna(0.0)

        df["pm10_roll_3h_mean"] = df["pm10_mean"].shift(1).rolling(window=3, min_periods=1).mean()
        df["pm10_roll_6h_mean"] = df["pm10_mean"].shift(1).rolling(window=6, min_periods=1).mean()

        # Temporal Features
        ts = pd.to_datetime(df["hour_start"], utc=True)
        df["hour_of_day"] = ts.dt.hour
        df["day_of_week"] = ts.dt.dayofweek
        df["is_weekend"] = ts.dt.dayofweek.isin([5, 6]).astype(int)
        df["month"] = ts.dt.month
        df["is_morning_peak"] = ts.dt.hour.isin([7, 8, 9]).astype(int)
        df["is_evening_peak"] = ts.dt.hour.isin([17, 18, 19, 20]).astype(int)

        # Meteorological & Directional Trigonometry
        df["temperature_c"] = df["temperature_mean"].fillna(25.0) if "temperature_mean" in df.columns else 25.0
        df["humidity_pct"] = df["humidity_mean"].fillna(50.0) if "humidity_mean" in df.columns else 50.0
        df["pressure_hpa"] = df["pressure_mean"].fillna(1013.25) if "pressure_mean" in df.columns else 1013.25
        df["rain_flag"] = df["rain_detected"].fillna(False).astype(int) if "rain_detected" in df.columns else 0
        df["wind_speed_m_s"] = df["wind_speed_mean"].fillna(1.0) if "wind_speed_mean" in df.columns else 1.0

        wind_deg = df["wind_direction_circular_mean"].fillna(0.0) if "wind_direction_circular_mean" in df.columns else 0.0
        rad = np.radians(wind_deg)
        df["wind_dir_sin"] = np.sin(rad)
        df["wind_dir_cos"] = np.cos(rad)

        # Quality & Availability
        df["quality_score"] = df["average_quality_score"].fillna(1.0) if "average_quality_score" in df.columns else 1.0
        df["high_humidity_fraction"] = df["high_humidity_fraction"].fillna(0.0) if "high_humidity_fraction" in df.columns else 0.0
        df["has_interpolation"] = df["has_interpolation"].fillna(False).astype(int) if "has_interpolation" in df.columns else 0
        df["completeness_pct"] = df["completeness_pct"].fillna(100.0) if "completeness_pct" in df.columns else 100.0

        cols = ["hour_start", "campus_id", "station_id"] + CANONICAL_FEATURE_NAMES
        available_cols = [c for c in cols if c in df.columns]
        return df[available_cols]

    @classmethod
    def compute_dataset_fingerprint(cls, df_features: pd.DataFrame, horizon: int, scope: str) -> str:
        """Computes a SHA-256 fingerprint for dataset reproducibility."""
        summary = {
            "feature_version": FEATURE_VERSION,
            "horizon": horizon,
            "scope": scope,
            "rows": len(df_features),
            "columns": list(df_features.columns),
            "first_timestamp": str(df_features["hour_start"].min()) if not df_features.empty else None,
            "last_timestamp": str(df_features["hour_start"].max()) if not df_features.empty else None
        }
        return hashlib.sha256(json.dumps(summary, sort_keys=True).encode("utf-8")).hexdigest()

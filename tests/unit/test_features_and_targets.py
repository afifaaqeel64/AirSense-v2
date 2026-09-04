"""Unit tests for Feature Engineering Pipeline and Target Builder."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from ml.features.feature_pipeline import FeaturePipeline, CANONICAL_FEATURE_NAMES
from ml.targets.target_builder import TargetBuilder


def create_sample_hourly_df(n_rows: int = 48) -> pd.DataFrame:
    base_ts = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
    records = []
    for i in range(n_rows):
        ts = base_ts + timedelta(hours=i)
        records.append({
            "hour_start": ts,
            "pm1_mean": 15.0 + (i % 5),
            "pm2_5_mean": 30.0 + (i % 10),
            "pm10_mean": 45.0 + (i % 15),
            "temperature_mean": 25.0 + (i % 3),
            "humidity_mean": 50.0 + (i % 4),
            "pressure_mean": 1013.25,
            "rain_detected": False,
            "wind_speed_mean": 2.0,
            "wind_direction_circular_mean": 90.0,
            "average_quality_score": 1.0,
            "high_humidity_fraction": 0.0,
            "has_interpolation": False,
            "completeness_pct": 100.0,
            "is_model_eligible": True
        })
    return pd.DataFrame(records)


def test_feature_pipeline_canonical_columns():
    df_raw = create_sample_hourly_df(48)
    df_features = FeaturePipeline.compute_features(df_raw)
    for col in CANONICAL_FEATURE_NAMES:
        assert col in df_features.columns


def test_feature_pipeline_past_only_shift():
    df_raw = create_sample_hourly_df(48)
    df_features = FeaturePipeline.compute_features(df_raw)

    # pm2_5_lag_1 at row index 1 should equal pm2_5_mean at raw index 0
    assert df_features["pm2_5_lag_1"].iloc[1] == df_raw["pm2_5_mean"].iloc[0]
    # pm2_5_lag_1 at row index 0 should be NaN
    assert pd.isna(df_features["pm2_5_lag_1"].iloc[0])


def test_target_builder_horizons():
    df_raw = create_sample_hourly_df(48)
    df_features = FeaturePipeline.compute_features(df_raw)
    df_dataset = TargetBuilder.attach_targets(df_features, df_raw, horizon=1)

    assert "target_pm2_5" in df_dataset.columns
    # Row 0 target_pm2_5 (horizon=1) should equal raw row 1 pm2_5_mean
    assert df_dataset["target_pm2_5"].iloc[0] == df_raw["pm2_5_mean"].iloc[1]

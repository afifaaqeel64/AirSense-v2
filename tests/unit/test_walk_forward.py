"""Unit tests for Chronological Walk-Forward Validation Engine and Metrics."""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from ml.validation.walk_forward import WalkForwardSplitter, calculate_metrics


def test_metrics_calculation_perfect_prediction():
    y_true = np.array([30.0, 45.0, 80.0, 15.0])
    y_pred = np.array([30.0, 45.0, 80.0, 15.0])
    m = calculate_metrics(y_true, y_pred)
    assert m["mae"] == 0.0
    assert m["rmse"] == 0.0
    assert m["r2"] == 1.0
    assert m["exceedance_f1"] == 1.0


def test_metrics_calculation_imperfect_prediction():
    y_true = np.array([30.0, 50.0, 80.0, 10.0])
    y_pred = np.array([32.0, 48.0, 75.0, 12.0])
    m = calculate_metrics(y_true, y_pred)
    assert m["mae"] > 0.0
    assert m["rmse"] >= m["mae"]


def test_walk_forward_splitter_chronological():
    base_ts = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
    records = [{"feature_timestamp": base_ts + timedelta(hours=i)} for i in range(100)]
    df = pd.DataFrame(records)

    splitter = WalkForwardSplitter(min_train_rows=30, val_window_rows=10, step_rows=10, max_folds=3)
    folds = list(splitter.split(df))

    assert len(folds) == 3
    for fold_num, train_df, val_df in folds:
        train_max_ts = train_df["feature_timestamp"].max()
        val_min_ts = val_df["feature_timestamp"].min()
        # Strict chronological non-overlap assertion
        assert train_max_ts < val_min_ts

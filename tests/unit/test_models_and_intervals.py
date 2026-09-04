"""Unit tests for Model Suite, Residual Bootstrap Prediction Intervals, and Explainability."""

import pytest
import numpy as np
import pandas as pd
from ml.models.estimators import PersistenceModel, MultipleLinearRegressionModel, RandomForestModel
from ml.intervals.bootstrap_intervals import ResidualBootstrapIntervals
from ml.explainability.explainer import AirSenseExplainer


def test_persistence_model_predict():
    X = pd.DataFrame({"pm2_5_lag_1": [25.0, 40.0, 55.0]})
    y = pd.Series([28.0, 42.0, 50.0])
    model = PersistenceModel()
    model.fit(X, y)
    preds = model.predict(X)
    assert np.array_equal(preds, np.array([25.0, 40.0, 55.0]))


def test_random_forest_model_fit_predict():
    X = pd.DataFrame({
        "pm2_5_lag_1": np.random.uniform(10, 80, 50),
        "temperature_c": np.random.uniform(20, 35, 50),
        "humidity_pct": np.random.uniform(30, 80, 50)
    })
    y = pd.Series(X["pm2_5_lag_1"] * 0.9 + np.random.normal(0, 2, 50))
    model = RandomForestModel(random_seed=42)
    model.fit(X, y)
    preds = model.predict(X)
    assert len(preds) == 50
    assert np.all(preds >= 0.0)


def test_residual_bootstrap_intervals_non_negative():
    point_preds = np.array([5.0, 15.0, 50.0])
    residuals = np.array([-10.0, 5.0, -3.0, 2.0, -8.0, 4.0])
    ci_low, ci_high, info = ResidualBootstrapIntervals.calculate_intervals(point_preds, residuals, confidence=0.90)

    assert len(ci_low) == 3
    assert len(ci_high) == 3
    # Enforce lower bound non-negativity clamp
    assert np.all(ci_low >= 0.0)
    assert np.all(ci_high >= ci_low)


def test_explainability_local_attribution():
    row = pd.Series({"pm2_5_lag_1": 45.0, "temperature_c": 28.0, "humidity_pct": 55.0})
    model = PersistenceModel()
    model.fit(pd.DataFrame([row]), pd.Series([45.0]))
    explanations = AirSenseExplainer.explain_local(model, row)
    assert len(explanations) > 0
    assert "feature_name" in explanations[0]
    assert "contribution_value" in explanations[0]

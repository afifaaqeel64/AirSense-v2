"""Unit tests for versioned Quality Control Engine rules, physical limits, and scoring."""

import pytest
from datetime import datetime, timezone
from services.quality_control.qc_engine import QualityControlEngine
from services.quality_control.gap_and_aggregation import calculate_circular_wind_mean


def test_qc_perfect_reading():
    reading = {
        "observed_at": datetime.now(timezone.utc),
        "pm1": 15.0,
        "pm2_5": 30.0,
        "pm10": 45.0,
        "temperature_c": 25.0,
        "humidity_pct": 50.0,
        "pressure_hpa": 1013.25
    }
    res = QualityControlEngine.evaluate_reading(reading)
    assert res.quality_score == 1.0
    assert res.quality_status == "accepted"
    assert res.impossible_value_flag is False


def test_qc_particulate_order_violation():
    # PM1 > PM2.5 violation
    reading = {
        "observed_at": datetime.now(timezone.utc),
        "pm1": 50.0,
        "pm2_5": 30.0,
        "pm10": 45.0,
        "temperature_c": 25.0,
        "humidity_pct": 50.0
    }
    res = QualityControlEngine.evaluate_reading(reading)
    assert res.ordering_consistency_flag is True
    assert res.quality_score < 1.0
    assert any("ordering violation" in msg for msg in res.validation_messages)


def test_qc_high_humidity_handling():
    # Relative humidity > 90%
    reading = {
        "observed_at": datetime.now(timezone.utc),
        "pm1": 10.0,
        "pm2_5": 20.0,
        "pm10": 30.0,
        "temperature_c": 22.0,
        "humidity_pct": 95.0
    }
    res = QualityControlEngine.evaluate_reading(reading)
    assert res.high_humidity_flag is True
    assert res.quality_score == 0.85
    assert res.quality_status == "accepted_with_warning"


def test_qc_impossible_value():
    # PM2.5 negative
    reading = {
        "observed_at": datetime.now(timezone.utc),
        "pm2_5": -10.0,
        "temperature_c": 25.0
    }
    res = QualityControlEngine.evaluate_reading(reading)
    assert res.impossible_value_flag is True
    assert res.quality_status == "rejected"


def test_circular_wind_mean_north_wrap_around():
    """Verify that wrap-around around 0/360 degrees yields 0.0 instead of 360.0."""
    assert calculate_circular_wind_mean([359.0, 1.0]) == 0.0
    assert calculate_circular_wind_mean([350.0, 10.0]) == 0.0
    assert calculate_circular_wind_mean([355.0, 5.0]) == 0.0


def test_circular_wind_mean_opposing_vectors():
    """Verify that canceling / diametrically opposed vectors resolve safely to 0.0."""
    assert calculate_circular_wind_mean([0.0, 180.0]) == 0.0
    assert calculate_circular_wind_mean([90.0, 270.0]) == 0.0
    assert calculate_circular_wind_mean([0.0, 90.0, 180.0, 270.0]) == 0.0


def test_circular_wind_mean_cardinal_directions():
    """Verify cardinal direction averages."""
    assert calculate_circular_wind_mean([0.0, 0.0]) == 0.0
    assert calculate_circular_wind_mean([90.0, 90.0]) == 90.0
    assert calculate_circular_wind_mean([180.0, 180.0]) == 180.0
    assert calculate_circular_wind_mean([270.0, 270.0]) == 270.0


def test_circular_wind_mean_quadrants():
    """Verify quadrant midpoints and near-cardinal angles."""
    assert calculate_circular_wind_mean([0.0, 90.0]) == 45.0
    assert calculate_circular_wind_mean([90.0, 180.0]) == 135.0
    assert calculate_circular_wind_mean([180.0, 270.0]) == 225.0
    assert calculate_circular_wind_mean([270.0, 360.0]) == 315.0
    assert calculate_circular_wind_mean([89.0, 91.0]) == 90.0
    assert calculate_circular_wind_mean([179.0, 181.0]) == 180.0
    assert calculate_circular_wind_mean([269.0, 271.0]) == 270.0


def test_circular_wind_mean_empty_and_nan():
    """Verify empty and NaN/None sequence handling returns None."""
    assert calculate_circular_wind_mean([]) is None
    assert calculate_circular_wind_mean([None]) is None
    assert calculate_circular_wind_mean([float("nan")]) is None
    assert calculate_circular_wind_mean([None, float("nan")]) is None
    assert calculate_circular_wind_mean([45.0, float("nan"), None]) == 45.0


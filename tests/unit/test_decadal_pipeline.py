"""Unit Tests for Milestone M2: Decadal Physics-Informed Feature Pipeline.

Verifies:
1. Feature contract: exact 52-feature output contract, unique column names, exact ordering.
2. Strict zero lookahead: modifying future row t+k strictly has zero impact on rows <= t;
   lagged and rolling features at row t strictly depend on past steps < t.
3. Atmospheric physics formulas:
   - Wind circular trigonometry: sin^2(theta) + cos^2(theta) == 1.0.
   - Barometric Stagnation Index: bounded in [0, 100].
   - Ventilation Coefficient: VC = BLH * WS >= 0.0.
   - Log dispersion volume: ln(1 + max(0, VC)) >= 0.0.
   - Air density: ideal gas rho in [0.5, 2.0] kg/m3.
   - Wind Power Density: WPD = 0.5 * rho * WS^3 >= 0.0.
   - Thermal inversion index: TI >= 0.0.
   - Environmental lapse rate: Gamma in physical range.
   - Hygroscopic growth ratio: HR in [1.0, 20.0].
4. Past-only rolling dynamic indicators (volatility, momentum, RoC, slope):
   - Mathematically exact linear slope recovery on synthetic linear sequences.
   - Constant sequence produces zero volatility, zero momentum, zero slope.
5. Concept-drift and biomass trajectory indices:
   - 365-day secular detrending and ratio.
   - Decadal secular progress tau in [0.0, 1.0].
   - Post-monsoon biomass smoke index peaking in early November with ESE winds.
6. Sample decadal data slices:
   - Real CSV slices from Lahore, Karachi, and Quetta.
   - Real Parquet slice from year=2020 partition.
7. Scikit-learn compatibility:
   - fit, transform, fit_transform, and StandardScaler integration.
   - Causal warmup imputation without lookahead leakage.
   - Edge cases: empty DataFrame, single row, missing columns, extreme meteorology.
"""

import math
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import pytest

from ml.features.decadal_feature_pipeline import (
    DecadalFeaturePipeline,
    DECADA_FEATURE_CONTRACT_V1,
    DECADA_FEATURE_NAMES,
    DECADA_FEATURE_CONTRACT_VERSION,
)

AIRSENSE_ROOT = Path(r"d:\MUNIM - UOE @BIC\AirSense")
DECADAL_CSV_DIR = AIRSENSE_ROOT / "data" / "datasets" / "decadal" / "csv"
DECADAL_PARQUET_DIR = AIRSENSE_ROOT / "data" / "datasets" / "decadal" / "parquet"


# =============================================================================
# 1. CONTRACT SCHEMA & COLUMN SPECIFICATION TESTS
# =============================================================================

def test_contract_contains_exactly_52_features():
    """Verify DECADA_FEATURE_CONTRACT_V1 contains exactly 52 canonical features."""
    assert len(DECADA_FEATURE_CONTRACT_V1) == 52
    assert len(DECADA_FEATURE_NAMES) == 52
    assert DECADA_FEATURE_CONTRACT_V1 == DECADA_FEATURE_NAMES
    # Verify no duplicate feature names
    assert len(set(DECADA_FEATURE_CONTRACT_V1)) == 52


def test_contract_feature_subgroups_composition():
    """Verify all 6 functional feature subgroups are fully represented."""
    # 1. Temporal lags: 11 PM2.5 + 5 PM10 = 16
    pm25_lags = [c for c in DECADA_FEATURE_CONTRACT_V1 if c.startswith("pm2_5_lag_")]
    pm10_lags = [c for c in DECADA_FEATURE_CONTRACT_V1 if c.startswith("pm10_lag_")]
    assert len(pm25_lags) == 11
    assert len(pm10_lags) == 5
    assert "pm2_5_lag_168" in pm25_lags  # Weekly cycle lag

    # 2. Rolling statistics: 4 vol + 4 mom + 4 roc + 4 slope = 16
    vol_feats = [c for c in DECADA_FEATURE_CONTRACT_V1 if "_vol_" in c]
    mom_feats = [c for c in DECADA_FEATURE_CONTRACT_V1 if "_mom_" in c]
    roc_feats = [c for c in DECADA_FEATURE_CONTRACT_V1 if "_roc_" in c]
    slope_feats = [c for c in DECADA_FEATURE_CONTRACT_V1 if "_slope_" in c]
    assert len(vol_feats) == 4
    assert len(mom_feats) == 4
    assert len(roc_feats) == 4
    assert len(slope_feats) == 4

    # 3. Atmospheric physics (8)
    atmo_feats = [
        "boundary_layer_height_m", "ventilation_coeff", "log_dispersion_vol",
        "lapse_rate_c_km", "thermal_inversion_index", "barometric_stagnation_index",
        "hygroscopic_ratio", "air_density_kg_m3"
    ]
    for f in atmo_feats:
        assert f in DECADA_FEATURE_CONTRACT_V1

    # 4. Aerodynamic wind decomposition (5)
    aero_feats = ["wind_u10", "wind_v10", "wind_dir_sin", "wind_dir_cos", "wind_power_density"]
    for f in aero_feats:
        assert f in DECADA_FEATURE_CONTRACT_V1

    # 5. Concept-drift & biomass indices (4)
    drift_feats = [
        "decadal_secular_progress", "pm2_5_detrended_secular",
        "pm2_5_secular_ratio", "biomass_smoke_trajectory_index"
    ]
    for f in drift_feats:
        assert f in DECADA_FEATURE_CONTRACT_V1

    # 6. Calendar & harmonic encodings (3)
    calendar_feats = ["hour_sin", "hour_cos", "day_of_year_sin"]
    for f in calendar_feats:
        assert f in DECADA_FEATURE_CONTRACT_V1


# =============================================================================
# 2. STRICT ZERO FUTURE LOOKAHEAD LEAKAGE TESTS
# =============================================================================

def test_strict_zero_lookahead_future_row_perturbation():
    """Verify that perturbing future row t+k has zero effect on features at rows <= t."""
    dates = pd.date_range("2021-01-01 00:00:00", periods=80, freq="h", tz="UTC")
    df_clean = pd.DataFrame({
        "timestamp": dates,
        "pm2_5": np.linspace(25.0, 180.0, 80),
        "pm10": np.linspace(45.0, 310.0, 80),
        "temperature_c": np.linspace(12.0, 28.0, 80),
        "relative_humidity_pct": np.linspace(35.0, 85.0, 80),
        "pressure_hpa": np.linspace(1010.0, 1022.0, 80),
        "wind_speed_kmh": np.linspace(5.0, 22.0, 80),
        "wind_direction_deg": np.linspace(45.0, 270.0, 80),
        "precipitation_mm": [0.0] * 80,
        "blh_m": np.linspace(300.0, 1400.0, 80)
    })

    pipe = DecadalFeaturePipeline()
    pipe.fit(df_clean)
    X_clean = pipe.transform(df_clean)

    # Perturb row 40 with extreme values
    df_perturbed = df_clean.copy()
    df_perturbed.loc[40, "pm2_5"] = 9999.0
    df_perturbed.loc[40, "pm10"] = 15000.0
    df_perturbed.loc[40, "temperature_c"] = 65.0
    df_perturbed.loc[40, "wind_speed_kmh"] = 120.0
    df_perturbed.loc[40, "precipitation_mm"] = 150.0

    X_perturbed = pipe.transform(df_perturbed)

    # All features for all rows strictly before row 40 (rows 0 to 39) must be IDENTICAL
    for row_idx in range(40):
        clean_row = X_clean.iloc[row_idx].to_numpy()
        perturbed_row = X_perturbed.iloc[row_idx].to_numpy()
        max_diff = np.max(np.abs(clean_row - perturbed_row))
        assert max_diff == 0.0, f"Future lookahead detected at row {row_idx}: max_diff={max_diff}"


def test_strict_zero_lookahead_lagged_features_at_current_row():
    """Verify that lagged and rolling features at row t strictly depend on steps < t."""
    dates = pd.date_range("2021-06-01 00:00:00", periods=50, freq="h", tz="UTC")
    df1 = pd.DataFrame({
        "timestamp": dates,
        "pm2_5": [50.0] * 50,
        "pm10": [90.0] * 50,
        "temperature_c": [30.0] * 50,
        "relative_humidity_pct": [60.0] * 50,
        "pressure_hpa": [1005.0] * 50,
        "wind_speed_kmh": [10.0] * 50,
        "wind_direction_deg": [120.0] * 50,
        "precipitation_mm": [0.0] * 50,
        "blh_m": [800.0] * 50
    })

    # In df2, only row 30 is altered
    df2 = df1.copy()
    df2.loc[30, "pm2_5"] = 850.0
    df2.loc[30, "pm10"] = 1400.0

    pipe = DecadalFeaturePipeline()
    X1 = pipe.fit_transform(df1)
    X2 = pipe.transform(df2)

    # At row 30, all lagged and rolling PM features must NOT reflect the sudden shock at row 30
    lag_and_rolling_cols = [
        c for c in DECADA_FEATURE_CONTRACT_V1
        if any(keyword in c for keyword in ["lag", "vol", "mom", "roc", "slope", "detrended", "secular_ratio"])
    ]

    for col in lag_and_rolling_cols:
        val1 = X1.loc[30, col]
        val2 = X2.loc[30, col]
        assert np.isclose(val1, val2, atol=1e-5), (
            f"Feature {col} at row 30 leaked current-step value! val1={val1}, val2={val2}"
        )


# =============================================================================
# 3. PHYSICAL ATMOSPHERIC & AERODYNAMIC FORMULAS
# =============================================================================

def test_wind_trigonometry_circular_invariant():
    """Verify circular wind vector trigonometry preserves sin^2(theta) + cos^2(theta) == 1.0."""
    angles = np.arange(0.0, 360.0, 15.0)
    dates = pd.date_range("2022-01-01", periods=len(angles), freq="h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "wind_direction_deg": angles,
        "wind_speed_kmh": [18.0] * len(angles),
        "pm2_5": [40.0] * len(angles)
    })

    pipe = DecadalFeaturePipeline()
    X = pipe.fit_transform(df)

    sin_vals = X["wind_dir_sin"].to_numpy()
    cos_vals = X["wind_dir_cos"].to_numpy()
    sum_sq = (sin_vals ** 2) + (cos_vals ** 2)

    assert np.allclose(sum_sq, 1.0, atol=1e-5), "sin^2 + cos^2 != 1.0 invariant violated"

    # Verify Cartesian components magnitude equals wind speed
    # 18 km/h = 5.0 m/s
    u10 = X["wind_u10"].to_numpy()
    v10 = X["wind_v10"].to_numpy()
    speed_sq = (u10 ** 2) + (v10 ** 2)
    assert np.allclose(speed_sq, 25.0, atol=1e-4)


def test_barometric_stagnation_index_bounded_0_to_100():
    """Verify Barometric Stagnation Index is strictly bounded in [0.0, 100.0] across extremes."""
    # Test boundary scenarios:
    # 1. Total calm, high pressure anticyclone, zero rain -> Max Stagnation
    # 2. Gale force winds, low pressure cyclone, heavy rain -> Min Stagnation
    # 3. Nominal average conditions
    dates = pd.date_range("2023-01-01", periods=6, freq="h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "wind_speed_kmh": [0.0, 0.5, 30.0, 75.0, 120.0, 10.0],
        "pressure_hpa": [1030.0, 1025.0, 1013.0, 990.0, 980.0, 1015.0],
        "precipitation_mm": [0.0, 0.0, 0.0, 25.0, 80.0, 0.2],
        "pm2_5": [50.0] * 6
    })

    pipe = DecadalFeaturePipeline()
    X = pipe.fit_transform(df)

    bsi = X["barometric_stagnation_index"].to_numpy()
    assert (bsi >= 0.0).all(), "BSI contains negative values"
    assert (bsi <= 100.0).all(), "BSI exceeds upper bound 100.0"

    # Calm anticyclone should produce higher BSI than gale storm
    assert bsi[0] > bsi[3]
    assert bsi[0] > bsi[4]
    assert bsi[4] < 1.0  # Hurricane-force rain/wind drops BSI to near zero


def test_ventilation_coefficient_non_negativity_and_units():
    """Verify Ventilation Coefficient VC = BLH * WS >= 0.0 and log dispersion volume."""
    dates = pd.date_range("2023-05-01", periods=5, freq="h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "blh_m": [100.0, 500.0, 1200.0, 2500.0, 50.0],
        "wind_speed_kmh": [0.0, 3.6, 14.4, 36.0, 7.2],  # 0.0, 1.0, 4.0, 10.0, 2.0 m/s
        "pm2_5": [30.0] * 5
    })

    pipe = DecadalFeaturePipeline()
    X = pipe.fit_transform(df)

    vc = X["ventilation_coeff"].to_numpy()
    log_vc = X["log_dispersion_vol"].to_numpy()

    assert (vc >= 0.0).all()
    assert (log_vc >= 0.0).all()

    # Verify at row 1: BLH=500m, WS=1.0 m/s -> VC=500 m2/s
    assert np.isclose(vc[1], 500.0, atol=1e-2)
    assert np.isclose(log_vc[1], np.log1p(500.0), atol=1e-4)

    # Verify at row 2: BLH=1200m, WS=4.0 m/s -> VC=4800 m2/s
    assert np.isclose(vc[2], 4800.0, atol=1e-2)


def test_ideal_gas_air_density_and_wind_power_density():
    """Verify moist air density formula rho = P*100 / (R * T_K) and WPD = 0.5 * rho * WS^3."""
    dates = pd.date_range("2023-07-01", periods=4, freq="h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "temperature_c": [15.0, 35.0, -5.0, 25.0],
        "pressure_hpa": [1013.25, 1000.0, 1025.0, 835.0],  # 835 is Quetta altitude
        "wind_speed_kmh": [14.4, 28.8, 0.0, 18.0],          # 4.0, 8.0, 0.0, 5.0 m/s
        "pm2_5": [40.0] * 4
    })

    pipe = DecadalFeaturePipeline()
    X = pipe.fit_transform(df)

    rho = X["air_density_kg_m3"].to_numpy()
    wpd = X["wind_power_density"].to_numpy()

    # Standard atmosphere check at row 0 (15 C = 288.15 K, 1013.25 hPa)
    expected_rho_std = (101325.0) / (287.058 * 288.15)  # ~1.225 kg/m3
    assert np.isclose(rho[0], expected_rho_std, atol=1e-3)

    # High altitude Quetta check at row 3 (25 C, 835 hPa) -> lower density
    assert rho[3] < rho[0]
    assert 0.90 < rho[3] < 1.05

    # WPD checks
    assert (wpd >= 0.0).all()
    # At zero wind (row 2), WPD must be exactly 0.0
    assert wpd[2] == 0.0
    # At row 0 (WS=4.0 m/s, rho=1.225): WPD = 0.5 * 1.225 * 64.0 = 39.2 W/m2
    expected_wpd_0 = 0.5 * expected_rho_std * (4.0 ** 3)
    assert np.isclose(wpd[0], expected_wpd_0, atol=1e-2)


def test_thermal_inversion_index_and_lapse_rate():
    """Verify thermal inversion index proxy and lapse rate relationship."""
    dates = pd.date_range("2023-11-15", periods=3, freq="h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "temperature_c": [8.0, 30.0, 18.0],
        "pressure_hpa": [1022.0, 1005.0, 1013.0],
        "wind_speed_kmh": [1.8, 25.0, 10.0],  # 0.5 m/s, ~7 m/s, ~2.8 m/s
        "pm2_5": [80.0] * 3
    })

    pipe = DecadalFeaturePipeline()
    X = pipe.fit_transform(df)

    ti = X["thermal_inversion_index"].to_numpy()
    gamma = X["lapse_rate_c_km"].to_numpy()

    assert (ti >= 0.0).all()
    # Winter anticyclone calm morning (row 0) should show severe inversion
    assert ti[0] > 0.0
    assert gamma[0] < 6.5  # Inversion depresses lapse rate

    # Hot turbulent afternoon (row 1) should show 0 inversion
    assert ti[1] == 0.0
    assert np.isclose(gamma[1], 6.5, atol=1e-4)


def test_hygroscopic_growth_ratio_behavior():
    """Verify hygroscopic swelling ratio increases monotonically with humidity."""
    rh_values = [0.0, 30.0, 50.0, 75.0, 85.0, 95.0, 100.0]
    dates = pd.date_range("2023-08-01", periods=len(rh_values), freq="h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "relative_humidity_pct": rh_values,
        "pm2_5": [45.0] * len(rh_values)
    })

    pipe = DecadalFeaturePipeline()
    X = pipe.fit_transform(df)

    hr = X["hygroscopic_ratio"].to_numpy()
    assert (hr >= 1.0).all(), "Hygroscopic ratio cannot be less than 1.0"
    assert (hr <= 20.0).all(), "Hygroscopic ratio exceeds safety cap"

    # Strictly monotonically non-decreasing
    for i in range(len(hr) - 1):
        assert hr[i+1] >= hr[i]


# =============================================================================
# 4. MATHEMATICAL PRECISION OF ROLLING INDICATORS
# =============================================================================

def test_rolling_least_squares_slope_exact_linear_recovery():
    """Verify rolling trend slope recovers true mathematical slope on linear ramp."""
    n = 60
    dates = pd.date_range("2022-01-01", periods=n, freq="h", tz="UTC")
    true_slope = 4.25
    df = pd.DataFrame({
        "timestamp": dates,
        "pm2_5": [true_slope * i + 10.0 for i in range(n)]
    })

    pipe = DecadalFeaturePipeline()
    X = pipe.fit_transform(df)

    for W in [3, 6, 12, 24]:
        slope_series = X[f"pm2_5_slope_{W}h"].to_numpy()
        # For index >= W, the past W points [y_{t-W} ... y_{t-1}] form a line with slope 4.25
        valid_slopes = slope_series[W:]
        assert np.allclose(valid_slopes, true_slope, atol=1e-4), (
            f"Failed to recover exact slope for W={W}: max error={np.max(np.abs(valid_slopes - true_slope))}"
        )


def test_rolling_indicators_on_constant_series():
    """Verify rolling volatility, momentum, roc, and slope are exactly zero on constant data."""
    n = 40
    dates = pd.date_range("2022-01-01", periods=n, freq="h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "pm2_5": [75.0] * n
    })

    pipe = DecadalFeaturePipeline()
    X = pipe.fit_transform(df)

    for W in [3, 6, 12, 24]:
        assert np.allclose(X[f"pm2_5_vol_{W}h"], 0.0, atol=1e-5)
        assert np.allclose(X[f"pm2_5_mom_{W}h"], 0.0, atol=1e-5)
        assert np.allclose(X[f"pm2_5_roc_{W}h"], 0.0, atol=1e-5)
        assert np.allclose(X[f"pm2_5_slope_{W}h"], 0.0, atol=1e-5)


# =============================================================================
# 5. CONCEPT-DRIFT & BIOMASS TRAJECTORY INDICES
# =============================================================================

def test_decadal_secular_progress_timeline_bounds():
    """Verify decadal secular progress is bounded [0.0, 1.0] across the 31-year span."""
    test_dates = [
        "1995-01-01 00:00:00+00:00",  # Start: tau = 0.0
        "2010-07-02 12:00:00+00:00",  # Midpoint: tau ~ 0.5
        "2025-12-31 23:00:00+00:00",  # End: tau ~ 1.0
    ]
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(test_dates),
        "pm2_5": [50.0, 60.0, 70.0]
    })

    pipe = DecadalFeaturePipeline()
    X = pipe.fit_transform(df)

    tau = X["decadal_secular_progress"].to_numpy()
    assert np.isclose(tau[0], 0.0, atol=1e-4)
    assert 0.48 < tau[1] < 0.52
    assert np.isclose(tau[2], 1.0, atol=1e-2)


def test_regional_biomass_burning_trajectory_index():
    """Verify UTI peaks during post-monsoon (early Nov) with ESE wind advection."""
    # Peak day 308 (early November), wind direction 110 deg (ESE advection)
    date_peak = pd.to_datetime(["2023-11-04 12:00:00+00:00"])  # Day 308
    date_summer = pd.to_datetime(["2023-07-15 12:00:00+00:00"]) # Mid-summer

    df_peak = pd.DataFrame({
        "timestamp": date_peak,
        "wind_direction_deg": [110.0],
        "wind_speed_kmh": [14.4],  # 4.0 m/s
        "pm2_5": [120.0]
    })

    df_summer = pd.DataFrame({
        "timestamp": date_summer,
        "wind_direction_deg": [110.0],
        "wind_speed_kmh": [14.4],
        "pm2_5": [40.0]
    })

    df_wrong_wind = pd.DataFrame({
        "timestamp": date_peak,
        "wind_direction_deg": [290.0],  # Opposite direction (WNW)
        "wind_speed_kmh": [14.4],
        "pm2_5": [120.0]
    })

    pipe = DecadalFeaturePipeline()
    uti_peak = pipe.fit_transform(df_peak)["biomass_smoke_trajectory_index"].iloc[0]
    uti_summer = pipe.transform(df_summer)["biomass_smoke_trajectory_index"].iloc[0]
    uti_wrong_wind = pipe.transform(df_wrong_wind)["biomass_smoke_trajectory_index"].iloc[0]

    assert uti_peak > 0.8
    assert uti_summer < 0.01
    assert uti_wrong_wind < 0.01


# =============================================================================
# 6. REAL DECADAL DATASET SLICE TRANSFORMATION TESTS
# =============================================================================

@pytest.mark.parametrize("city", ["lahore", "karachi", "quetta"])
def test_transformation_on_real_decadal_csv_slices(city):
    """Verify feature pipeline on real slices from the 1,630,512-hour decadal data lake."""
    csv_path = DECADAL_CSV_DIR / f"airsense_decadal_{city}_1995_2025.csv"
    if not csv_path.exists():
        # Fallback path if master csv at parent
        csv_path = DECADAL_CSV_DIR.parent / f"airsense_30year_{city}_1995_2025.csv"

    assert csv_path.exists(), f"Decadal dataset for {city} missing at {csv_path}"

    df_slice = pd.read_csv(csv_path, nrows=500)
    pipe = DecadalFeaturePipeline(city=city)
    X = pipe.fit_transform(df_slice)

    # 1. Output shape must be exactly (N, 52)
    assert X.shape == (500, 52)
    # 2. Columns must exactly match contract
    assert list(X.columns) == DECADA_FEATURE_CONTRACT_V1
    # 3. Dtype must be float32
    assert (X.dtypes == np.float32).all()
    # 4. Zero NaNs or Infs
    assert X.isna().sum().sum() == 0
    assert not np.isinf(X.to_numpy()).any()


def test_transformation_on_real_decadal_parquet_slice():
    """Verify feature extraction on real Snappy-compressed Parquet partition."""
    pq_file = DECADAL_PARQUET_DIR / "city=lahore" / "year=2020" / "airsense_lahore_2020.parquet"
    assert pq_file.exists(), f"Parquet file missing at {pq_file}"

    df_pq = pd.read_parquet(pq_file).iloc[:300]
    pipe = DecadalFeaturePipeline(city="lahore")
    X = pipe.fit_transform(df_pq)

    assert X.shape == (300, 52)
    assert list(X.columns) == DECADA_FEATURE_CONTRACT_V1
    assert X.isna().sum().sum() == 0


# =============================================================================
# 7. SCIKIT-LEARN PIPELINE & SYSTEM INTEGRATION TESTS
# =============================================================================

def test_sklearn_transformer_fit_transform_and_scaling():
    """Verify scikit-learn pipeline compliance, StandardScaler option, and test isolation."""
    dates_train = pd.date_range("2020-01-01", periods=200, freq="h", tz="UTC")
    dates_test = pd.date_range("2020-01-09 08:00:00", periods=50, freq="h", tz="UTC")

    df_train = pd.DataFrame({
        "timestamp": dates_train,
        "pm2_5": np.random.uniform(20.0, 150.0, 200),
        "temperature_c": np.random.uniform(10.0, 35.0, 200),
        "wind_speed_kmh": np.random.uniform(2.0, 25.0, 200)
    })

    df_test = pd.DataFrame({
        "timestamp": dates_test,
        "pm2_5": np.random.uniform(30.0, 180.0, 50),
        "temperature_c": np.random.uniform(12.0, 32.0, 50),
        "wind_speed_kmh": np.random.uniform(3.0, 22.0, 50)
    })

    # Unscaled pipeline
    pipe_unscaled = DecadalFeaturePipeline(scale_features=False)
    pipe_unscaled.fit(df_train)
    assert pipe_unscaled.is_fitted_
    X_test_unscaled = pipe_unscaled.transform(df_test)
    assert X_test_unscaled.shape == (50, 52)
    assert X_test_unscaled.isna().sum().sum() == 0

    # Scaled pipeline
    pipe_scaled = DecadalFeaturePipeline(scale_features=True)
    pipe_scaled.fit(df_train)
    X_train_scaled = pipe_scaled.transform(df_train)
    # Check that training features have approximately mean 0 and std 1
    assert np.allclose(X_train_scaled.mean(), 0.0, atol=0.2)
    X_test_scaled = pipe_scaled.transform(df_test)
    assert X_test_scaled.shape == (50, 52)
    assert X_test_scaled.isna().sum().sum() == 0


def test_extract_features_and_target_alignment():
    """Verify extract_features_and_target produces aligned X and y without lookahead."""
    dates = pd.date_range("2022-01-01", periods=100, freq="h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "pm2_5": [float(i * 2 + 10) for i in range(100)],
        "temperature_c": [20.0] * 100
    })

    pipe = DecadalFeaturePipeline()
    # 1-hour ahead horizon
    X, y = pipe.extract_features_and_target(df, target_col="pm2_5", horizon=1)
    assert len(X) == 100
    assert len(y) == 100
    # At row t, y is pm2_5 at step t
    assert y.iloc[10] == 30.0
    # Lag 1 at row t is pm2_5 at step t-1
    assert X.loc[10, "pm2_5_lag_1"] == 28.0

    # Multi-step ahead horizon (h=6)
    X6, y6 = pipe.extract_features_and_target(df, target_col="pm2_5", horizon=6)
    # Trailing 5 rows dropped because target is shifted backward by 5
    assert len(X6) == 95
    assert len(y6) == 95
    # Target at row 0 is value at index 5 (5 * 2 + 10 = 20.0)
    assert y6.iloc[0] == 20.0


def test_dataset_fingerprint_deterministic_and_sensitive():
    """Verify compute_dataset_fingerprint is deterministic and sensitive to changes."""
    dates = pd.date_range("2023-01-01", periods=40, freq="h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "pm2_5": np.linspace(20.0, 80.0, 40)
    })

    pipe = DecadalFeaturePipeline()
    X = pipe.fit_transform(df)

    fp1 = DecadalFeaturePipeline.compute_dataset_fingerprint(X, horizon=1, scope="decadal_test")
    fp2 = DecadalFeaturePipeline.compute_dataset_fingerprint(X, horizon=1, scope="decadal_test")
    assert fp1 == fp2
    assert len(fp1) == 64

    # Modifying one element must produce a distinct fingerprint
    X_modified = X.copy()
    X_modified.iloc[10, 0] = X_modified.iloc[10, 0] + 1.0
    fp3 = DecadalFeaturePipeline.compute_dataset_fingerprint(X_modified, horizon=1, scope="decadal_test")
    assert fp1 != fp3


def test_edge_cases_empty_single_row_and_extreme_weather():
    """Verify edge cases: empty DataFrame, single row, missing columns, and extreme values."""
    pipe = DecadalFeaturePipeline()

    # Empty DataFrame
    df_empty = pd.DataFrame(columns=["timestamp", "pm2_5"])
    X_empty = pipe.fit_transform(df_empty)
    assert X_empty.shape == (0, 52)
    assert list(X_empty.columns) == DECADA_FEATURE_CONTRACT_V1

    # Single row DataFrame
    df_single = pd.DataFrame({
        "timestamp": ["2023-01-01 00:00:00+00:00"],
        "pm2_5": [55.0]
    })
    X_single = pipe.fit_transform(df_single)
    assert X_single.shape == (1, 52)
    assert X_single.isna().sum().sum() == 0

    # Extreme meteorological conditions
    df_extreme = pd.DataFrame({
        "timestamp": pd.date_range("2023-01-01", periods=3, freq="h", tz="UTC"),
        "pm2_5": [0.0, 999.0, 45.0],
        "temperature_c": [-25.0, 55.0, 20.0],
        "relative_humidity_pct": [0.0, 100.0, 50.0],
        "wind_speed_kmh": [0.0, 150.0, 15.0],
        "pressure_hpa": [800.0, 1040.0, 1013.25],
        "precipitation_mm": [0.0, 200.0, 0.0],
        "blh_m": [10.0, 4500.0, 500.0]
    })
    X_extreme = pipe.fit_transform(df_extreme)
    assert X_extreme.shape == (3, 52)
    assert X_extreme.isna().sum().sum() == 0
    assert not np.isinf(X_extreme.to_numpy()).any()

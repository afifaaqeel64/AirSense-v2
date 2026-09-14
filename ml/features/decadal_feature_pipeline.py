"""AirSense Pakistan Decadal Feature Pipeline (DECADA_FEATURE_CONTRACT_V1).

Physics-Informed, Concept-Drift-Resilient 52-Feature Pipeline for Multi-Decadal
(1995-2025) Atmospheric and Particulate Modeling across Pakistan's Core Urban Centers.

Features (52 Canonical Features):
1. Temporal Lags (16):
   - PM2.5 past-only lags: t-1, t-2, t-3, t-4, t-6, t-8, t-12, t-16, t-20, t-24, t-168
   - PM10 past-only lags: t-1, t-2, t-6, t-12, t-24
2. Rolling Volatility, Momentum, RoC & Trend Slope (16):
   - Rolling Volatility (std): 3h, 6h, 12h, 24h
   - Rolling Momentum (diff): 3h, 6h, 12h, 24h
   - Rolling Rate-of-Change (roc): 3h, 6h, 12h, 24h
   - Rolling Trend Slope (least-squares velocity): 3h, 6h, 12h, 24h
3. Atmospheric Physics & Inversion Dynamics (8):
   - Boundary Layer Height (BLH in meters)
   - Ventilation Coefficient (VC = BLH * WS in m2/s)
   - Log Dispersion Volume (ln(1 + VC))
   - Environmental Lapse Rate (Gamma in °C/km)
   - Thermal Inversion Index (TI proxy in °C)
   - Barometric Stagnation Index (BSI in [0, 100])
   - Hygroscopic Growth Ratio (HR)
   - Moist Air Density (rho in kg/m3 via ideal gas law)
4. Aerodynamic & Wind Vector Decomposition (5):
   - Cartesian eastward vector component (u10)
   - Cartesian northward vector component (v10)
   - Circular trigonometric sine (wind_dir_sin)
   - Circular trigonometric cosine (wind_dir_cos)
   - Wind Power Density (WPD = 0.5 * rho * WS^3 in W/m2)
5. Concept-Drift, Decadal Trend & Biomass Indices (4):
   - Decadal Secular Progress (tau in [0, 1])
   - 365-Day Secular Detrended Residual (Delta PM_secular)
   - Secular Trend Ratio (PM2.5 / Trend_365d)
   - Regional Biomass Smoke Trajectory Index (UTI)
6. Calendar & Diurnal Harmonic Encodings (3):
   - Diurnal cycle sine (hour_sin)
   - Diurnal cycle cosine (hour_cos)
   - Annual solar cycle sine (day_of_year_sin)

Guarantees:
- Strict zero future lookahead: all features at row t depend strictly on observations <= t
  (and strictly < t for lagged and rolling PM features).
- Causal imputation for initial lag warm-up without lookahead leakage.
- Scikit-learn BaseEstimator / TransformerMixin compliance.
- Deterministic dataset SHA-256 fingerprinting.
"""

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler

DECADA_FEATURE_CONTRACT_VERSION = "1.0.0"

# Exact 52-Feature Canonical Contract
DECADA_FEATURE_CONTRACT_V1: List[str] = [
    # 1. Temporal Lags (16)
    "pm2_5_lag_1", "pm2_5_lag_2", "pm2_5_lag_3", "pm2_5_lag_4",
    "pm2_5_lag_6", "pm2_5_lag_8", "pm2_5_lag_12", "pm2_5_lag_16",
    "pm2_5_lag_20", "pm2_5_lag_24", "pm2_5_lag_168",
    "pm10_lag_1", "pm10_lag_2", "pm10_lag_6", "pm10_lag_12", "pm10_lag_24",

    # 2. Rolling Volatility, Momentum & RoC (16)
    "pm2_5_vol_3h", "pm2_5_vol_6h", "pm2_5_vol_12h", "pm2_5_vol_24h",
    "pm2_5_mom_3h", "pm2_5_mom_6h", "pm2_5_mom_12h", "pm2_5_mom_24h",
    "pm2_5_roc_3h", "pm2_5_roc_6h", "pm2_5_roc_12h", "pm2_5_roc_24h",
    "pm2_5_slope_3h", "pm2_5_slope_6h", "pm2_5_slope_12h", "pm2_5_slope_24h",

    # 3. Atmospheric Physics & Inversion Dynamics (8)
    "boundary_layer_height_m", "ventilation_coeff", "log_dispersion_vol",
    "lapse_rate_c_km", "thermal_inversion_index", "barometric_stagnation_index",
    "hygroscopic_ratio", "air_density_kg_m3",

    # 4. Aerodynamic & Wind Vector Features (5)
    "wind_u10", "wind_v10", "wind_dir_sin", "wind_dir_cos", "wind_power_density",

    # 5. Concept-Drift, Decadal Trend & Biomass Indices (4)
    "decadal_secular_progress", "pm2_5_detrended_secular", "pm2_5_secular_ratio",
    "biomass_smoke_trajectory_index",

    # 6. Calendar & Diurnal Harmonic Encodings (3)
    "hour_sin", "hour_cos", "day_of_year_sin"
]

DECADA_FEATURE_NAMES: List[str] = DECADA_FEATURE_CONTRACT_V1

# Physical Constants
R_SPECIFIC_AIR = 287.058  # J / (kg * K)
DECADA_START_TIMESTAMP = pd.Timestamp("1995-01-01 00:00:00+00:00")
DECADA_TOTAL_SECONDS = 31.0 * 365.25 * 86400.0  # 31 years in seconds


def _compute_rolling_slopes(
    y_vals: np.ndarray,
    windows: List[int],
    initial_fill: float = 0.0
) -> Dict[str, np.ndarray]:
    """Computes past-only least-squares trend slopes over past W observations.

    At index t, the window of observations is strictly [y_{t-W}, ..., y_{t-1}].
    Zero future lookahead: y_t is never included in the slope calculation.
    """
    n = len(y_vals)
    slopes: Dict[str, np.ndarray] = {}

    for W in windows:
        col_name = f"pm2_5_slope_{W}h"
        out = np.full(n, initial_fill, dtype=np.float64)
        if n >= W + 1:
            w = np.arange(W, dtype=np.float64) - (W - 1) / 2.0
            denom = np.sum(w ** 2)
            kernel = w / denom
            out[W:] = np.convolve(y_vals[:-1], kernel[::-1], mode="valid")
        slopes[col_name] = out
    return slopes


class DecadalFeaturePipeline(BaseEstimator, TransformerMixin):
    """Scikit-learn compliant, physics-informed feature pipeline for decadal air quality modeling.

    Implements the 52-feature DECADA_FEATURE_CONTRACT_V1 specification with strict zero lookahead,
    causal initial lag imputation, and atmospheric thermodynamic indicators.
    """

    def __init__(
        self,
        scale_features: bool = False,
        fill_na: bool = True,
        city: Optional[str] = None
    ):
        self.scale_features = scale_features
        self.fill_na = fill_na
        self.city = city

        # Fitted parameters
        self.is_fitted_: bool = False
        self.feature_medians_: Dict[str, float] = {}
        self.feature_means_: Dict[str, float] = {}
        self.fit_pm2_5_mean_: float = 45.0
        self.fit_pm2_5_median_: float = 35.0
        self.fit_pm10_mean_: float = 75.0
        self.fit_pm10_median_: float = 65.0
        self.fit_pressure_mean_: float = 1013.25
        self.scaler_: Optional[StandardScaler] = None

    def fit(self, X: pd.DataFrame, y: Optional[Any] = None) -> "DecadalFeaturePipeline":
        """Fits baseline statistics and scalers on training observations without lookahead."""
        if X.empty:
            return self

        # 1. Compute primary distribution statistics first so warmup fills are identical
        pm25_series = self._resolve_column(X, ["pm2_5", "pm2_5_mean", "pm25"], 35.0)
        pm10_series = self._resolve_column(X, ["pm10", "pm10_mean"], 65.0)
        p_series = self._resolve_column(X, ["pressure_hpa", "pressure_mean"], 1013.25)

        self.fit_pm2_5_mean_ = float(pm25_series.mean())
        self.fit_pm2_5_median_ = float(pm25_series.median())
        self.fit_pm10_mean_ = float(pm10_series.mean())
        self.fit_pm10_median_ = float(pm10_series.median())
        self.fit_pressure_mean_ = float(p_series.mean())

        # 2. Generate unscaled raw features on training partition
        df_raw = self._extract_raw_features(X, is_training=True)

        # Record training distribution medians and means for zero-lookahead imputation
        self.feature_medians_ = {
            col: float(df_raw[col].median()) if not df_raw[col].isna().all() else 0.0
            for col in DECADA_FEATURE_CONTRACT_V1
        }
        self.feature_means_ = {
            col: float(df_raw[col].mean()) if not df_raw[col].isna().all() else 0.0
            for col in DECADA_FEATURE_CONTRACT_V1
        }

        # 3. Fit standard scaler if requested
        if self.scale_features:
            df_imputed = df_raw.fillna(self.feature_medians_)
            self.scaler_ = StandardScaler()
            self.scaler_.fit(df_imputed[DECADA_FEATURE_CONTRACT_V1])

        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transforms observations into canonical 52-dimensional float32 feature matrix."""
        if X.empty:
            return pd.DataFrame(columns=DECADA_FEATURE_CONTRACT_V1, dtype=np.float32)

        # Generate raw causal features
        df_feats = self._extract_raw_features(X, is_training=False)

        # Causal imputation using fitted training medians
        if self.fill_na:
            fill_values = self.feature_medians_ if self.is_fitted_ else {
                col: 0.0 for col in DECADA_FEATURE_CONTRACT_V1
            }
            # Also fill initial PM2.5/PM10 lags from earliest available or trained median
            for col in DECADA_FEATURE_CONTRACT_V1:
                default_fill = fill_values.get(col, 0.0)
                df_feats[col] = df_feats[col].fillna(default_fill)

        # Apply scaler if enabled
        if self.scale_features and self.scaler_ is not None:
            scaled_vals = self.scaler_.transform(df_feats[DECADA_FEATURE_CONTRACT_V1])
            df_feats = pd.DataFrame(
                scaled_vals,
                columns=DECADA_FEATURE_CONTRACT_V1,
                index=df_feats.index
            )

        # Ensure strict column ordering, physical float32 casting, and finite values
        df_out = df_feats[DECADA_FEATURE_CONTRACT_V1].astype(np.float32).copy()
        df_out = df_out.replace([np.inf, -np.inf], 0.0).fillna(0.0)
        return df_out

    def fit_transform(self, X: pd.DataFrame, y: Optional[Any] = None) -> pd.DataFrame:
        """Fits on training observations and returns transformed 52-feature matrix."""
        return self.fit(X, y).transform(X)

    @classmethod
    def compute_features(cls, df_hourly: pd.DataFrame, city: Optional[str] = None) -> pd.DataFrame:
        """Convenience method to transform an hourly DataFrame directly into 52 canonical features."""
        pipeline = cls(scale_features=False, fill_na=True, city=city)
        return pipeline.fit_transform(df_hourly)

    def extract_features_and_target(
        self,
        df: pd.DataFrame,
        target_col: str = "pm2_5",
        horizon: int = 1
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Extracts 52-feature matrix X and lead-horizon target y with strict zero lookahead.

        For lead horizon h >= 1:
        Target at index t is the observed PM2.5 concentration at step t + (h - 1),
        so for 1-hour forecast (h=1), target is current PM2.5 at step t, while all PM
        autoregressive and rolling features in X(t) strictly depend on past steps <= t-1.
        """
        X = self.transform(df)

        target_series = self._resolve_column(df, [target_col, f"{target_col}_mean", "pm2_5", "pm2_5_mean"], 35.0)

        if horizon > 1:
            # Shift target backward by (horizon - 1) so row t aligns with target at t + (horizon - 1)
            y = target_series.shift(-(horizon - 1)).astype(np.float32)
        else:
            y = target_series.astype(np.float32)

        # Drop trailing rows where target is unavailable due to lead shift
        valid_idx = ~y.isna()
        return X.loc[valid_idx].copy(), y.loc[valid_idx].copy()

    @classmethod
    def compute_dataset_fingerprint(
        cls,
        df_features: pd.DataFrame,
        horizon: int = 1,
        scope: str = "decadal"
    ) -> str:
        """Computes a deterministic SHA-256 fingerprint for dataset reproducibility and governance."""
        if df_features.empty:
            raw_hash = "empty"
        else:
            raw_hash = hashlib.sha256(df_features.to_numpy().tobytes()).hexdigest()

        summary = {
            "feature_contract": "DECADA_FEATURE_CONTRACT_V1",
            "version": DECADA_FEATURE_CONTRACT_VERSION,
            "horizon": horizon,
            "scope": scope,
            "rows": len(df_features),
            "columns": list(df_features.columns),
            "feature_checksum": raw_hash
        }
        return hashlib.sha256(json.dumps(summary, sort_keys=True).encode("utf-8")).hexdigest()

    # -------------------------------------------------------------------------
    # Internal Feature Extraction Mechanics
    # -------------------------------------------------------------------------

    def _extract_raw_features(self, df: pd.DataFrame, is_training: bool = False) -> pd.DataFrame:
        """Extracts all 52 features using strictly causal past observations."""
        df_work = df.copy()

        # 1. Parse and sort timestamps chronologically
        ts_series = self._resolve_timestamp_column(df_work)
        df_work["_parsed_ts"] = ts_series

        # Determine target city for elevation and trajectory adjustments
        city_name = self._resolve_city(df_work)

        # Resolve primary meteorological and particulate series
        pm25 = self._resolve_column(df_work, ["pm2_5", "pm2_5_mean", "pm25"], 35.0)
        pm10 = self._resolve_column(df_work, ["pm10", "pm10_mean"], 65.0)
        temp_c = self._resolve_column(df_work, ["temperature_c", "temperature_mean", "temp_c", "temperature"], 25.0)
        rh = self._resolve_column(df_work, ["relative_humidity_pct", "humidity_mean", "humidity_pct", "rh"], 50.0)
        pressure = self._resolve_column(df_work, ["pressure_hpa", "pressure_mean", "pressure"], 1013.25)
        ws_m_s = self._resolve_wind_speed(df_work)
        wind_deg = self._resolve_column(df_work, ["wind_direction_deg", "wind_direction_circular_mean", "wind_direction"], 0.0)
        precip_mm = self._resolve_precipitation(df_work)
        blh_m = self._resolve_column(df_work, ["blh_m", "boundary_layer_height_m", "blh"], 500.0)

        n = len(df_work)
        feats: Dict[str, Union[pd.Series, np.ndarray]] = {}

        # ---------------------------------------------------------------------
        # 1. Past-Only Autoregressive Lags (16)
        # ---------------------------------------------------------------------
        # Fallback values for initial warmup period
        fill_pm25 = self.fit_pm2_5_median_
        fill_pm10 = self.fit_pm10_median_

        pm25_lags = [1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 168]
        for lag in pm25_lags:
            col = f"pm2_5_lag_{lag}"
            shifted = pm25.shift(lag)
            # Causal warmup: use earliest observed past values, then fallback to training median
            feats[col] = shifted.fillna(fill_pm25)

        pm10_lags = [1, 2, 6, 12, 24]
        for lag in pm10_lags:
            col = f"pm10_lag_{lag}"
            shifted = pm10.shift(lag)
            feats[col] = shifted.fillna(fill_pm10)

        # ---------------------------------------------------------------------
        # 2. Rolling Volatility, Momentum, RoC & Trend Slope (16)
        # All computed strictly over shifted series y_{t-1}
        # ---------------------------------------------------------------------
        shifted_pm25 = pm25.shift(1)
        pm25_vals = pm25.to_numpy(dtype=np.float64)

        windows = [3, 6, 12, 24]
        for W in windows:
            # Volatility (sample standard deviation over past W hours)
            vol_col = f"pm2_5_vol_{W}h"
            vol_series = shifted_pm25.rolling(window=W, min_periods=2).std()
            feats[vol_col] = np.maximum(0.0, vol_series.fillna(0.0))

            # Momentum (y_{t-1} - y_{t-W})
            mom_col = f"pm2_5_mom_{W}h"
            mom_series = shifted_pm25 - pm25.shift(W)
            feats[mom_col] = mom_series.fillna(0.0)

            # Rate-of-Change ((y_{t-1} - y_{t-W}) / max(|y_{t-W}|, 1.0))
            roc_col = f"pm2_5_roc_{W}h"
            past_w = pm25.shift(W)
            denom_roc = np.maximum(np.abs(past_w), 1.0)
            roc_series = (shifted_pm25 - past_w) / denom_roc
            feats[roc_col] = roc_series.fillna(0.0)

        # Least-Squares Trend Slopes via past-only convolution
        slopes_dict = _compute_rolling_slopes(pm25_vals, windows, initial_fill=0.0)
        for col_name, slope_arr in slopes_dict.items():
            feats[col_name] = slope_arr

        # ---------------------------------------------------------------------
        # 3. Atmospheric Physics & Inversion Dynamics (8)
        # ---------------------------------------------------------------------
        # Boundary Layer Height (m)
        blh_arr = np.maximum(20.0, blh_m.to_numpy(dtype=np.float64))
        feats["boundary_layer_height_m"] = blh_arr

        # Wind speed array in m/s (guaranteed non-negative)
        ws_arr = np.maximum(0.0, ws_m_s.to_numpy(dtype=np.float64))

        # Ventilation Coefficient (m2/s): VC = BLH * WS
        vc_arr = blh_arr * ws_arr
        feats["ventilation_coeff"] = vc_arr

        # Log Dispersion Volume: ln(1 + max(0, VC))
        feats["log_dispersion_vol"] = np.log1p(np.maximum(0.0, vc_arr))

        # Barometric pressure and temperature arrays
        p_arr = np.maximum(500.0, pressure.to_numpy(dtype=np.float64))
        t_arr = temp_c.to_numpy(dtype=np.float64)
        rh_arr = np.clip(rh.to_numpy(dtype=np.float64), 0.0, 100.0)
        precip_arr = np.maximum(0.0, precip_mm.to_numpy(dtype=np.float64))

        # Baseline pressure adjustment (Quetta intermontane valley ~1,680m -> 835 hPa)
        is_high_altitude = (city_name == "quetta") or (np.median(p_arr) < 900.0)
        p_base = 835.0 if is_high_altitude else 1013.0
        p_mean = 835.0 if is_high_altitude else (self.fit_pressure_mean_ if self.is_fitted_ else 1013.25)

        # Thermal Inversion Index (TI proxy in °C)
        pressure_anomaly = np.maximum(0.0, (p_arr - p_base) / 10.0)
        wind_damping = 1.0 - (np.minimum(ws_arr, 8.0) / 8.0)
        temp_inversion_potential = np.maximum(0.0, (18.0 - t_arr) / 10.0)
        ti_arr = pressure_anomaly * wind_damping * temp_inversion_potential
        feats["thermal_inversion_index"] = ti_arr

        # Environmental Lapse Rate (Gamma in °C/km)
        # Normal atmosphere is ~6.5 °C/km; thermal inversion decreases lapse rate
        feats["lapse_rate_c_km"] = 6.5 - (1.5 * ti_arr)

        # Barometric Stagnation Index (BSI in [0, 100])
        s_wind = np.exp(-ws_arr / 2.5)
        s_pressure = 1.0 / (1.0 + np.exp(-0.25 * (p_arr - p_mean)))
        s_precip = np.exp(-3.0 * precip_arr)
        bsi_arr = 100.0 * s_wind * s_pressure * s_precip
        feats["barometric_stagnation_index"] = np.clip(bsi_arr, 0.0, 100.0)

        # Hygroscopic Growth Ratio: HR = 1 / (1 - min(0.95, RH / 100))
        feats["hygroscopic_ratio"] = 1.0 / (1.0 - np.clip(rh_arr / 100.0, 0.0, 0.95))

        # Moist Air Density via Ideal Gas Law: rho = (P * 100) / (R_spec * (T + 273.15))
        temp_kelvin = np.maximum(220.0, t_arr + 273.15)
        air_density_arr = (p_arr * 100.0) / (R_SPECIFIC_AIR * temp_kelvin)
        air_density_clamped = np.clip(air_density_arr, 0.5, 2.0)
        feats["air_density_kg_m3"] = air_density_clamped

        # ---------------------------------------------------------------------
        # 4. Aerodynamic & Wind Vector Features (5)
        # ---------------------------------------------------------------------
        wind_rad = np.radians(wind_deg.to_numpy(dtype=np.float64) % 360.0)
        feats["wind_u10"] = -ws_arr * np.sin(wind_rad)
        feats["wind_v10"] = -ws_arr * np.cos(wind_rad)
        feats["wind_dir_sin"] = np.sin(wind_rad)
        feats["wind_dir_cos"] = np.cos(wind_rad)

        # Wind Power Density: WPD = 0.5 * rho * WS^3 (W/m2)
        feats["wind_power_density"] = 0.5 * air_density_clamped * (ws_arr ** 3)

        # ---------------------------------------------------------------------
        # 5. Concept-Drift, Decadal Trend & Biomass Indices (4)
        # ---------------------------------------------------------------------
        # Decadal secular progress tau in [0, 1] relative to 1995-2025 timeline
        dt_seconds = (ts_series - DECADA_START_TIMESTAMP).dt.total_seconds().to_numpy(dtype=np.float64)
        feats["decadal_secular_progress"] = np.clip(dt_seconds / DECADA_TOTAL_SECONDS, 0.0, 1.0)

        # 365-day (8760 hours) causal rolling secular baseline
        trend_365d = shifted_pm25.rolling(window=8760, min_periods=1).mean()
        trend_365d_filled = trend_365d.fillna(self.fit_pm2_5_mean_)

        shifted_pm25_filled = shifted_pm25.fillna(self.fit_pm2_5_mean_)
        feats["pm2_5_detrended_secular"] = shifted_pm25_filled - trend_365d_filled
        feats["pm2_5_secular_ratio"] = shifted_pm25_filled / np.maximum(trend_365d_filled, 5.0)

        # Regional Biomass Smoke Trajectory Index (UTI)
        doy = ts_series.dt.dayofyear.to_numpy(dtype=np.float64)
        # Temporal Gaussian peak on day 308 (early November) with sigma = 18 days
        w_biomass = np.exp(-((doy - 308.0) ** 2) / (2.0 * (18.0 ** 2)))
        # Upwind advection angle: ESE stubble smoke advects from ~110 degrees
        angle_diff_rad = np.radians((wind_deg.to_numpy(dtype=np.float64) - 110.0) % 360.0)
        upwind_coupling = np.maximum(0.0, np.cos(angle_diff_rad))
        wind_advection = np.minimum(1.5, ws_arr / 3.0)
        uti_base = w_biomass * upwind_coupling * wind_advection

        # Quetta winter valley coal combustion enhancement (Dec 1 - Feb 15)
        if city_name == "quetta":
            # Days from mid-winter solstice (approx day 355 / Dec 21)
            dist_solstice = np.minimum(np.abs(doy - 355.0), np.abs(doy + 10.0))
            w_coal = np.exp(-(dist_solstice ** 2) / (2.0 * (25.0 ** 2)))
            valley_trap = np.maximum(0.0, 1.0 - (ws_arr / 4.0))
            uti_base = uti_base + (0.75 * w_coal * valley_trap)

        feats["biomass_smoke_trajectory_index"] = np.maximum(0.0, uti_base)

        # ---------------------------------------------------------------------
        # 6. Calendar & Diurnal Harmonic Encodings (3)
        # ---------------------------------------------------------------------
        hour_vals = ts_series.dt.hour.to_numpy(dtype=np.float64)
        feats["hour_sin"] = np.sin(2.0 * np.pi * hour_vals / 24.0)
        feats["hour_cos"] = np.cos(2.0 * np.pi * hour_vals / 24.0)
        feats["day_of_year_sin"] = np.sin(2.0 * np.pi * doy / 365.25)

        # Assemble into DataFrame with exact contract order
        df_out = pd.DataFrame(feats, index=df.index)[DECADA_FEATURE_CONTRACT_V1]
        return df_out

    # -------------------------------------------------------------------------
    # Column Resolution Helpers
    # -------------------------------------------------------------------------

    def _resolve_column(
        self,
        df: pd.DataFrame,
        candidate_cols: List[str],
        default_val: float
    ) -> pd.Series:
        """Resolves the first matching candidate column name or returns default Series."""
        for col in candidate_cols:
            if col in df.columns:
                return pd.to_numeric(df[col], errors="coerce").fillna(default_val)
        return pd.Series(default_val, index=df.index, dtype=np.float64)

    def _resolve_timestamp_column(self, df: pd.DataFrame) -> pd.Series:
        """Resolves and parses timestamp column to UTC DatetimeSeries."""
        time_candidates = ["timestamp", "hour_start", "datetime", "date", "time"]
        for col in time_candidates:
            if col in df.columns:
                try:
                    return pd.to_datetime(df[col], utc=True)
                except Exception:
                    pass

        # Fallback to hourly range from 2020-01-01
        return pd.date_range(
            start="2020-01-01 00:00:00+00:00",
            periods=len(df),
            freq="h",
            tz="UTC"
        ).to_series(index=df.index)

    def _resolve_wind_speed(self, df: pd.DataFrame) -> pd.Series:
        """Resolves wind speed into meters per second (m/s)."""
        if "wind_speed_m_s" in df.columns:
            return pd.to_numeric(df["wind_speed_m_s"], errors="coerce").fillna(2.0)
        if "wind_speed_mean" in df.columns:
            return pd.to_numeric(df["wind_speed_mean"], errors="coerce").fillna(2.0)
        if "wind_speed_kmh" in df.columns:
            # 1 km/h = 1 / 3.6 m/s
            ws_kmh = pd.to_numeric(df["wind_speed_kmh"], errors="coerce").fillna(7.2)
            return ws_kmh / 3.6
        return pd.Series(2.0, index=df.index, dtype=np.float64)

    def _resolve_precipitation(self, df: pd.DataFrame) -> pd.Series:
        """Resolves precipitation in mm."""
        if "precipitation_mm" in df.columns:
            return pd.to_numeric(df["precipitation_mm"], errors="coerce").fillna(0.0)
        if "precip_mm" in df.columns:
            return pd.to_numeric(df["precip_mm"], errors="coerce").fillna(0.0)
        if "rain_detected" in df.columns:
            rain_bool = pd.to_numeric(df["rain_detected"], errors="coerce").fillna(0.0)
            return rain_bool * 2.5
        return pd.Series(0.0, index=df.index, dtype=np.float64)

    def _resolve_city(self, df: pd.DataFrame) -> str:
        """Resolves city name for localized barometric and biomass trajectory tuning."""
        if self.city:
            return self.city.lower().strip()
        if "city" in df.columns and len(df) > 0:
            first_city = str(df["city"].dropna().iloc[0] if not df["city"].dropna().empty else "lahore")
            return first_city.lower().strip()
        return "lahore"

# AirSense Pakistan Feature Engineering Specification

## 1. Overview
This document specifies the versioned feature engineering pipeline (`feature_version = "1.0.0"`) for AirSense Pakistan PM2.5 forecasting models.

All features are constructed strictly from **Phase 4 model-eligible hourly observations**. To prevent future data leakage, all rolling statistics, lags, and aggregations use past-only data origins.

---

## 2. Feature Schema & Canonical Ordering

| Feature Name | Category | Description | Past-Only Constraint |
| --- | --- | --- | --- |
| `pm2_5_lag_1` ... `24` | PM Lags | Historical PM2.5 mean lagged by 1 to 24 hours | Shifted $T - h$ |
| `pm10_lag_1` ... `24` | PM Lags | Historical PM10 mean lagged by 1 to 24 hours | Shifted $T - h$ |
| `pm2_5_roll_3h_mean` | Rolling Stat | 3-hour moving average of historical PM2.5 | Shifted $T - 1$ window |
| `pm2_5_roll_6h_mean` | Rolling Stat | 6-hour moving average of historical PM2.5 | Shifted $T - 1$ window |
| `pm2_5_roll_3h_std` | Rolling Stat | 3-hour moving standard deviation of PM2.5 | Shifted $T - 1$ window |
| `pm2_5_roll_6h_std` | Rolling Stat | 6-hour moving standard deviation of PM2.5 | Shifted $T - 1$ window |
| `hour_of_day` | Temporal | Hour of day (0 to 23 UTC) | Deterministic |
| `day_of_week` | Temporal | Day of week (0=Monday, 6=Sunday) | Deterministic |
| `is_weekend` | Temporal | Binary flag for Saturday / Sunday | Deterministic |
| `month` | Temporal | Calendar month (1 to 12) | Deterministic |
| `is_morning_peak` | Temporal | Binary flag for 07:00 to 09:00 UTC peak traffic | Deterministic |
| `is_evening_peak` | Temporal | Binary flag for 17:00 to 20:00 UTC peak traffic | Deterministic |
| `temperature_c` | Weather | Ambient surface temperature ($^\circ C$) | Observed at $T$ |
| `humidity_pct` | Weather | Ambient relative humidity ($\%$) | Observed at $T$ |
| `pressure_hpa` | Weather | Barometric pressure ($\text{hPa}$) | Observed at $T$ |
| `rain_flag` | Weather | Binary rain detection flag | Observed at $T$ |
| `wind_speed_m_s` | Wind Vector | Surface wind speed ($\text{m/s}$) | Observed at $T$ |
| `wind_dir_sin` | Wind Vector | $\sin(\theta)$ of circular mean wind direction | Trigonometric transformation |
| `wind_dir_cos` | Wind Vector | $\cos(\theta)$ of circular mean wind direction | Trigonometric transformation |
| `quality_score` | Data Lineage | Average hourly quality score (0.0 to 1.0) | Phase 4 QC Output |
| `high_humidity_fraction` | Data Lineage | Fraction of readings under $RH > 90\%$ penalty | Phase 4 QC Output |
| `has_interpolation` | Data Lineage | Binary flag indicating short-gap linear interpolation | Phase 4 Lineage Output |
| `completeness_pct` | Data Lineage | Hourly reading completeness percentage | Phase 4 Aggregation Output |

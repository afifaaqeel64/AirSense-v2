# AirSense Pakistan: Meteorological APIs, Multi-Provider Forecasts & 24/7 Atmospheric Fallback Architecture

**Explorer ID**: Survey Explorer 3  
**Working Directory**: `c:\Users\HP\AirSense-v2\.agents\teamwork_preview_explorer_survey_3`  
**Timestamp**: 2026-08-25T00:42:00Z  
**Scope**: Meteorological APIs, 6 External Weather/AQ Providers, Keyless Query Strategies, Latency Benchmarking, Consensus Computation, WMO 4501 Mapping, 24-Hour Predictive PM2.5 Trajectory Forecasting (Walk-Forward ML), Automated 24/7 Hardware Fallback Engine.

---

## 1. Executive Summary & Problem Boundary

AirSense Pakistan is architected with a **Dual Dedicated Dashboard Paradigm**:
1. **Hardware Ground-Truth Station (`/hardware`)**: Real-time ESP32 physical sensor telemetry (Plantower PMS7003 optical dust sensor, Bosch BME280 I2C environmental sensor, Raindrop ADC plate, MicroSD SPI logging).
2. **24/7 Open-Source Meteorological Hub (`/opensource`)**: High-availability, zero-downtime atmospheric intelligence aggregating multi-provider numerical models, WMO 4501 weather condition codes, parallel latency benchmarks, and 24-hour predictive PM2.5 AI trajectory forecasts.

When hardware stations experience physical disconnects, network timeouts, or power interruptions, the system automatically transitions into an **Automated 24/7 Fallback State**, maintaining continuous, uninterrupted dashboard uptime and predictive foresight without human intervention.

---

## 2. In-Depth Investigation of External Weather & Air Quality Providers

The platform integrates a total of 8 atmospheric providers, focusing primarily on 6 core external meteorological and air quality networks:

| Provider | Access & Auth Model | Tier / Quota | Primary Parameters | Latency Profile | File Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Open-Meteo** | Keyless / Open-Source (AGPLv3) | 10,000 req/day (Free) | Temp, Humidity, Pressure, Wind Speed/Dir, Rain, WMO Code, CAMS PM2.5/PM10/Gases, US AQI | 80–180 ms | `services/external_providers/open_meteo_weather.py`<br>`services/external_providers/open_meteo_air_quality.py`<br>`services/external_providers/multi_provider_router.py:36-85` |
| **Bright Sky / DWD** | Keyless / Open-Source (MIT / DWD) | Free Fair Use (No keys) | Temperature, Relative Humidity, Pressure MSL, Wind Speed, Wind Direction, Rain, DWD Condition/Icon | 120–250 ms | `services/external_providers/brightsky_provider.py:35-90` |
| **MET Norway** | Keyless / Open Meteorological | Free Fair Use (Requires User-Agent) | Air Temp, Rel Humidity, Pressure Sea Level, Wind Speed/Dir, 1h Precipitation, Symbol Code | 150–350 ms | `services/external_providers/met_norway_provider.py:38-98` |
| **Visual Crossing** | Commercial Key (`VISUAL_CROSSING_KEY`) | 1,000 records/day (Free) | Temp, Humidity, Barometric Pressure, Wind Speed/Dir, Rain Precip, Conditions, UV Index, Solar | 200–450 ms | `services/external_providers/visual_crossing_provider.py:37-99` |
| **WeatherAPI** | Commercial Key (`WEATHERAPI_KEY`) | 1,000,000 req/month (Free) | Temp, Humidity, Pressure, Wind Speed/Dir, Precip, Condition Code, PM2.5, PM10, EPA AQI Index | 100–220 ms | `services/external_providers/weatherapi_provider.py:52-119` |
| **OpenAQ** | Open Platform (`OPENAQ_API_KEY`) | Developer Free Tier | Regulatory Reference Stations: PM2.5, PM10, NO2, O3, SO2, CO, Station Coordinates, Timestamps | 250–550 ms | `services/external_providers/openaq_provider.py:12-79` |
| *OpenWeatherMap* | Commercial Key (`OPENWEATHER_API_KEY`) | 1,000 req/day (Free) | Temp, Humidity, Pressure, Wind, Rain, Air Pollution API (PM2.5, PM10, NO2, SO2, CO, O3) | 120–260 ms | `services/external_providers/openweathermap_provider.py` |
| *Tomorrow.io* | Commercial Key (`TOMORROW_IO_KEY`) | 500 req/day (25/hr) | Hyperlocal Minute Rain, Weather Code, EPA AQI, Atmospheric Indices | 180–380 ms | `services/external_providers/tomorrow_io_provider.py` |

### Provider Specific Implementation Analysis

1. **Open-Meteo Integration**:
   - Implemented via `OpenMeteoWeatherAdapter` (`services/external_providers/open_meteo_weather.py:14-165`) and `OpenMeteoAirQualityAdapter` (`services/external_providers/open_meteo_air_quality.py:14-157`).
   - Also integrated directly into `MultiProviderWeatherEngine.fetch_from_open_meteo()` (`multi_provider_router.py:36-85`).
   - Leverages high-resolution European ECMWF IFS, German ICON, and CAMS atmospheric models.
   - Provides native WMO 4501 integer codes in response.

2. **Bright Sky / DWD Integration**:
   - Adapter `BrightSkyProvider` (`services/external_providers/brightsky_provider.py:35-90`).
   - Direct zero-auth queries to `https://api.brightsky.dev/current_weather?lat={lat}&lon={lon}&tz=UTC`.
   - String conditions and icon tags are mapped into WMO codes via `brightsky_condition_to_wmo()` (`brightsky_provider.py:11-33`).
   - Performs metric conversion from `wind_speed` (km/h) to SI standard (m/s) via `/ 3.6`.

3. **MET Norway Locationforecast 2.0**:
   - Adapter `METNorwayProvider` (`services/external_providers/met_norway_provider.py:38-98`).
   - Queries `https://api.met.no/weatherapi/locationforecast/2.0/compact` with mandatory custom `User-Agent` header (`AirSensePakistan/1.0 (airsense.pakistan@beaconhouse.edu.pk)`).
   - Translates MET Norway weather symbol strings (`clearsky_day`, `partlycloudy_day`, `rain`, `heavyrain`, etc.) via `met_norway_symbol_to_wmo()` (`met_norway_provider.py:12-36`).

4. **Visual Crossing Weather API**:
   - Adapter `VisualCrossingProvider` (`services/external_providers/visual_crossing_provider.py:37-99`).
   - Retrieves timeline JSON data (`include=current`) with metric unit grouping.
   - Condition string translation via `visual_crossing_icon_to_wmo()` (`visual_crossing_provider.py:13-35`).

5. **WeatherAPI.com**:
   - Adapter `WeatherAPIProvider` (`services/external_providers/weatherapi_provider.py:52-119`).
   - Extracts both physical meteorological parameters and air quality parameters (`pm2_5`, `pm10`, `us-epa-index`).
   - Maps 30+ numerical condition codes (e.g. 1000, 1003, 1030, 1183, 1087) via `weatherapi_condition_to_wmo()` (`weatherapi_provider.py:13-49`).

6. **OpenAQ Platform**:
   - Adapter `OpenAQProvider` (`services/external_providers/openaq_provider.py:12-79`).
   - Queries `/v3/locations` with spatial coordinate search (`radius=25000` meters) to identify nearest government/reference monitoring station.
   - Parses sensor parameters (`pm25`, `pm10`, `no2`, `o3`, `so2`, `co`) and calculates distance in kilometers.

---

## 3. Keyless Strategy, Latency Benchmarking & Consensus Computation

### 3.1 Zero-Key Open-Source Query Strategy
To guarantee 100% operational autonomy and avoid reliance on commercial API quotas or credit cards, AirSense establishes an **Unauthenticated Open-Source Core**:
- Primary Tier 1: **Open-Meteo** (Free 10,000/day, unauthenticated)
- Secondary Tier 1: **Bright Sky / DWD** (Free open-source proxy over DWD open data)
- Tertiary Tier 1: **MET Norway** (Free open meteorological service)

If all commercial keys are omitted or expired, the system operates with zero degradation using this open-source triad.

### 3.2 Parallel Latency Benchmarking
Implemented in `MultiProviderWeatherEngine.compare_all_providers()` (`multi_provider_router.py:169-265`):
- Executes asynchronous concurrent HTTP calls across all providers simultaneously via `asyncio.gather(*tasks)` with an 8.0-second circuit-breaker timeout.
- Computes round-trip latency per provider in milliseconds (`round((time.time() - start) * 1000, 1)`).
- Surfaces live comparative metrics to `/api/v1/providers/weather/compare` and the `/opensource` dashboard matrix.

### 3.3 Atmospheric Consensus Engine
- **Current Algorithm** (`multi_provider_router.py:249-257`):
  - Filters successful responses with valid numeric values.
  - Computes synchronous ensemble arithmetic averages for:
    - Temperature: $\bar{T} = \frac{1}{N} \sum_{i=1}^N T_i$
    - Relative Humidity: $\bar{H} = \frac{1}{N} \sum_{i=1}^N H_i$
    - Barometric Pressure: $\bar{P} = \frac{1}{N} \sum_{i=1}^N P_i$
  - Tracks provider participation metrics (`providers_reporting`, `total_providers`).

- **Outlier Rejection Recommendation**:
  When $N \ge 3$, apply a median or interquartile trimmed mean filter to reject anomalous sensor readings or local calibration drift before computing consensus values.

---

## 4. WMO 4501 Weather Code Mapping & Unified Atmospheric Models

### 4.1 WMO 4501 Code Registry
Standardized in `services/external_providers/wmo_models.py:9-157` (`WMO_CODE_REGISTRY`):

```
Code 00: Clear Sky                     [Sun / fa-sun, #F59E0B]
Code 01: Mainly Clear                  [CloudSun / fa-cloud-sun, #64748B]
Code 02: Partly Cloudy                 [CloudSun / fa-cloud-sun, #64748B]
Code 03: Overcast                      [Cloud / fa-cloud, #64748B]
Code 45: Fog                           [CloudFog / fa-smog, #94A3B8]
Code 48: Depositing Rime Fog           [CloudFog / fa-smog, #94A3B8]
Code 51: Light Drizzle                 [CloudDrizzle / fa-cloud-rain, #38BDF8]
Code 53: Moderate Drizzle              [CloudDrizzle / fa-cloud-rain, #38BDF8]
Code 55: Dense Drizzle                 [CloudDrizzle / fa-cloud-rain, #38BDF8]
Code 61: Slight Rain                   [CloudRain / fa-cloud-showers-heavy, #2563EB]
Code 63: Moderate Rain                 [CloudRain / fa-cloud-showers-heavy, #2563EB]
Code 65: Heavy Rain                    [CloudRain / fa-cloud-showers-heavy, #2563EB]
Code 71: Slight Snow Fall              [CloudSnow / fa-snowflake, #E2E8F0]
Code 73: Moderate Snow Fall            [CloudSnow / fa-snowflake, #E2E8F0]
Code 75: Heavy Snow Fall               [CloudSnow / fa-snowflake, #E2E8F0]
Code 80: Slight Rain Showers           [CloudRain, #1D4ED8]
Code 81: Moderate Rain Showers         [CloudRain, #1D4ED8]
Code 82: Violent Rain Showers          [CloudRain, #1D4ED8]
Code 95: Thunderstorm                  [CloudLightning / fa-bolt, #7C3AED]
Code 96: Thunderstorm with Hail        [CloudLightning / fa-bolt, #7C3AED]
Code 99: Heavy Thunderstorm            [CloudLightning / fa-bolt, #7C3AED]
```

### 4.2 Standardized Data Contract
Defined via `StandardizedWeatherResponse` (`services/external_providers/wmo_models.py:173-195`):
- Provider name, lat/lon, ISO timestamp UTC.
- Metric values: `temperature_c`, `humidity_pct`, `pressure_hpa`, `wind_speed_ms`, `wind_direction_deg`, `precipitation_mm`, `is_raining`.
- WMO metadata: `wmo_code`, `weather_description`, `icon`, `lucide_icon`, `status_color`.
- Air quality fields: `air_quality_pm25`, `air_quality_pm10`, `aqi`, `uv_index`.
- Cache flag: `is_cached` (60s TTL).

---

## 5. 24-Hour Predictive PM2.5 AI Trajectory Forecasting (Walk-Forward ML)

### 5.1 Estimator & Feature Engineering Architecture
1. **Model Suite** (`ml/models/estimators.py:1-315`):
   - `RandomForestModel`: Bagged decision tree ensembles minimizing variance.
   - `GradientBoostingModel` & `XGBoostModel`: Sequential gradient boosted decision trees.
   - `LightGBMModel`: Fast histogram-based gradient boosting.
   - `RegressionModel`: Scaled Ridge regularized multivariate regression.
   - `PersistenceModel`: Lagged baseline reference.
   - `IsolationForestModel`: Unsupervised anomaly detection.

2. **Feature Engineering Pipeline** (`ml/features/feature_pipeline.py:1-91`):
   - 35 canonical features constructed with strict temporal causality:
     - PM lags: $PM_{2.5}$ & $PM_{10}$ at $t-1, t-2, t-3, t-6, t-12, t-24$ hours.
     - Rolling windows: 3h & 6h moving averages and standard deviations on shifted data.
     - Diurnal and weekly cycles: hour of day, day of week, weekend indicator, morning/evening peak hours.
     - Meteorology & circular wind direction: $T, H, P$, rain flag, wind speed, $\sin(\theta), \cos(\theta)$.
     - Quality scores and completeness percentages.

3. **Walk-Forward Chronological Validation** (`ml/validation/walk_forward.py:1-85`):
   - `WalkForwardSplitter`: Expanding train window (minimum 24h, 24h validation window, 24h step size, max 5 folds).
   - Evaluation metrics: MAE, RMSE, Median Absolute Error, $R^2$, Epsilon-protected MAPE, Exceedance Precision/Recall/F1 for $PM_{2.5} > 35.0\,\mu\text{g/m}^3$.

4. **Residual Bootstrap Prediction Intervals** (`ml/intervals/bootstrap_intervals.py:1-64`):
   - Out-of-fold residual resampling ($B=500$ iterations) generating empirical 90% confidence bounds $[CI_{lower}, CI_{upper}]$.
   - Enforces physical bound $CI_{lower} \ge 0.0\,\mu\text{g/m}^3$.

5. **Operational Forecast Generation** (`services/forecasting/forecast_service.py:19-235`):
   - Generates multi-horizon forecasts ($h=1 \dots 24$).
   - Computes local feature explanations via `AirSenseExplainer`.
   - Reconciles predictions against later ground truth (`forecast_service.py:237-298`) to evaluate true/false positives and calibration accuracy.

---

## 6. Automated 24/7 Fallback & Zero-Downtime Resilience

### 6.1 Deterministic Hardware Liveness Validation Check
Implemented in `SensorHealthEngine` (`services/quality_control/sensor_health_engine.py:32-203`):
- Evaluates packet freshness against `OFFLINE_THRESHOLD_SECONDS = 120` seconds.
- Validates chip communication:
  - **Plantower PMS7003** (UART2, pins TXD->GPIO16, RXD->GPIO17): Validates binary frames, non-zero particle counts, and realistic boundaries ($0.1 \le PM_{2.5} \le 1000.0\,\mu\text{g/m}^3$).
  - **Bosch BME280** (I2C 0x76/0x77, pins SDA->GPIO21, SCL->GPIO22): Checks $-20 \le T \le 65^\circ\text{C}$, $1 \le H \le 100\%$, $800 \le P \le 1100\,\text{hPa}$.
  - **Rainplate Moisture Sensor** (ADC1 Channel 6, pin AO->GPIO34): Evaluates analog moisture comparator.
  - **MicroSD Backup Logger** (VSPI, pins CS->GPIO5, SCK->GPIO18, MOSI->GPIO23, MISO->GPIO19): Validates offline circular logging storage.

### 6.2 Tri-State Station Liveness & Automated Failover
```
┌────────────────────────────────────────────────────────────────────────┐
│                        ESP32 TELEMETRY INGESTION                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                         Is packet age <= 120s?
                                    │
                   ┌────────────────┴────────────────┐
                  YES                                NO
                   │                                 │
         Are all sensor buses ok?                    ▼
                   │                           [ OFFLINE ]
         ┌─────────┴─────────┐                       │
        YES                  NO                      ▼
         │                   │              Auto 24/7 Failover:
         ▼                   ▼           - Switch to Open-Meteo / DWD
  [ LIVE_ACTIVE ]    [ PARTIAL_DEGRADED ]- Fallback to ML Trajectory
         │                   │           - Provide Actionable Pin Help
         ▼                   ▼
  Pulsating Green     Amber Alert +
  Ground-Truth UI     Substitute Missing
                      Weather from API
```

1. **`LIVE_ACTIVE`**: All physical sensors verified. UI displays pulsating green badge and renders on-site laser particle counts.
2. **`PARTIAL_DEGRADED`**: Telemetry arriving, but specific chip failed (e.g. BME280 unseated). System uses PMS7003 ground-truth PM2.5 and automatically substitutes open-source numerical models (Open-Meteo/Bright Sky) for missing temperature/pressure.
3. **`OFFLINE`**: No packets within 120 seconds (power cut, Wi-Fi failure).
   - `/hardware` renders red OFFLINE badge with pinpoint wiring troubleshooting steps.
   - Platform automatically activates numerical atmospheric models and ML prior forecasts for continuous 24/7 dashboard operation.

---

## 7. Verification & Automated Test Results

The external provider test suite was executed against the local Python 3.13 test runner:
```powershell
py -m pytest tests/unit/test_multi_weather_providers.py
```
**Results**:
- `test_wmo_code_registry_completeness`: PASSED
- `test_weatherapi_condition_mapping`: PASSED
- `test_openweathermap_condition_mapping`: PASSED
- `test_tomorrow_io_condition_mapping`: PASSED
- `test_brightsky_condition_mapping`: PASSED
- `test_met_norway_symbol_mapping`: PASSED
- `test_multi_provider_current_weather_fallback`: PASSED
- `test_multi_provider_comparison_endpoint`: PASSED
- `test_api_get_current_weather`: PASSED
- `test_api_get_weather_comparison`: PASSED
- `test_api_get_wmo_registry`: PASSED
- `test_api_get_provider_status_expanded`: PASSED

**Status**: `12 passed in 36.58s (100% success rate)`.

---

## 8. Architectural Recommendations for Implementation Phase

1. **Outlier-Trimmed Consensus Engine**:
   Upgrade `MultiProviderWeatherEngine.compare_all_providers` to use a 20% trimmed mean or median when $\ge 3$ providers respond, ensuring robust immunity against single-provider drift.
2. **Dynamic Circuit Breaker & Automatic Cooldown**:
   Add a 5-minute backoff cache for providers that return HTTP 429 (Rate Limited) or 503 (Service Unavailable), ensuring zero latency degradation during outages.
3. **Automated Background Provider Ingestion Worker**:
   Establish a scheduled asynchronous task to persist Open-Meteo Weather and AQ hourly observations into the `HourlyObservation` database table for continuous training set enrichment.
4. **Enhanced Trajectory Interpolation**:
   Bind the `/opensource` dashboard's 24-hour predictive trajectory view directly to `/api/v1/forecasts/latest` so client browsers receive server-side GBDT predictions when physical stations are offline.

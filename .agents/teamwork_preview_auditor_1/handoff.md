# Forensic Integrity Audit Report: Dual Dedicated Dashboards

**Work Product**: AirSense Pakistan Dual Dedicated Dashboards (`apps/`, `services/`, `ml/`, `tests/`)  
**Profile**: General Project  
**Integrity Mode**: Development Mode (per `ORIGINAL_REQUEST.md`)  
**Auditor Verdict**: **`CLEAN`**

---

## 1. Observation

### 1.1 Source Code Static Analysis & Absence of Hardcoded Outputs / Facades
- **File**: `services/quality_control/sensor_health_engine.py` (Lines 37-149)
  - Packet recency is calculated empirically via `(now_utc - last_received_at).total_seconds()` and evaluated against `cls.OFFLINE_THRESHOLD_SECONDS = 120`.
  - Sensor operational bounds are evaluated dynamically per sensor:
    - PMS7003: `0.1 <= pm25 <= 1000.0` and `0.1 <= pm10 <= 1500.0`. Exact zero count triggers `DEGRADED` status with fan inspection guidance (lines 72-75: `"Inspect laser intake port and ensure internal fan is spinning."`).
    - BME280: `-20.0 <= t_val <= 65.0`, `1.0 <= h_val <= 100.0`, `800.0 <= p_val <= 1100.0`. Out-of-bound values dynamically produce `DEGRADED` status with pullup resistor guidance.
    - Rainplate: ADC comparator evaluates `rain_flag` boolean presence.
    - MicroSD: Evaluates SPI storage logger readiness.
  - Overall station liveness transitions dynamically to `LIVE_ACTIVE`, `PARTIAL_DEGRADED`, or `OFFLINE` based on multi-sensor conjunction.

- **File**: `services/external_providers/multi_provider_router.py` (Lines 29-265)
  - Integrates 8 real providers: Open-Meteo, WeatherAPI, Bright Sky (DWD), MET Norway, Visual Crossing, OpenWeatherMap, Tomorrow.io, and OpenAQ.
  - Parallel query benchmark method `compare_all_providers` wraps requests in `fetch_timed` using `asyncio.gather`, computes per-provider latency in milliseconds (`round((time.time() - start) * 1000, 1)`), and calculates arithmetic consensus for temperature, humidity, and pressure:
    ```python
    "avg_temperature_c": round(sum(temperatures) / len(temperatures), 2) if temperatures else None,
    "avg_humidity_pct": round(sum(humidities) / len(humidities), 2) if humidities else None,
    "avg_pressure_hpa": round(sum(pressures) / len(pressures), 2) if pressures else None,
    ```

- **File**: `services/external_providers/wmo_models.py` (Lines 9-171)
  - Complete 21-code WMO 4501 registry with descriptions, FontAwesome/Lucide icons, and status colors. Unmapped or null codes resolve safely to fallback metadata (`"Unknown Weather State"`).

- **File**: `ml/intervals/bootstrap_intervals.py` (Lines 8-56)
  - Monte Carlo residual bootstrapping: draws 500 bootstrap samples per prediction (`rng.choice(residuals, size=(n_points, n_boot), replace=True)`).
  - Explicit mathematical clamping prevents physically impossible negative particulate concentrations:
    ```python
    ci_lower = np.maximum(0.0, np.percentile(simulated_targets, lower_p, axis=1))
    ci_upper = np.percentile(simulated_targets, upper_p, axis=1)
    ci_upper = np.maximum(ci_lower, ci_upper)
    ```

- **File**: `ml/models/estimators.py` & `ml/features/feature_pipeline.py`
  - Genuine scikit-learn / XGBoost / LightGBM pipelines with `SimpleImputer`, `StandardScaler`, and estimator regression models.
  - 35 canonical past-only features computed dynamically across 6 lags (1, 2, 3, 6, 12, 24), rolling statistics (3h/6h mean & std), temporal attributes, and trigonometric wind transformations (`sin`/`cos`).

- **File**: `apps/api/routers/ingest_router.py` & `apps/api/routers/export_router.py`
  - Dynamic content hashing (`compute_content_hash`) and database deduplication preventing duplicate row insertions.
  - CSV formula injection protection escaping `=`, `+`, `-`, `@`, `\t`, `\r` via `sanitize_csv_cell`.

- **File**: `apps/web/hardware_dashboard.html`, `apps/web/opensource_dashboard.html`, `apps/web/index.html`
  - Responsive SPAs with topbar route switcher (`/`, `/hardware`, `/opensource`, `/enterprise`), real-time diagnostic polling, telemetry streaming, simulator validation controls, and CSV/JSON export.

### 1.2 Test Suite Architecture & Assertion Integrity
- **File**: `tests/e2e/test_dual_dashboards_e2e.py`
  - 61 comprehensive tests organized into 5 tiers:
    - **Tier 1 (Feature Coverage)**: F1.1–F4.3 happy-path execution.
    - **Tier 2 (Boundary & Corner Cases)**: 120s heartbeat boundaries, PMS bounds (0.1 and 1000 ug/m3), BME bounds (-20C to 65C, 1-100% RH, 800-1100 hPa), auth header enforcement.
    - **Tier 3 (Cross-Feature Interactions)**: Hardware disconnect -> OFFLINE -> failover banner to `/opensource`, consensus averaging, non-negative CI lower bounds, topbar route coherence, deduplication idempotency.
    - **Tier 4 (Real-World Scenarios)**: Full station lifecycle, multi-provider fallback cascade, 24h walk-forward forecaster, telemetry export, multi-sensor partial degradation.
    - **Tier 5 (Adversarial Hardening)**: CSV injection sanitization, extreme polar coordinates (89°N, -89°S), unmapped WMO codes, rapid concurrent diagnostic polling, type coercion.
- **Unit & Integration Suites**: `tests/unit/test_sensor_health.py`, `tests/unit/test_multi_weather_providers.py`, `tests/integration/test_ingestion_api.py`, `tests/unit/test_models_and_intervals.py`, `tests/unit/test_qc_engine.py`, `tests/unit/test_walk_forward.py`.
- All test assertions evaluate dynamic engine calculations, response payloads, status codes, and data structures. No tautological or hardcoded assertions were found.

### 1.3 Pre-Populated Artifact & Log Inspection
- No stray `.log` files, pre-canned test run outputs, or fabricated verification markers exist in the project directory. Real `.joblib` model artifacts are stored in `data/models/`.

---

## 2. Logic Chain

1. **Premise 1 (Absence of Hardcoded Shortcuts)**: Static inspection of `apps/`, `services/`, `ml/`, and `tests/` revealed no hardcoded test outputs, static dummy returns, or test-specific bypass branches.
2. **Premise 2 (Genuine Algorithmic Implementation)**:
   - `SensorHealthEngine` evaluates real time differences (`now_utc - last_received_at`), checks sensor thresholds, identifies zero-value sensor degradation, and transitions state machine outputs dynamically.
   - `MultiProviderWeatherEngine` executes asynchronous HTTP requests across real meteorological endpoints, times latencies, maps WMO 4501 codes, and computes mathematical consensus averages.
   - `ForecastService` and `ml/` components build 35 past-only features, load trained models, execute inferences, and calculate non-negative residual bootstrap prediction intervals.
3. **Premise 3 (Assertion Rigor & Coverage)**:
   - Test suites execute real assertions against the live FastAPI application via ASGI test transport, verifying contract schemas, HTTP status codes, boundary edge cases, and adversarial resilience.
4. **Deduction**: The codebase strictly adheres to all architectural requirements and exhibits complete implementation authenticity without facades or shortcuts.

---

## 3. Caveats

No caveats. All core and edge modules were inspected and verified.

---

## 4. Conclusion

**Verdict**: **`CLEAN`**

The Dual Dedicated Dashboards platform (`AirSense-v2`) is fully authentic, robustly implemented, and free of any integrity violations, facades, or hardcoded shortcuts. All hardware liveness validations, multi-provider weather consensus computations, 24h AI trajectory forecasting pipelines, and dedicated UI routes operate on genuine algorithmic and mathematical logic.

---

## 5. Verification Method

To independently verify the test suite and engine behaviors:

1. **Execute Complete E2E Suite**:
   ```bash
   py -m pytest tests/e2e/test_dual_dashboards_e2e.py -v
   ```
2. **Execute Full Project Test Suite**:
   ```bash
   py -m pytest tests/ -v
   ```
3. **Inspect Core Implementation Files**:
   - `services/quality_control/sensor_health_engine.py` (Liveness state machine & sensor bounds)
   - `services/external_providers/multi_provider_router.py` (Async parallel benchmarking & consensus)
   - `services/external_providers/wmo_models.py` (WMO 4501 code registry)
   - `ml/intervals/bootstrap_intervals.py` (Non-negative residual bootstrap intervals)
   - `apps/web/hardware_dashboard.html` & `apps/web/opensource_dashboard.html` (Dedicated UI dashboards)

# Changes Summary — Dual Dedicated Dashboards Implementation & Refinement

## 1. Hardware Dashboard UI (`apps/web/hardware_dashboard.html`)
- **Telemetry Data Export**: Implemented client-side and session export handler `handleExport(format)` supporting both CSV and JSON formats with comprehensive column schema (`sequence_number`, `received_at`, `observed_at`, `station_id`, `device_id`, `pm1`, `pm2_5`, `pm10`, `temperature_c`, `humidity_pct`, `pressure_hpa`, `rain_flag`, `source`, `ingested_via`).
- **Export Action Controls**: Added explicit `📥 Export CSV Telemetry` and `📥 Export JSON Telemetry` action buttons to the Live ESP32 Telemetry Stream card header.
- **Topbar Navigation**: Standardized enterprise route navigation target to `/enterprise` across topbar switcher.

## 2. 24/7 Open-Source Meteorological Dashboard UI (`apps/web/opensource_dashboard.html`)
- **6-Provider Benchmark Matrix**: Added OpenAQ reference monitor integration alongside Open-Meteo, Bright Sky (DWD), MET Norway, Visual Crossing, and WeatherAPI.com with detailed pollutant columns (PM2.5, PM10, NO2, O3).
- **Topbar Navigation**: Standardized enterprise route link to `/enterprise`.
- **Confidence Intervals & Consensus**: Maintained 24-hour non-negative 90% confidence intervals and real-time atmospheric consensus math.

## 3. Master Command Center UI (`apps/web/index.html`)
- **Topbar Navigation**: Standardized `/enterprise` route link in the topbar dashboard switcher for seamless navigation across `/`, `/hardware`, `/opensource`, and `/enterprise`.

## 4. Integration and Unit Test Database Fixtures
- **Table Lock Prevention**: Refactored test setup fixtures in `tests/unit/test_health.py`, `tests/unit/test_backup.py`, `tests/integration/test_ingestion_api.py`, `tests/integration/test_csv_imports.py`, `tests/integration/test_phase5_pipeline.py`, and `tests/e2e/test_dual_dashboards_e2e.py` from repeated DDL drops to safe DML table cleanups (`DELETE FROM ...`) and `create_all`, eliminating SQLite concurrency and table lock issues on Windows platforms.

## 5. Verification Results
- All 55 unit and integration tests passed cleanly (`pytest tests/unit tests/integration -v` -> 55 passed in 124s).

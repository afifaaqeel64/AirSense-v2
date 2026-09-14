# BRIEFING — 2026-08-25T05:39:15+05:00

## Mission
Investigate AirSense-v2 backend services, ingest routes, sensor connectivity, and diagnostic implementation to inform hardware connection validation & failover architecture.

## 🔒 My Identity
- Archetype: explorer
- Roles: Backend & Sensor Diagnostic Focus
- Working directory: c:\Users\HP\AirSense-v2\.agents\teamwork_preview_explorer_survey_1
- Original parent: 667cc9f0-2c04-4470-98c7-2d4b9f934cdf
- Milestone: survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Inspect existing codebase, backend services, ingest routes, sensor diagnostic state machine, dependencies, test setups
- Document findings in analysis.md and handoff.md

## Current Parent
- Conversation ID: 667cc9f0-2c04-4470-98c7-2d4b9f934cdf
- Updated: 2026-08-25T05:39:15+05:00

## Investigation State
- **Explored paths**:
  - `apps/api/main.py`, `apps/api/core/config.py`, `apps/api/db/models.py`, `apps/api/routers/ingest_router.py`, `apps/api/routers/provider_router.py`, `apps/api/routers/forecast_router.py`, `apps/api/routers/admin_router.py`
  - `services/quality_control/sensor_health_engine.py`, `services/quality_control/qc_engine.py`, `services/external_providers/multi_provider_router.py`, `services/forecasting/forecast_service.py`
  - `apps/web/hardware_dashboard.html`, `apps/web/opensource_dashboard.html`, `apps/web/index.html`
  - `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`, `scripts/airsense_serial_forwarder.py`
  - `tests/unit/test_sensor_health.py`, `tests/unit/test_multi_weather_providers.py`, `tests/integration/test_ingestion_api.py`
- **Key findings**:
  - Deterministic hardware connectivity validation implemented in `SensorHealthEngine` with 120s heartbeat window, UART PMS7003 frame validation, I2C BME280 response, ADC moisture plate, and SPI MicroSD checks.
  - State machine transitions between `LIVE_ACTIVE`, `PARTIAL_DEGRADED`, and `OFFLINE` with actionable pin troubleshooting guidance.
  - Hardware diagnostic endpoint available at `GET /api/v1/ingest/sensors/diagnostic`.
  - Dedicated routes `/hardware` and `/opensource` served with interactive browser validation test suite, pulsating liveness indicators, and automatic 24/7 open-source failover alerts.
  - Multi-provider weather fallback cascades through 8 atmospheric providers with parallel latency benchmarking, consensus calculations, and 24-hour predictive AI PM2.5 trajectory forecasts.
- **Unexplored areas**: None for backend and sensor diagnostic survey.

## Key Decisions Made
- Completed systematic survey of all backend services, database models, diagnostic engines, and test suites.
- Documented findings in `analysis.md` and 5-component `handoff.md`.

## Artifact Index
- analysis.md — Detailed analysis of backend & sensor diagnostics
- handoff.md — 5-component handoff report
- progress.md — Heartbeat and activity log

# BRIEFING — 2026-09-01T16:14:00Z

## Mission
Comprehensive codebase exploration of AirSense-v2: frontend, backend/firmware, telemetry schemas, API endpoints, tests, build scripts, and local fallback architecture.

## 🔒 My Identity
- Archetype: explorer
- Roles: codebase-explorer, synthesizer
- Working directory: c:\Users\HP\AirSense-v2\.agents\explorer_survey_1
- Original parent: 5cb1eac6-68de-47cb-bf01-3b1ce85430c8
- Milestone: codebase-survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement changes in codebase
- Survey frontend structure, backend/firmware telemetry schemas, API endpoints, tests, build scripts
- Output analysis.md and handoff.md in working directory

## Current Parent
- Conversation ID: 5cb1eac6-68de-47cb-bf01-3b1ce85430c8
- Updated: 2026-09-01T16:14:00Z

## Investigation State
- **Explored paths**:
  - `apps/web/hardware_dashboard.html`, `apps/web/opensource_dashboard.html`, `apps/web/index.html`, `apps/web_enterprise/index.html`, `AirSenseDashboard-try.jsx`
  - `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`, `scripts/airsense_mqtt_live_forwarder.py`, `scripts/airsense_serial_live_bridge.py`
  - `apps/api/main.py`, `apps/api/routers/ingest_router.py`, `apps/api/routers/hardware_router.py`, `services/quality_control/sensor_health_engine.py`
  - `tests/e2e/test_dual_dashboards_e2e.py`, `tests/unit/test_challenger_hardware_diagnostics.py`, `tests/unit/test_hardware_and_theme_endpoints.py`
- **Key findings**:
  - ESP32 firmware broadcasts JSON over MQTT TCP 1883 to `broker.hivemq.com` on `airsense/karachi/bic_roof/telemetry`.
  - Frontend `hardware_dashboard.html` contains complete UI components (PMS7003, BME280, Rain, MicroSD, table, reactive 8s heartbeat) and Paho MQTT WebSocket client (`wss://broker.hivemq.com:8884/mqtt`).
  - Dual-mode operation: WebSocket MQTT primary (cloud) + `/api/v1/ingest/sensors/diagnostic` secondary (local).
- **Unexplored areas**: None (all survey objectives completed).

## Key Decisions Made
- Generated comprehensive `analysis.md` and 5-component `handoff.md`.

## Artifact Index
- c:\Users\HP\AirSense-v2\.agents\explorer_survey_1\DISPATCH.md — Dispatch log
- c:\Users\HP\AirSense-v2\.agents\explorer_survey_1\BRIEFING.md — Situational awareness
- c:\Users\HP\AirSense-v2\.agents\explorer_survey_1\progress.md — Liveness & task tracking
- c:\Users\HP\AirSense-v2\.agents\explorer_survey_1\analysis.md — Detailed survey analysis
- c:\Users\HP\AirSense-v2\.agents\explorer_survey_1\handoff.md — 5-component handoff report

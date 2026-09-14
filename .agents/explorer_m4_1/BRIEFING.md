# BRIEFING — 2026-09-05T18:04:15Z

## Mission
Investigate `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` to determine required upgrades: tzapu/WiFiManager captive portal setup and WiFiClientSecure direct cloud ingestion, producing analysis.md and handoff.md.

## 🔒 My Identity
- Archetype: teamwork_preview_explorer
- Roles: explorer, analyst, synthesist
- Working directory: c:\Users\HP\AirSense-v2\.agents\explorer_m4_1\
- Original parent: e7827958-0d44-43ec-a8b8-a5a685eb01ec
- Milestone: M4 - ESP32 Physical Telemetry, WiFiManager, Direct Secure Cloud Ingestion

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Analyze existing .ino code thoroughly (Wi-Fi, MQTT, HTTP, sensor loops)
- Detail exact changes for tzapu/WiFiManager (header, autoConnect, captive portal AP, timeout)
- Detail exact changes for WiFiClientSecure cloud API ingestion (insecure TLS, HTTPClient, endpoint, headers, payload)
- Document all findings in analysis.md and write handoff.md

## Current Parent
- Conversation ID: e7827958-0d44-43ec-a8b8-a5a685eb01ec
- Updated: 2026-09-05T18:04:15Z

## Investigation State
- **Explored paths**:
  - `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`
  - `apps/api/routers/ingest_router.py`
  - `apps/api/core/security.py`
  - `scripts/airsense_serial_live_bridge.py`
  - `tests/integration/test_ingestion_api.py`
  - `tests/test_bridge_resilience.py`
  - `docs/Arduino_IDE_Setup_and_Firmware_Guide.md`
- **Key findings**:
  - Wi-Fi has hardcoded `WIFI_SSID` / `WIFI_PASS` (`Tracks_brand` / `AQeel1234`) and static `WiFi.begin` in `setup()` and `handleWiFiReconnection()`.
  - MQTT connects to `broker.hivemq.com` / `broker.emqx.io` (port 1883) via `WiFiClient` with custom non-blocking MQTT 3.1.1 byte packets.
  - HTTP push uses `HTTPClient` targeting local IP `http://172.20.10.13:8000/api/v1/ingest/reading` with an aggressive 400ms timeout.
  - Sensors: PMS7003 on UART2 (GPIO 16/17), BME280 on I2C (GPIO 21/22), Rainplate on ADC1 (GPIO 34), MicroSD on VSPI (GPIO 5/18/19/23).
  - Integration of `tzapu/WiFiManager` via `wm.setConfigPortalTimeout(180)` and `wm.autoConnect("AirSense-Setup")` enables dynamic onboarding and prevents field bricking.
  - Integration of `WiFiClientSecure` with `client.setInsecure()` and 4000ms timeout enables direct ingestion to `https://airsense-team.vercel.app/api/v1/ingest/reading` with `X-Device-Token: airsense_dev_token_khi_01`.
  - Live Vercel cloud ingestion endpoint verified via programmatic test returning HTTP 200 with `accepted: true`.
- **Unexplored areas**: None for this investigation phase.

## Key Decisions Made
- Confirmed `snprintf` wire payload format exactly matches FastAPI `ESP32IngestPayload` schema with `null` for sensor disconnects.
- Detailed parameterless `WiFi.begin()` for background reconnection using credentials in NVS.

## Artifact Index
- `DISPATCH.md` — Inbound instructions from orchestrator
- `BRIEFING.md` — Persistent agent memory and state
- `progress.md` — Liveness and execution heartbeat
- `analysis.md` — Comprehensive architectural specification and diff blueprint
- `handoff.md` — 5-component self-contained handoff report

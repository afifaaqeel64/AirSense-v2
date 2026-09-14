# BRIEFING — 2026-09-05T18:07:00Z

## Mission
Upgrade the ESP32 C++ firmware (`airsense_esp32_firmware.ino`) to be a 100% autonomous IoT appliance using `tzapu/WiFiManager` with AP name "AirSense-Setup" and direct secure Vercel cloud ingestion (`WiFiClientSecure` with `client.setInsecure()`), create user guide `README_FIRMWARE.md`, and author a comprehensive pytest verification suite (`test_firmware_autonomous_upgrade.py`).

## 🔒 My Identity
- Archetype: teamwork_preview_worker
- Roles: implementer, qa, specialist
- Working directory: c:\Users\HP\AirSense-v2\.agents\worker_m4_1\
- Original parent: e7827958-0d44-43ec-a8b8-a5a685eb01ec
- Milestone: Milestone 5 — ESP32 Autonomous Firmware Upgrade

## 🔒 Key Constraints
- Exclusive write ownership:
  - `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`
  - `scripts/airsense_esp32_firmware/README_FIRMWARE.md`
  - `tests/test_firmware_autonomous_upgrade.py`
  - `.agents/worker_m4_1/*`
- Standardize WiFiManager AP name strictly to `"AirSense-Setup"`.
- Set `wm.setConfigPortalTimeout(180);` before `wm.autoConnect("AirSense-Setup");`.
- Direct secure Vercel ingestion to `https://airsense-team.vercel.app/api/v1/ingest/reading` using `WiFiClientSecure` and `client.setInsecure()`.
- Zero hardcoded Wi-Fi credentials (`WIFI_SSID`, `WIFI_PASS`).
- Fix console log typos (`[HTTPS VERECEL PUSH]` -> `[HTTPS VERCEL PUSH]`).
- Retain HiveMQ Cloud MQTT publishing and hardware sensor drivers (PMS7003, BME280, Rainplate, MicroSD).
- Genuine implementations only — DO NOT CHEAT, do not hardcode test results.
- 100% pass on pytest `tests/test_firmware_autonomous_upgrade.py`.

## Current Parent
- Conversation ID: e7827958-0d44-43ec-a8b8-a5a685eb01ec
- Updated: 2026-09-05T18:07:00Z

## Task Summary
- **What to build**: Autonomous ESP32 firmware updates, comprehensive `README_FIRMWARE.md` guide, and automated 6-gate pytest test suite in `tests/test_firmware_autonomous_upgrade.py`.
- **Success criteria**: 
  1. Firmware updated with exact AP name `"AirSense-Setup"`, `setConfigPortalTimeout(180)`, `WiFiClientSecure` with `setInsecure()`, typo fixed, zero credentials.
  2. `README_FIRMWARE.md` authored covering Arduino IDE setup, tzapu/WiFiManager installation, board configuration, captive portal provisioning flow, and verification.
  3. `tests/test_firmware_autonomous_upgrade.py` covering Gates 1-6 passes 100%.
  4. Handoff report in `.agents/worker_m4_1/handoff.md`.
- **Interface contracts**: `apps/api/routers/ingest_router.py` (`ESP32IngestPayload`) and `ORIGINAL_REQUEST.md`.
- **Code layout**: Arduino sketch in `scripts/airsense_esp32_firmware/`, guide in same folder, tests in `tests/`.

## Key Decisions Made
- Use `"AirSense-Setup"` as the exact AP name in `autoConnect`.
- Replace `ESP.restart()` on portal timeout with non-blocking fallback to autonomous offline sensor mode, allowing continuous MicroSD and serial logging without boot loops.
- Add non-blocking `handleWiFiReconnection()` in loop using parameterless `WiFi.begin()` for NVS reconnect.
- Retain deterministic `snprintf` JSON serialization matching `ESP32IngestPayload` schema with both primary and alias keys.

## Change Tracker
- **Files modified**: None yet
- **Build status**: Pending
- **Pending issues**: None

## Quality Status
- **Build/test result**: Not yet executed
- **Lint status**: Clean
- **Tests added/modified**: `tests/test_firmware_autonomous_upgrade.py` (planned)

## Loaded Skills
- None specified in dispatch prompt.

## Artifact Index
- `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` — ESP32 Autonomous C++ firmware
- `scripts/airsense_esp32_firmware/README_FIRMWARE.md` — Onboarding and provisioning guide
- `tests/test_firmware_autonomous_upgrade.py` — Automated verification test suite
- `.agents/worker_m4_1/handoff.md` — Handoff report

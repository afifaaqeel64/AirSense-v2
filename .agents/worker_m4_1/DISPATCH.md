# Dispatch: worker_m4_1

Target Files Owned:
- `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`
- `scripts/airsense_esp32_firmware/README_FIRMWARE.md`
- `tests/test_firmware_autonomous_upgrade.py`

Key Tasks:
1. Update `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`:
   - Standardize Setup AP name to `"AirSense-Setup"`.
   - Ensure `tzapu/WiFiManager` is included and `wm.setConfigPortalTimeout(180)` is set before `wm.autoConnect("AirSense-Setup")`.
   - Ensure `WiFiClientSecure` with `client.setInsecure()` is used for `API_ENDPOINT = "https://airsense-team.vercel.app/api/v1/ingest/reading"`.
   - Confirm hardcoded Wi-Fi credentials (`WIFI_SSID`, `WIFI_PASS`) are completely absent.
   - Clean up any minor log typos (e.g. `[HTTPS VERECEL PUSH]` -> `[HTTPS VERCEL PUSH]`).
2. Create `scripts/airsense_esp32_firmware/README_FIRMWARE.md`:
   - Arduino IDE setup instructions for ESP32.
   - Installing `WiFiManager` by tzapu via Arduino Library Manager (or `arduino-cli lib install "WiFiManager"`).
   - Installing `ArduinoJson` (v6 or v7) and other required sensor libraries.
   - Board configuration (ESP32 Dev Module, 115200 baud).
   - Step-by-step first-boot captive portal flow: connect to `AirSense-Setup`, open `192.168.4.1`, choose local Wi-Fi, enter password, save.
   - Verifying autonomous operation with wall adapter (LED blinks, HTTPS push to Vercel, MQTT to HiveMQ Cloud).
3. Create automated pytest test suite `tests/test_firmware_autonomous_upgrade.py`:
   - Run tests validating firmware syntax, JSON payload schema against `ESP32IngestPayload`, absence of hardcoded Wi-Fi credentials, AP configuration, and live cloud ingestion compatibility.
   - If `arduino-cli` is available, test compilation (`arduino-cli lib install "WiFiManager"` and `arduino-cli compile`).
4. Run tests and document verification commands and results in `c:\Users\HP\AirSense-v2\.agents\worker_m4_1\handoff.md`.

## 2026-09-05T18:06:26Z
You are worker_m4_1 (teamwork_preview_worker).
Your working directory is: c:\Users\HP\AirSense-v2\.agents\worker_m4_1\
Objectives & Instructions:
1. Update `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`
2. Author `scripts/airsense_esp32_firmware/README_FIRMWARE.md`
3. Author and run automated verification tests in `tests/test_firmware_autonomous_upgrade.py`
4. Run pytest (`python -m pytest tests/test_firmware_autonomous_upgrade.py -v`) and verify 100% pass.
5. Document all changes, test commands, and exact outputs in `c:\Users\HP\AirSense-v2\.agents\worker_m4_1\handoff.md`.

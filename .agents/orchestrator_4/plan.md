# Execution Plan — ESP32 Autonomous Firmware Upgrade

## Objective
Update the ESP32 C++ firmware (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`) to be a fully autonomous IoT device connecting directly to the Vercel cloud and MQTT broker without relying on the laptop serial bridge script.

## Milestones & Work Breakdown
1. **Phase 0: Survey & Architecture Discovery**
   - Dispatch Explorer(s) to inspect:
     - `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`
     - Current HTTP vs MQTT logic, Wi-Fi handling, baud rate, sensor read routines, JSON payload format
     - `https://airsense-team.vercel.app/api/v1/ingest/reading` schema expectations
     - Existing tests / validation scripts (e.g., Python linters or syntax validators, arduino-cli availability, mock tests)
     - `tzapu/WiFiManager` library requirements for ESP32 and `WiFiClientSecure` HTTPS best practices
2. **Phase 1: Implementation - Dynamic Wi-Fi & Direct HTTPS Ingestion**
   - Implement `WiFiManager` (autoConnect with AP "AirSense-Setup")
   - Remove hardcoded credentials (`WIFI_SSID`, `WIFI_PASS`)
   - Replace HTTP with `WiFiClientSecure` using `client.setInsecure()`
   - Target production URL `https://airsense-team.vercel.app/api/v1/ingest/reading`
   - Retain HiveMQ Cloud MQTT publishing and hardware sensor reading logic
   - Non-blocking error handling and reconnect loops
3. **Phase 2: Verification, Challenger Tests & Forensic Audit**
   - Reviewer: Code review, security & architecture check
   - Challenger: Empirical validation (JSON payload correctness against FastAPI Pydantic schema, mock server response verification, C++ syntax check)
   - Forensic Auditor: Check for no mock cheats, real implementation, zero integrity violations
4. **Phase 3: Documentation & Handoff**
   - Create `scripts/airsense_esp32_firmware/README_FIRMWARE.md` with step-by-step flashing instructions, library installation in Arduino IDE, and phone setup AP flow.
   - Deliver Handoff Report to Sentinel for Victory Audit.

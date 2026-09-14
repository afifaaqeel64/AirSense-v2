# Handoff Report: Milestone 5 Verification Strategy & Test Architecture

**Agent:** explorer_m4_2 (Teamwork Preview Explorer)  
**Date:** 2026-09-05T23:05:45+05:00  
**Target File Created:** `c:\Users\HP\AirSense-v2\.agents\explorer_m4_2\verification_strategy.md`  

---

## 1. Observation

1. **Serial Bridge & Telemetry Simulation Tools:**
   - In `scripts/airsense_serial_live_bridge.py`:
     - Lines 415–470 implement `run_simulation_mode()`, which builds a canonical telemetry packet using `build_telemetry_payload()`, dual-publishes to HiveMQ (`broker.hivemq.com:1883`) and EMQX (`broker.emqx.io:1883`), and dispatches asynchronously via `push_telemetry_dual_async()` to local and cloud targets using `ThreadPoolExecutor`.
     - Lines 588–615 implement CLI parser with `--simulate` flag, enabling simulation via `python scripts/airsense_serial_live_bridge.py --simulate --cloud-url <URL>`.
   - In `scripts/verify_live_endpoints.py`:
     - Lines 21–150 implement 5 endpoint probes: `/api/v1/health/liveness`, `/api/v1/health/readiness`, `/api/v1/providers/weather/telemetry-feed`, `/api/v1/ingest/reading`, and `/api/v1/ingest/sensors/diagnostic`.
     - Lines 98–137 submit a sample JSON reading with header `X-Device-Token: airsense_dev_token_khi_01` and assert `res.status_code in (200, 201) and accepted is True`.

2. **Existing Test Suites & Test Execution:**
   - `python -m pytest tests/test_payload_schema_and_safety.py` passed all 56 tests in 0.92s.
   - `python -m pytest tests/e2e/test_live_public_endpoints.py` passed all 8 tests in 15.50s.
   - `apps/api/routers/ingest_router.py` (lines 50–72) defines the canonical Pydantic model `ESP32IngestPayload` for `/api/v1/ingest/reading`.

3. **Compiler & Toolchain Availability:**
   - Windows command search showed `arduino-cli.exe` is installed at:
     `C:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe` (Version 1.5.1).
   - `arduino-cli core list` showed `esp32:esp32` version 3.3.11 installed at `C:\Users\HP\AppData\Local\Arduino15\packages\esp32\hardware\esp32\3.3.11`.
   - `arduino-cli lib list` showed core libraries installed, but `WiFiManager` was missing from user libraries.
   - Executing `arduino-cli compile --fqbn esp32:esp32:esp32 scripts/airsense_esp32_firmware` produced verbatim output:
     `fatal error: WiFiManager.h: No such file or directory`
   - Searching available libraries with `arduino-cli lib search WiFiManager` returned version 2.0.17 by tzapu.

4. **Updated Firmware Code State:**
   - In `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`:
     - Lines 19–21: `#include <WiFi.h>`, `#include <WiFiManager.h>`, `#include <WiFiClientSecure.h>`.
     - Lines 27–28: Previous `WIFI_SSID` and `WIFI_PASS` variable definitions have been deleted.
     - Line 39: `const char* API_ENDPOINT = "https://airsense-team.vercel.app/api/v1/ingest/reading";`.
     - Line 448: `bool res = wm.autoConnect("AirSense-Setup-AP");`.
     - Lines 596–603: `WiFiClientSecure secureClient; secureClient.setInsecure(); HTTPClient http; http.begin(secureClient, API_ENDPOINT); http.setTimeout(2500); http.addHeader("Content-Type", "application/json"); http.addHeader("X-Device-Token", DEVICE_TOKEN);`.
     - Lines 607, 609: Serial log message has a minor typo: `[HTTPS VERECEL PUSH]`.
     - Line 617: Background Wi-Fi loop replaced with comment: `// WiFiManager handles background reconnects, no manual Wi-Fi loop required!`.

5. **Firmware Documentation Status:**
   - File `scripts/airsense_esp32_firmware/README_FIRMWARE.md` does NOT exist yet.
   - Legacy document `docs/Arduino_IDE_Setup_and_Firmware_Guide.md` (lines 138–144) still instructs developers to enter hardcoded Wi-Fi credentials into the C++ code.

---

## 2. Logic Chain

1. **Hardware-Free Verification Requirement:**
   Because physical ESP32 boards and real Wi-Fi credentials cannot be physically attached or rebooted during automated testing, verification must rely on programmatic analysis and local tooling (Observation 1, 2, 3).
2. **Dual-Path Firmware Validation Strategy:**
   - **Path A (Deterministic Static & Schema Testing in Python):** Using Python's `re` module, `json` module, and `pydantic`, we can extract the JSON payload template from `airsense_esp32_firmware.ino`, test JSON validity, check schema conformance against `ESP32IngestPayload`, and scan for prohibited hardcoded variables (`WIFI_SSID`, `WIFI_PASS`). This runs via `pytest` in <2s with zero external dependencies (Observation 2).
   - **Path B (Physical C++ Compilation):** With `arduino-cli.exe` and `esp32:esp32 3.3.11` already installed, the Challenger/Reviewer can execute `arduino-cli lib install "WiFiManager"` and compile the sketch with `--fqbn esp32:esp32:esp32` to prove zero C++ compilation errors (Observation 3).
3. **Identification of Discrepancies:**
   - `ORIGINAL_REQUEST.md` and user instructions specifically request the AP name `AirSense-Setup`. Line 448 of `airsense_esp32_firmware.ino` uses `"AirSense-Setup-AP"` (Observation 4). This should be standardized to `"AirSense-Setup"` (or regex should allow both).
   - `README_FIRMWARE.md` must be created so that human users know how to install `tzapu/WiFiManager` in Arduino IDE and connect to the captive portal at `192.168.4.1` (Observation 5).

---

## 3. Caveats

1. **Physical AP Radio Emittance:**
   Software tests cannot verify that the ESP32 hardware RF synthesizer physically broadcasts 2.4GHz beacon frames. However, verifying `wm.autoConnect("AirSense-Setup")` and successful compilation guarantees that the Espressif Wi-Fi stack initiates AP mode.
2. **Vercel TLS Certificate Revocation:**
   The firmware utilizes `client.setInsecure()` to bypass CA chain verification on the ESP32. This is the standard pattern for resource-constrained microcontrollers, but means server certificate expiration will not be detected on the edge node.
3. **Compilation Prerequisite:**
   `arduino-cli compile` requires `WiFiManager` to be installed into `C:\Users\HP\AppData\Local\Arduino15\libraries` first. If run without installing the library, compilation will exit with exit code 1 (`WiFiManager.h: No such file or directory`).

---

## 4. Conclusion

1. The project has a comprehensive test infrastructure for endpoint validation (`verify_live_endpoints.py`) and payload schema sanitization (`test_payload_schema_and_safety.py`).
2. The firmware has successfully eliminated hardcoded credentials and integrated `WiFiManager`, `WiFiClientSecure`, and the Vercel HTTPS endpoint.
3. The AP SSID parameter in `wm.autoConnect()` should be adjusted from `"AirSense-Setup-AP"` to `"AirSense-Setup"` for 100% compliance with `ORIGINAL_REQUEST.md`.
4. A turnkey 6-gate verification plan and ready-to-run pytest harness (`tests/test_firmware_autonomous_upgrade.py`) have been documented in `verification_strategy.md`.
5. Implementer must author `scripts/airsense_esp32_firmware/README_FIRMWARE.md` before final review.

---

## 5. Verification Method

To independently verify these findings:

1. **Inspect Strategy Document:**
   ```powershell
   type c:\Users\HP\AirSense-v2\.agents\explorer_m4_2\verification_strategy.md
   ```
2. **Verify Python Test Capabilities:**
   ```powershell
   python -m pytest tests/test_payload_schema_and_safety.py
   ```
3. **Verify `arduino-cli` and ESP32 Core Detection:**
   ```powershell
   & "C:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" core list
   ```
4. **Verify Firmware AP Discrepancy & HTTPS Logic:**
   Inspect lines 38–41, 448, and 595–612 of `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`.

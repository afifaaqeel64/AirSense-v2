## 2026-09-02T09:57:17Z
You are Worker 2 (ESP32 Firmware Specialist).
Your working directory is: c:/Users/HP/AirSense-v2/.agents/worker_2
Read ORIGINAL_REQUEST.md at c:/Users/HP/AirSense-v2/.agents/ORIGINAL_REQUEST.md.
Read PROJECT.md at c:/Users/HP/AirSense-v2/PROJECT.md.
Read Explorer 1 analysis at c:/Users/HP/AirSense-v2/.agents/explorer_1/analysis.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Write Ownership (Exclusive to Worker 2):
- `c:/Users/HP/AirSense-v2/scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`

Tasks:
1. In `airsense_esp32_firmware.ino`:
   - Emit structured JSON telemetry over Serial: Add `Serial.print("[JSON_TELEMETRY] "); Serial.println(jsonPayload);` so the Python bridge can ingest clean JSON directly without fragile regexes.
   - Fix sensor failure masking: When PMS7003 or BME280 fails to read, do NOT inject fake static numbers (`7.0, 9.0, 10.0, 29.5, 65.0, 1012.0`). Instead, set `sensor_health` fields (e.g. `pms7003: "ERROR"`, `bme280: "ERROR"`) and send `null` or -1 values, with clear health status flags.
   - Make network operations non-blocking: Eliminate blocking delays (e.g. 5000ms connect + 3000ms wait) in `publishMQTT()`. Use non-blocking Wi-Fi reconnection state machine in `loop()` so sensor acquisition is never frozen when Wi-Fi drops.
   - Ensure clean C++ syntax and Arduino/ESP32 core 2.0+ compatibility.
2. Verify C++ syntax and code integrity.
3. Write your handoff report to `c:/Users/HP/AirSense-v2/.agents/worker_2/handoff.md` and notify parent.

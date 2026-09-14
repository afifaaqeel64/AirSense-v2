## 2026-08-25T01:01:26Z
You are Challenger 1 (Hardware Diagnostics & State Machine Challenger).
Your working directory is: c:\Users\HP\AirSense-v2\.agents\teamwork_preview_challenger_1

Please read:
- c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md
- c:\Users\HP\AirSense-v2\PROJECT.md
- c:\Users\HP\AirSense-v2\TEST_READY.md

Your mission:
1. Empirically stress-test the sensor health engine and diagnostic endpoints with edge cases, extreme inputs, and state machine transitions:
   - Test packet arrival at exactly 119s (LIVE), 120s (LIVE), 121s (OFFLINE), and 1000s (OFFLINE).
   - Test degraded sensor states: PMS7003 PM2.5 = 0.0 ug/m3 (DEGRADED with UART pin guidance), BME280 temperature = 70.0°C (DEGRADED with I2C pin guidance).
   - Test missing sensor values, partial telemetry packets, and corrupted fields.
   - Test rapid sequential diagnostic polls and concurrent ingestion calls.
2. Execute empirical test scripts via `run_command` in powershell.
3. Write your empirical challenge findings and verdict (`APPROVE` or `REQUEST_CHANGES`) in `c:\Users\HP\AirSense-v2\.agents\teamwork_preview_challenger_1\handoff.md` and send a message.

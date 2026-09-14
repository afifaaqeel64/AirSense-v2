## 2026-09-02T10:48:53Z
You are Challenger 2 (Replacement: Bridge Daemon & Hot-Plug / Port-Lock Challenger).
Your working directory is: c:/Users/HP/AirSense-v2/.agents/challenger_2_gen2
Read ORIGINAL_REQUEST.md at c:/Users/HP/AirSense-v2/.agents/ORIGINAL_REQUEST.md.
Read PROJECT.md at c:/Users/HP/AirSense-v2/PROJECT.md.
Read TEST_READY.md at c:/Users/HP/AirSense-v2/TEST_READY.md.

Task:
Empirically stress-test and challenge the Python serial bridge (`scripts/airsense_serial_live_bridge.py`) and serial communications in AirSense-v2:
1. Write and execute tests verifying:
   - Dynamic serial port hot-plugging simulation (USB port disconnects and reappears on a new COM port).
   - Port locked / permission error simulation (e.g. `PermissionError` when port is busy).
   - Corrupted or malformed incoming serial lines (garbage bytes, partial JSON, truncated ASCII).
   - Falsy zero values (e.g. `pm2_5: 0.0`, `temperature: 0.0`, `rain_flag: false`) to ensure they are not dropped or converted to null/NaN.
2. Run pytest suite (`py -m pytest tests/test_bridge_resilience.py tests/test_payload_schema_and_safety.py -v`).
3. Output your explicit verdict: `APPROVE` or `REQUEST_CHANGES`.

Write a detailed handoff report to: `c:/Users/HP/AirSense-v2/.agents/challenger_2_gen2/handoff.md` and send a message to parent with your verdict.

## 2026-09-02T09:57:17Z
You are Worker 1 (Python Bridge & Dependencies Specialist).
Your working directory is: c:/Users/HP/AirSense-v2/.agents/worker_1
Read ORIGINAL_REQUEST.md at c:/Users/HP/AirSense-v2/.agents/ORIGINAL_REQUEST.md.
Read PROJECT.md at c:/Users/HP/AirSense-v2/PROJECT.md.
Read Explorer 2 analysis at c:/Users/HP/AirSense-v2/.agents/explorer_2/analysis.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Write Ownership (Exclusive to Worker 1):
- `c:/Users/HP/AirSense-v2/requirements.txt`
- `c:/Users/HP/AirSense-v2/scripts/airsense_serial_live_bridge.py`
- `c:/Users/HP/AirSense-v2/scripts/airsense_mqtt_live_forwarder.py`
- `c:/Users/HP/AirSense-v2/scripts/airsense_serial_forwarder.py`
- `c:/Users/HP/AirSense-v2/run_bridge_daemon.bat`

Tasks:
1. Update `requirements.txt` to include `pyserial>=3.5` and `paho-mqtt>=2.0.0`.
2. Rewrite/Harden `scripts/airsense_serial_live_bridge.py`:
   - Support Paho-MQTT v2 callback API (`CallbackAPIVersion.VERSION2`).
   - Implement dual-publishing to BOTH `broker.hivemq.com` (1883) and `broker.emqx.io` (1883) so that any frontend or subscriber receives the telemetry.
   - Implement dynamic COM port detection inside the reconnect loop: scan active serial ports continuously on disconnects or permission errors using `serial.tools.list_ports`.
   - Implement an infinite auto-recovery loop with exponential backoff and jitter — NEVER terminate or exit on serial disconnect, port locked/in-use, or network drops.
   - Robustly parse both structured JSON lines (`[JSON_TELEMETRY] {...}`) and fallback raw regex patterns if legacy debug text is received.
3. Harden `scripts/airsense_mqtt_live_forwarder.py` and `scripts/airsense_serial_forwarder.py` with infinite reconnect loops and non-crashing exception handlers.
4. Update `run_bridge_daemon.bat` to support auto-detection of COM ports if no port argument is passed.
5. Verify changes by executing unit/integration tests or running python syntax/import validation.
6. Write your handoff report to `c:/Users/HP/AirSense-v2/.agents/worker_1/handoff.md` and notify parent.

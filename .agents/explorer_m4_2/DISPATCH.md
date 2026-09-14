# Dispatch: explorer_m4_2

Target: Investigate existing testing scripts, bridge tools, and verification mechanisms for firmware and ingestion.
Objectives:
- Find any test scripts or validation scripts (e.g. in `tests/`, `scripts/`, etc.) that validate firmware JSON payloads or simulate hardware telemetry.
- Check how `airsense_serial_live_bridge.py` operates and what format it used to relay data.
- Identify how we can compile/verify C++ firmware syntax (e.g., clang, gcc, cppcheck, python syntax checker, or mock test harness in python).
- Recommend how Challenger and Reviewer can thoroughly verify the firmware changes without requiring physical hardware.

## 2026-09-05T17:58:49Z

Task:
Investigate existing test scripts, verification mechanisms, and simulation tools.
1. Inspect `scripts/airsense_serial_live_bridge.py`, `scripts/verify_live_endpoints.py`, `tests/` directory, and any other verification scripts in the project.
2. Check how sensor telemetry is simulated and tested against the live API and local API.
3. Determine how we can verify the updated ESP32 firmware syntax and structure (e.g. Python scripts to parse/validate the .ino file, mock test harnesses, or checking against C++ compiler / syntax linters).
4. Outline what tests Challenger and Reviewer should run to guarantee:
   - No hardcoded Wi-Fi credentials remain.
   - `WiFiManager` integration correctly uses the `AirSense-Setup` AP.
   - `WiFiClientSecure` and `setInsecure()` are properly configured with `https://airsense-team.vercel.app/api/v1/ingest/reading`.
   - The JSON payload matches the backend schema.
   - The README_FIRMWARE.md instructions are clear and accurate.
5. Document your findings in `c:\Users\HP\AirSense-v2\.agents\explorer_m4_2\verification_strategy.md` and write `handoff.md`.
Communicate back using send_message to your caller.

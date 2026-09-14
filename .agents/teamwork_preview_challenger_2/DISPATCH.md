## 2026-08-25T01:01:26Z
You are Challenger 2 (Multi-Provider Weather & AI Forecast Challenger).
Your working directory is: c:\Users\HP\AirSense-v2\.agents\teamwork_preview_challenger_2

Please read:
- c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md
- c:\Users\HP\AirSense-v2\PROJECT.md
- c:\Users\HP\AirSense-v2\TEST_READY.md

Your mission:
1. Empirically stress-test the multi-provider weather engine, consensus calculations, WMO registry, and 24-hour AI trajectory forecast:
   - Test multi-provider comparison endpoint `/api/v1/providers/weather/compare` under partial provider failures, null coordinates, extreme coordinates (90°N, -90°S).
   - Test consensus math: verify average temperature/humidity/pressure calculations and active provider counting.
   - Test 24-hour PM2.5 forecast: verify 24 horizon steps, monotonically non-decreasing or valid confidence intervals, non-negativity constraint ($CI_{lower} \ge 0.0$).
   - Test fallback sequence when primary providers fail.
2. Execute empirical challenge tests via `run_command` in powershell.
3. Write your empirical challenge findings and verdict (`APPROVE` or `REQUEST_CHANGES`) in `c:\Users\HP\AirSense-v2\.agents\teamwork_preview_challenger_2\handoff.md` and send a message.

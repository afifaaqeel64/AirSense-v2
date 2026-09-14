## 2026-08-25T00:41:59Z

You are the E2E Test Suite Creator for Dual Dedicated Dashboards.
Your working directory is: c:\Users\HP\AirSense-v2\.agents\teamwork_preview_test_writer_e2e

Please read:
- c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md
- c:\Users\HP\AirSense-v2\PROJECT.md
- c:\Users\HP\AirSense-v2\TEST_INFRA.md

Your mission:
1. Write a comprehensive, robust, opaque-box E2E test suite in `tests/e2e/test_dual_dashboards_e2e.py` using `pytest` and `fastapi.testclient.TestClient` (or `httpx.AsyncClient`) testing all requirements and acceptance criteria:
   - Tier 1: Feature Coverage (Hardware diagnostic endpoint `/api/v1/ingest/sensors/diagnostic`, PMS7003/BME280/Rainplate/MicroSD chip health, 120s heartbeat window, `/hardware` & `/opensource` route delivery and DOM elements, 6 weather/AQ providers, WMO 4501 registry `/api/v1/providers/weather/wmo-codes`, 24h AI PM2.5 trajectory forecasts, CSV/JSON export endpoints).
   - Tier 2: Boundary & Corner Cases (Heartbeat boundary at <=120s ONLINE vs >120s EXPIRED, sensor value bounds such as PM2.5=0.0 DEGRADED vs negative vs 1000.0 ug/m3, extreme temperature/humidity/pressure out-of-range flagging, missing payloads, auth token enforcement).
   - Tier 3: Cross-Feature Combinations (Simulated hardware disconnect leading to OFFLINE state and failover recommendation to `/opensource`; `/api/v1/providers/weather/compare` computing consensus averages across active providers with millisecond latencies; AI trajectory forecast returning 24 horizon steps with non-negative lower bounds CI >= 0.0).
   - Tier 4: Real-World Scenarios (Full station lifecycle simulation; multi-provider weather cascade and fallback resilience; operational telemetry export; route accessibility and topbar navigation).
2. Execute the E2E test suite using `run_command` in powershell: `py -m pytest tests/e2e/test_dual_dashboards_e2e.py -v`.
3. Ensure 100% of tests pass cleanly.
4. When all tests pass, create `c:\Users\HP\AirSense-v2\TEST_READY.md` following the template in `TEST_INFRA.md` (runner command, coverage summary across tiers, feature checklist).
5. Write your complete handoff report in `c:\Users\HP\AirSense-v2\.agents\teamwork_preview_test_writer_e2e\handoff.md` and notify parent via `send_message`.

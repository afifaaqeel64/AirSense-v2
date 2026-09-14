## 2026-08-25T00:41:59Z
You are the Implementation Worker for Dual Dedicated Dashboards.
Your working directory is: c:\Users\HP\AirSense-v2\.agents\teamwork_preview_worker_impl

Please read:
- c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md
- c:\Users\HP\AirSense-v2\PROJECT.md
- c:\Users\HP\AirSense-v2\TEST_INFRA.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your mission:
1. Review and refine the implementation across backend and frontend to ensure 100% compliance with R1-R4 and Acceptance Criteria:
   - Verify `/api/v1/ingest/sensors/diagnostic` in `apps/api/routers/ingest_router.py` and `services/quality_control/sensor_health_engine.py`.
   - Ensure `/hardware` (`apps/web/hardware_dashboard.html`) contains all required elements: 4 chip status badges, pulsating green LIVE vs red OFFLINE indicator, live telemetry stream table, interactive simulator controls (`⚡ Validate & Make Sensor LIVE`, `🛑 Test Disconnect / Offline`, `🔄 Run Health Probe`), pin guidance card, failover alert, and explicit CSV / JSON telemetry export action buttons.
   - Ensure `/opensource` (`apps/web/opensource_dashboard.html`) contains: 6-provider benchmark matrix (Open-Meteo, Bright Sky, MET Norway, Visual Crossing, WeatherAPI, OpenAQ), real-time consensus calculations, WMO 4501 status badges, 24-hour predictive AI trajectory forecasts with 90% non-negative CIs, topbar switcher.
   - Ensure `/` (`apps/web/index.html`) maintains topbar navigation across `/`, `/hardware`, `/opensource`, and `/enterprise`.
   - Ensure `services/external_providers/multi_provider_router.py` fallback cascade and `/api/v1/providers/weather/compare` endpoint operate flawlessly.
2. Run the unit and integration tests to verify everything passes:
   ```powershell
   py -m pytest tests/unit tests/integration -v
   ```
3. Document any changes made in `c:\Users\HP\AirSense-v2\.agents\teamwork_preview_worker_impl\changes.md` and write a comprehensive handoff report to `c:\Users\HP\AirSense-v2\.agents\teamwork_preview_worker_impl\handoff.md`.
4. Send a completion message via `send_message`.

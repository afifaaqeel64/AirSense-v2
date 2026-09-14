# BRIEFING — 2026-08-25T05:38:20+05:00

## Mission
Investigate frontend/UI codebase (React/Next.js/Vite/Tailwind/Components/Routing) in c:\Users\HP\AirSense-v2 for dual dashboards (/hardware, /opensource, and /), hardware connection status indicators, sensor chip badges, simulator controls, telemetry streams, and CSV/JSON export.

## 🔒 My Identity
- Archetype: explorer
- Roles: frontend & UI routing investigator
- Working directory: c:\Users\HP\AirSense-v2\.agents\teamwork_preview_explorer_survey_2
- Original parent: 667cc9f0-2c04-4470-98c7-2d4b9f934cdf
- Milestone: survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Inspect existing frontend code, dependencies, structure, routes, styling, build/test setups

## Current Parent
- Conversation ID: 667cc9f0-2c04-4470-98c7-2d4b9f934cdf
- Updated: 2026-08-25T05:38:20+05:00

## Investigation State
- **Explored paths**:
  - `PROJECT.md`
  - `ORIGINAL_REQUEST.md`
  - `apps/api/main.py`
  - `apps/api/routers/ingest_router.py`
  - `apps/api/routers/export_router.py`
  - `apps/web/index.html`
  - `apps/web/hardware_dashboard.html`
  - `apps/web/opensource_dashboard.html`
  - `apps/web/hooks/useRealtimeWeather.js`
  - `apps/web_enterprise/index.html`
  - `AirSenseDashboard-try.jsx`
  - `services/quality_control/sensor_health_engine.py`
  - `tests/unit/test_sensor_health.py`
- **Key findings**:
  - Zero-build React 18 UMD + Babel architecture served directly via FastAPI `FileResponse` / `StaticFiles`.
  - Dedicated `/hardware` route (`apps/web/hardware_dashboard.html`) with deterministic diagnostic integration (`/api/v1/ingest/sensors/diagnostic`), pulsating green/red status indicators, 4 chip status badges (PMS7003, BME280, Rainplate, MicroSD), live telemetry stream, and interactive validation/disconnect simulators.
  - Dedicated `/opensource` route (`apps/web/opensource_dashboard.html`) with 7-provider parallel benchmarking, real-time consensus calculations, WMO 4501 icons, and 24-hour predictive PM2.5 trajectory table with 90% CIs.
  - Topbar switcher enables seamless switching across `/`, `/hardware`, `/opensource`, and `/enterprise`.
  - Export feature gap: `/hardware` should include direct CSV/JSON export action buttons in the telemetry stream card header.
- **Unexplored areas**: None. Frontend survey is 100% complete.

## Key Decisions Made
- Authored comprehensive survey in `analysis.md` and complete 5-component report in `handoff.md`.

## Artifact Index
- `analysis.md` — Detailed frontend findings and architectural proposal
- `handoff.md` — 5-component handoff report
- `progress.md` — Liveness heartbeat
- `DISPATCH.md` — Incoming dispatch log

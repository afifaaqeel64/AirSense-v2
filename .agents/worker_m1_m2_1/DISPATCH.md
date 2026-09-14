# DISPATCH: worker_m1_m2_1

**Identity**: You are worker_m1_m2_1 (teamwork_preview_worker).
**Working Directory**: c:\Users\HP\AirSense-v2\.agents\worker_m1_m2_1
**Authoritative User Request**: c:\Users\HP\AirSense-v2\ORIGINAL_REQUEST.md
**Parent**: orchestrator_3 (Conversation ID: 8b794ee2-ed6c-40e1-99dd-6ab770b678dd)

## Context & Inputs
You must read the following input files before making any modifications:
1. `c:\Users\HP\AirSense-v2\ORIGINAL_REQUEST.md` (Authoritative user request)
2. `c:\Users\HP\AirSense-v2\.agents\explorer_survey_backend_1\handoff.md` (Backend & scheduler survey)
3. `c:\Users\HP\AirSense-v2\.agents\explorer_survey_bridge_tests_1\handoff.md` (Bridge & test survey)
4. `c:\Users\HP\AirSense-v2\.agents\orchestrator_3\PROJECT.md` (Current project architecture & milestones)

## Exclusive File Ownership
You exclusively own and may edit:
- `apps/api/db/session.py`
- `scripts/airsense_serial_live_bridge.py`
- `c:\Users\HP\AirSense-v2\PROJECT.md`
- `tests/test_bridge_resilience.py` (and optionally `tests/integration/test_serial_bridge_dual_routing.py`)

Do NOT modify any other files.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks to Execute
1. **Milestone 1 - Sessionmaker Alias**:
   In `apps/api/db/session.py`, add `async_session_maker = AsyncSessionLocal` so that `services/background_scheduler.py` can import `async_session_maker` without raising an `ImportError`.
2. **Milestone 2 - Hardware Serial Bridge Cloud Multi-Destination Dual-Routing**:
   In `scripts/airsense_serial_live_bridge.py`:
   - Add support for environment variable `AIRSENSE_LOCAL_API_URL` (default `http://127.0.0.1:8000/api/v1/ingest/reading`).
   - Add support for environment variable `AIRSENSE_CLOUD_API_URL` and CLI flag `--cloud-url`.
   - Add non-blocking concurrent HTTP dispatch using `ThreadPoolExecutor(max_workers=4, thread_name_prefix="AirSense-HttpPush")`.
   - Ensure timeouts are strict (2.5s) and errors are caught gracefully so serial acquisition is never blocked or stalled by slow cloud networks.
   - Add a simulation mode (e.g. `--simulate` or `SIMULATE` CLI argument) to dispatch a genuine synthetic telemetry reading through the dual-dispatch pipeline for verification without physical hardware.
3. **Project File Synchronization**:
   Update `c:\Users\HP\AirSense-v2\PROJECT.md` to reflect the updated architecture, feature inventory, milestones, and contracts from `.agents/orchestrator_3/PROJECT.md`.
4. **Test Verification**:
   Run pytest to verify all existing and updated tests pass:
   - `py -m pytest tests/unit/test_production_readiness.py tests/integration/test_ingestion_api.py -v`
   - `py -m pytest tests/test_bridge_resilience.py -v`
5. **Report**:
   Write your completion report in `c:\Users\HP\AirSense-v2\.agents\worker_m1_m2_1\handoff.md`.

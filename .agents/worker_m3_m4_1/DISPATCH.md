# DISPATCH: worker_m3_m4_1

**Identity**: You are worker_m3_m4_1 (teamwork_preview_worker).
**Working Directory**: c:\Users\HP\AirSense-v2\.agents\worker_m3_m4_1
**Authoritative User Request**: c:\Users\HP\AirSense-v2\ORIGINAL_REQUEST.md
**Parent**: orchestrator_3 (Conversation ID: 8b794ee2-ed6c-40e1-99dd-6ab770b678dd)

## Context & Inputs
You must read the following input files before making any modifications:
1. `c:\Users\HP\AirSense-v2\ORIGINAL_REQUEST.md` (Authoritative user request)
2. `c:\Users\HP\AirSense-v2\.agents\explorer_survey_bridge_tests_1\handoff.md` (Section 4.2 has the complete live endpoint verification script blueprint)
3. `c:\Users\HP\AirSense-v2\.agents\skills\airsense-render-deploy\SKILL.md` (Render deployment skill)
4. `c:\Users\HP\AirSense-v2\.agents\worker_m1_m2_1\handoff.md` (Previous worker's handoff)

## Exclusive File Ownership
You exclusively own:
- `scripts/verify_live_endpoints.py`
- Background process execution (uvicorn backend on port 8000, cloudflared tunnel)
- Git repository initialization and GitHub remote synchronization
- `c:\Users\HP\AirSense-v2\PROJECT.md` (milestone updates)

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks to Execute
1. **GitHub Repository Sync**:
   - Check if `.git` exists. If not, run `git init`, set branch to `main`, add all files (`git add .`), and commit (`git commit -m "feat: AirSense-v2 live cloud deployment, scheduler, and dual-routing bridge"`).
   - Check `gh auth status` or git remotes. If GitHub CLI `gh` is authenticated, create or sync repository `AirSense-v2` (`gh repo create AirSense-v2 --public --source=. --push` or connect to existing remote).
2. **Live Backend Execution**:
   - Ensure the FastAPI backend (`apps.api.main:app`) is running locally on port 8000 so the background scheduler (60s weather, 10s watchdog) is executing.
3. **Live Public HTTPS Endpoint Provisioning**:
   - Using `cloudflared.exe` located at workspace root, run the tunnel:
     `.\cloudflared.exe tunnel --url http://127.0.0.1:8000`
     Extract the assigned public HTTPS URL (e.g., `https://*.trycloudflare.com`).
   - If Render deployment is also feasible via `scripts/deploy_to_render_api.py`, document or test it.
4. **Create Live Verification Harness**:
   - Create `scripts/verify_live_endpoints.py` per the blueprint in `explorer_survey_bridge_tests_1/handoff.md §4.2`.
   - The script must test all 5 production endpoints over the public HTTPS URL:
     1. `GET /api/v1/health/liveness` (HTTP 200, status: healthy)
     2. `GET /api/v1/health/readiness` (HTTP 200, status: ready, DB connected)
     3. `GET /api/v1/providers/weather/telemetry-feed` (HTTP 200, records present, cadence 60s)
     4. `POST /api/v1/ingest/reading` (HTTP 200, accepted: true, valid ingestion_id)
     5. `GET /api/v1/ingest/sensors/diagnostic` (HTTP 200, station active)
5. **Execute E2E Live Verification**:
   - Run `py scripts/verify_live_endpoints.py <public-https-url>` and record complete stdout.
   - Run `py scripts/airsense_serial_live_bridge.py --simulate --cloud-url <public-https-url>/api/v1/ingest/reading` to verify physical sensor packet simulation forwards to the live public HTTPS endpoint.
6. **Report**:
   - Write comprehensive report to `c:\Users\HP\AirSense-v2\.agents\worker_m3_m4_1\handoff.md`.

## 2026-09-04T13:29:33Z
You are worker_m3_m4_1 (teamwork_preview_worker).
Your working directory is: c:\Users\HP\AirSense-v2\.agents\worker_m3_m4_1
The authoritative user request is: c:\Users\HP\AirSense-v2\ORIGINAL_REQUEST.md
Your dispatch instructions are at: c:\Users\HP\AirSense-v2\.agents\worker_m3_m4_1\DISPATCH.md

Read ORIGINAL_REQUEST.md and DISPATCH.md first.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your tasks:
1. Initialize git repo if not present, commit current state, check GitHub CLI / sync repository AirSense-v2 for Render Cloud Blueprint sync.
2. Ensure backend (apps.api.main:app) is running with background scheduler active.
3. Launch Cloudflare Tunnel using `cloudflared.exe` targeting `http://127.0.0.1:8000` to establish a persistent public HTTPS URL.
4. Implement `scripts/verify_live_endpoints.py` per `explorer_survey_bridge_tests_1/handoff.md §4.2`.
5. Run live programmatic verification against the generated public HTTPS URL:
   - `py scripts/verify_live_endpoints.py <public-https-url>`
   - `py scripts/airsense_serial_live_bridge.py --simulate --cloud-url <public-https-url>/api/v1/ingest/reading`
6. Write your handoff report in `c:\Users\HP\AirSense-v2\.agents\worker_m3_m4_1\handoff.md` and message back with full results and public HTTPS URL.


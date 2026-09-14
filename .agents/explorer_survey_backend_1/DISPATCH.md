# Task Assignment: Backend & Scheduler Architecture Survey

## Identity
- Role: Codebase & Backend Explorer
- Working Directory: c:\Users\HP\AirSense-v2\.agents\explorer_survey_backend_1\
- Parent: orchestrator_3 (Conversation ID: d855ea29-0400-4419-801f-9d26248c059f)

## Objective
Survey the AirSense Pakistan FastAPI backend, database configuration, and autonomous 24/7 background scheduler in detail.

## Context & Authoritative References
- Original User Request: c:\Users\HP\AirSense-v2\ORIGINAL_REQUEST.md
- Project Scope: c:\Users\HP\AirSense-v2\PROJECT.md
- Backend code: c:\Users\HP\AirSense-v2\apps\api\

## Tasks to Investigate
1. Inspect `apps/api/main.py`, `apps/api/core/config.py`, `apps/api/db/`, and all routers under `apps/api/routers/` or `apps/api/v1/`.
2. Verify all endpoints required by R2:
   - `/api/v1/health/liveness`
   - `/api/v1/health/readiness`
   - `/api/v1/ingest/reading`
   - `/api/v1/ingest/sensors/diagnostic`
   - `/api/v1/providers/weather/telemetry-feed`
3. Inspect the 24/7 background scheduler implementation:
   - How does the 60s meteorological stream run?
   - How does the 10s node watchdog run?
   - How do daily backups run?
   - Is it managed via FastAPI lifespan or APScheduler / background tasks?
4. Inspect database connection and migrations (SQLite vs PostgreSQL, asyncpg, aiosqlite, table initialization).
5. Document exact commands and requirements to start the backend locally on Windows (e.g. uvicorn port, env variables).


## Output Deliverable
Write a comprehensive report to `c:\Users\HP\AirSense-v2\.agents\explorer_survey_backend_1\handoff.md`. Include exact file paths, code snippets, dependencies, and recommendations for deployment.
When done, message orchestrator_3 with a brief notification referencing `handoff.md`.

## 2026-09-04T13:08:10Z
Survey the AirSense Pakistan FastAPI backend (`apps/api/`), database setup, and autonomous 24/7 background scheduler.
Investigate:
1. `apps/api/main.py`, `apps/api/core/config.py`, `apps/api/db/`, and routers.
2. The 5 required production endpoints: `/api/v1/health/liveness`, `/api/v1/health/readiness`, `/api/v1/ingest/reading`, `/api/v1/ingest/sensors/diagnostic`, `/api/v1/providers/weather/telemetry-feed`.
3. 24/7 background scheduler implementation (60s meteorological stream, 10s node watchdog, daily backups).
4. Database initialization and migrations.
5. Exact startup commands and dependency environment.
Write your findings to c:\Users\HP\AirSense-v2\.agents\explorer_survey_backend_1\handoff.md. When done, send a message to orchestrator_3 (ID: d855ea29-0400-4419-801f-9d26248c059f) notifying completion.


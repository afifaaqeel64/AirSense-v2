# AirSense Pakistan Known Gaps and Issues

This document catalogues all missing, broken, unsafe, obsolete, or unverifiable components identified during the Phase 1 Repository Audit.

| Item ID | Category | Description | Impact | Current Status | Remediation Required |
| --- | --- | --- | --- | --- | --- |
| GAP-001 | City Scope | Codebase and documentation hardcoded for Lahore as primary city. | High | Obsolete | Refactor schemas, routes, and config to support Islamabad and Karachi pilot locations. |
| GAP-002 | Contacts | Legacy documentation references outdated team members. | Medium | Obsolete | Update contacts to Muhammad M. Qureshi (Islamabad) and Areesha (Karachi). |
| GAP-003 | Model Ingest | `predictor.py` uses `np.random.normal(0, 5)` for scalar predictions when MLflow model is absent. | High | Unsafe | Remove synthetic random generation. Return explicit `empty_state` or `configuration_required`. |
| GAP-004 | Multi-Campus | Database schemas (`db/init.sql`) do not track campus entity or station ownership cleanly across multiple cities. | High | Missing | Update entity model to include Campus, Station, Device, RawReading, Observation. |
| GAP-005 | Environment | Runtime lacks Docker and Node.js in system PATH; Python is main available runtime. | High | Environment Limitation | Support Mode A execution: local Python runtime with SQLite fallback. |
| GAP-006 | Directory Names | Malformed directory names (`{backend`, `{tasks,migrations}`, `{hooks,services,components,utils}`) exist in tree. | Low | Malformed Scaffolding | Consolidate directory structure without deleting user source files. |
| GAP-007 | Database URL | Backend configuration defaults to PostgreSQL/TimescaleDB URL (`postgresql+asyncpg://...`), causing immediate crash on SQLite. | High | Broken | Implement fallback database URL parsing supporting SQLite (`sqlite+aiosqlite:///./airsense.db`). |
| GAP-008 | Coordinates | Coordinates for Islamabad and Karachi campus rooftops are missing. | Medium | Configuration Required | Set to `configuration_required` in defaults; load via environment variables. |
| GAP-009 | Timezone | System timestamps not explicitly converted to UTC internally and Asia/Karachi for display. | Medium | Inconsistent | Enforce UTC for database timestamps and Asia/Karachi conversion in API responses. |
| GAP-010 | Infrastructure | Heavy dependencies (Celery, Airflow, MLflow, Redis) hardcoded in startup paths. | High | Over-engineered | Replace with APScheduler / lightweight threading and local model file serialization. |

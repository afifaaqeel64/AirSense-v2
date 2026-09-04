# AirSense Pakistan Requirements Traceability Matrix (RTM)

This matrix maps system requirements for Phase 4 to implemented architectural components, APIs, and verification results.

| Req ID | Description | Source | Priority | Implemented Component | API Endpoint | Verification Method | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | Support dual campus pilot locations (Islamabad & Karachi) | Project Charter | Critical | Domain Architecture (`Campus` Entity) | `GET /api/v1/campuses` | `test_health.py` & bootstrap verification | Complete |
| REQ-002 | Logical separation of Islamabad and Karachi campuses | Security / Domain Rule | Critical | API Routers & DB Queries | `GET /api/v1/campuses/{code}` | DB campus filtering test | Complete |
| REQ-003 | Live ESP32 sensor ingestion with authentication | Ingestion Spec | High | `apps/api/routers/ingest_router.py` | `POST /api/v1/ingest/reading` | `test_ingestion_api.py` (Valid/Invalid token tests) | Complete |
| REQ-004 | Batch CSV upload with mapping and preview | Ingestion Spec | High | `apps/api/routers/import_router.py` | `POST /api/v1/imports/csv/preview` | `test_csv_imports.py` preview test | Complete |
| REQ-005 | Two-stage CSV commit with rejected row reporting | Ingestion Spec | High | `apps/api/routers/import_router.py` | `POST /api/v1/imports/csv/commit` | `test_csv_imports.py` commit test | Complete |
| REQ-006 | Zero-cost local execution on SQLite (Mode A) | Architecture Rule | Critical | Core Database Layer (`config.py` & `session.py`) | `GET /api/v1/health` | `test_health.py` on SQLite database | Complete |
| REQ-007 | UTC internal timestamp storage & Asia/Karachi display | Timezone Rule | High | Core DB & Serializers | All API responses | Timestamp conversion unit tests | Complete |
| REQ-008 | Data Quality Assessment pipeline (limits, PM order, RH>90%) | Quality Control Spec | High | `services/quality_control/qc_engine.py` | `GET /api/v1/quality/summary` | `test_qc_engine.py` (Physical limits & ordering tests) | Complete |
| REQ-009 | Short-gap interpolation (max 2h) & Hourly circular wind mean | Aggregation Spec | High | `services/quality_control/gap_and_aggregation.py` | `GET /api/v1/hourly-observations` | Aggregation & interpolation unit assertions | Complete |
| REQ-010 | Data readiness calculator for forecasting models | Readiness Spec | High | `services/forecasting/readiness_and_health.py` | `GET /api/v1/data-readiness` | Readiness endpoint integration test | Complete |
| REQ-011 | Zero-cost Tier 1 weather & AQI sync (Open-Meteo) | Provider Spec | High | `services/external_providers/` | `POST /api/v1/providers/admin/{provider}/sync` | Provider adapter unit tests | Complete |
| REQ-012 | Redact all secrets and credentials in docs/logs | Security Rule | Critical | Security Middleware & Hashing | Device Auth & Loggers | `test_security.py` token hashing verification | Complete |
| REQ-013 | Streaming CSV data exports | Export Spec | High | `apps/api/routers/export_router.py` | `GET /api/v1/exports/readings.csv` | Export streaming response test | Complete |
| REQ-014 | Operational HTML/JS web control interface | UI / UX Spec | Medium | `apps/web/index.html` | `GET /` or `GET /ops` | Web page rendering test | Complete |

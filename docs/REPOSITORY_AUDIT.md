# AirSense Pakistan Repository Audit

## 1. Executive Summary

This technical audit documents the existing state of the AirSense repository before initiating Phase 4 implementation. The codebase contains legacy prototype files, partial FastAPI service scaffolding, malformed bash-expansion directory names, and hardcoded single-city assumptions for Lahore. The project is being transitioned to AirSense Pakistan, focusing on two pilot campus locations: Islamabad campus and Karachi campus.

## 2. Repository Status and Environment

- **Target Path**: `d:\MUNIM - UOE @BIC\AirSense`
- **Host OS**: Windows
- **Python Runtime**: Python 3.12.6 (`py` launcher available, `pip` 24.2 installed)
- **Node.js Runtime**: Unavailable in PATH
- **Docker / Docker Compose**: Unavailable in PATH
- **Git Status**: Git executable is not installed or not in PATH. No active `.git` repository was initialized.
- **Git Recommendation**: Initialize Git repository after creating `.gitignore` to prevent accidental tracking of local databases, virtual environments, or credentials.

## 3. Directory Structure Summary

```
d:\MUNIM - UOE @BIC\AirSense\
├── AirSense - Budget Appendix.pdf
├── AirSenseDashboard-try.jsx
├── AirSense_Deployable_Platform.zip
├── AirSense_Master_Technical_Blueprint.md
├── AirSense_README.md
├── BUDGET APPENDIX/
├── Campus Deployment - LATEST/
│   ├── AirSense_Budget_Appendix.xlsx
│   ├── AirSense_Campus_Proposal.pdf
│   ├── AirSense_Hardware_Framework.pdf
│   ├── AirSense_Vendor_Pricing_Report.pdf
│   ├── Final-files-for-email/
│   └── KARACHI CAMPUIS/
├── Hardware Requirements.xlsx
├── Key files to create.txt
├── pm25_budget_appendix_university_style (1).docx
├── pm25_budget_appendix_university_style (2).docx
├── pm25_pakistan_local_pricing_report (1).pdf
└── AirSense_Deployable_Platform/airsense/
    ├── .env.example
    ├── README.md
    ├── docker-compose.yml
    ├── {backend/                      [Malformed directory name]
    ├── backend/
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── app/
    │   │   ├── main.py
    │   │   ├── api/v1/ (admin.py, aqi.py, auth.py, stations.py)
    │   │   ├── core/ (config.py, metrics.py)
    │   │   ├── db/ (database.py, redis_client.py, timescale.py)
    │   │   ├── ml/ (predictor.py)
    │   │   └── services/ (alert_service.py, aqi_service.py)
    │   ├── tasks/
    │   ├── tests/
    │   └── {tasks,migrations}/       [Malformed directory name]
    ├── frontend/
    │   ├── Dockerfile
    │   └── nginx.frontend.conf
    ├── frontend_patches/
    │   └── src/
    │       └── {hooks,services,components,utils}/ [Malformed directory name]
    ├── db/ (init.sql, multi_db.sh)
    ├── nginx/
    ├── monitoring/
    └── scripts/
```

## 4. Malformed Directories Found

The existing repository contained several directories created via unexpanded shell commands:
1. `AirSense_Deployable_Platform/airsense/{backend`
2. `AirSense_Deployable_Platform/airsense/backend/{tasks,migrations}`
3. `AirSense_Deployable_Platform/airsense/frontend_patches/src/{hooks,services,components,utils}`

These directories represent empty shell artifacts and should be consolidated into standard modular paths without deleting user source files.

## 5. Existing Technology Stack

- **Backend Framework**: FastAPI 0.111.0 with Uvicorn 0.29.0
- **Database Layer**: SQLAlchemy 2.0.30, Alembic 1.13.1, asyncpg 0.29.0 (configured for TimescaleDB / PostgreSQL)
- **Caching & Async Queue**: Redis 5.0.4, Celery 5.3.6 (Over-engineered for pilot; deferred per Rule 15)
- **Workflow & ML Management**: Airflow, MLflow 2.13.0 (Deferred per Rule 15)
- **Machine Learning**: scikit-learn 1.4.2, XGBoost 2.0.3, PyTorch 2.3.0, NumPy 1.26.4, Pandas 2.2.2
- **Frontend Prototype**: React component in `AirSenseDashboard-try.jsx` using Recharts

## 6. Frontend and UI Audit

- **`AirSenseDashboard-try.jsx`**: Prototype UI hardcoded for 5 Lahore stations (US Consulate, Jail Road, PCRWR, DHA Phase 5, Gulberg III). Uses `Math.random()` to generate fake real-time readings and hardcoded decision advisory responses.
- **Classification**: Static / Synthetic Prototype.
- **Remediation**: Needs refactoring to accept real multi-campus data (Islamabad campus & Karachi campus), remove random data generation, and render clean state indicators.

## 7. Backend and API Audit

- **`backend/app/main.py`**: FastAPI entry point. Includes endpoints `/health`, `/metrics`, and `/api/v1/` routes.
- **Startup Dependencies**: Fails startup cleanly if TimescaleDB or Redis is missing. Needs fallback to SQLite and lightweight in-memory cache for zero-cost operation.
- **Routes Audit**:
  - `GET /health`: Degrades if PostgreSQL connection fails. Needs SQLite awareness.
  - `GET /api/v1/aqi/current/{city}`: Hardcoded for single-city parameters.
  - `POST /api/v1/aqi/forecast`: Calls `predictor.py`.

## 8. Machine Learning and Data Audit

- **`backend/app/ml/predictor.py`**: Implements feature engineering with lags (1h, 2h, 3h, 6h, 12h, 24h) and rolling means.
- **Time-Series Leakage Audit**:
  - **Issue 1**: In `predictor.py` line 82, rolling windows use `.rolling(win, min_periods=1).mean()`. Centred windows are not explicitly used, but feature calculation occurs prior to train-test boundary checks in historical DAGs.
  - **Issue 2**: Synthetic random variation (`np.random.normal(0, 5)`) is appended when scalar predictions are returned, violating Rule 3 (no fabricated values).
- **Historical Benchmark Reference**:
  - Model: Multiple Linear Regression
  - Historical MAE: 49.27 micrograms per cubic metre
  - Historical R2: 0.412
  - Dataset: 123,134 Islamabad meteorological records (August 2021 to June 2024)
  - Correlation: Pressure Pearson correlation 0.342
  - Status: Documented historical benchmark. Requires empirical validation upon dataset ingest.

## 9. Security and Secret Audit

- **Scan Results**: No live production API keys or tokens were found committed in plain text.
- **Configurations Scanned**: `.env.example`, `docker-compose.yml`, `backend/app/core/config.py`.
- **Findings**: Default placeholder strings like `dev-jwt-secret-change-in-production` and empty strings for API keys.
- **Risk Mitigation**: Ensure `.env` is strictly excluded in `.gitignore`.

## 10. Legacy Content and Scope Mismatches

1. **City Scope**: Legacy documentation and code refer heavily to Lahore as the sole primary city. The pilot scope for AirSense Pakistan requires Islamabad campus and Karachi campus.
2. **Team References**: Previous documentation contained obsolete team member lists. Contacts for Campus Pilot Phase 1 are:
   - Islamabad campus: Muhammad M. Qureshi
   - Karachi campus: Areesha
3. **Over-engineered Stack**: Legacy scaffolds included Celery, Airflow, MLflow, TimescaleDB, and Mapbox tokens. Zero-cost constraints require SQLite/PostgreSQL, local scheduling, and open-source maps.

## 11. Reusability Classification

- **Reusable with Modification**:
  - FastAPI schema structure and route handlers.
  - Pydantic models for sensor payloads.
  - Docker Compose service definitions (for Mode B deployment).
  - Data ingestion normalization logic.
- **Obsolete / Defer**:
  - Airflow DAGs (replaced by lightweight background scheduler or cron).
  - MLflow hot-reload thread (replaced by local file-based model serialization).
  - Lahore-only initial seed scripts.

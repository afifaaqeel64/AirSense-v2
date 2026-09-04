# AirSense Pakistan Implementation Plan

## 1. Overview and Workstreams

This document outlines the step-by-step technical implementation plan for AirSense Pakistan across all planned future development phases. The project is currently at the completion of Phase 3 (Foundation Setup).

## 2. Workstreams

- **WS1: Database & Core Domain Scaffolding** (SQLAlchemy models, Alembic migrations, SQLite/Postgres dual compatibility, Campus seed logic).
- **WS2: Ingestion & Quality Control Engine** (ESP32 HTTP ingestion API, CSV batch upload processor, QC flag validation rules).
- **WS3: External Data Provider Integration** (Open-Meteo Weather & Air Quality Tier 1 adapters, caching, rate limiting).
- **WS4: Machine Learning & Forecasting Pipeline** (Feature store, chronological walk-forward split, models: Persistence, Linear Regression, Decision Tree, Random Forest, XGBoost, LightGBM, prediction intervals, SHAP explanations).
- **WS5: Dashboard & Environmental Intelligence Interface** (React mission control, multi-campus views for Islamabad and Karachi, historical explorer, model lab).
- **WS6: Testing & Operational Readiness** (Unit tests, integration tests, end-to-end verification, deployment runbooks).

## 3. Implementation Sequence & File Change Plan

### Phase 4 (Next Phase: Core Backend Ingestion & Database)
- Implement `apps/api/core/config.py` dual database loader.
- Create ORM models in `apps/api/models/` (Campus, Station, Device, RawReading, QualityAssessment, Observation).
- Implement `POST /api/v1/ingest/sensor` for ESP32 readings with payload verification.
- Implement `POST /api/v1/ingest/csv` with mapping preview and validation.

### Phase 5 (External Providers & Weather Sync)
- Build Tier 1 Open-Meteo weather and air quality provider client (`services/external_providers/open_meteo.py`).
- Implement provider health monitor and execution logging.

### Phase 6 (ML Forecasting & Validation)
- Implement feature engineering (`ml/features/feature_pipeline.py`) avoiding centered rolling windows.
- Implement chronological walk-forward cross-validation splitter (`ml/validation/walk_forward.py`).
- Build model trainers for Baseline Linear Regression, Random Forest, and XGBoost.
- Serialize trained models cleanly to `data/models/`.

### Phase 7 (Environmental Intelligence Dashboard)
- Build multi-campus dashboard components supporting Islamabad and Karachi campus selection.
- Implement clear empty states, error states, and stale data indicators (no random mock data!).

## 4. Rollback and Safety Plan

- All database modifications must be managed via non-destructive Alembic migrations.
- Production deployment scripts must perform database backups prior to schema migration.
- If a new model underperforms baseline persistence, automated rollback to baseline occurs.

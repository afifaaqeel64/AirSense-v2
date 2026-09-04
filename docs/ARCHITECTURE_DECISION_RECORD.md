# AirSense Pakistan Architecture Decision Record (ADR)

## 1. Context and Problem Statement

AirSense Pakistan requires a production-quality, zero-cost campus air-quality intelligence and PM2.5 forecasting platform for two pilot locations:
1. Islamabad campus (Contact: Muhammad M. Qureshi)
2. Karachi campus (Contact: Areesha)

The platform must ingest live ESP32 sensor readings, accept batch CSV uploads, fetch free external weather/AQI data, perform data quality assessments, generate hourly datasets, train PM2.5 forecasting models using chronological walk-forward validation, and present insights via an environmental intelligence dashboard.

The system must run without paid core dependencies (Mode A: Local laptop with SQLite; Mode B: Campus machine with Docker Compose & PostgreSQL; Mode C: Free-tier compatible cloud hosting).

## 2. Technical Stack Decision Matrix

| Technology | Existing Repository State | Target Decision | Rationale | Cost Implication | Risk |
| --- | --- | --- | --- | --- | --- |
| Backend Framework | FastAPI 0.111.0 | Retain FastAPI | High performance, native async, automatic OpenAPI docs. | Zero cost | Low |
| Database Layer | SQLAlchemy + asyncpg (TimescaleDB) | Dual Driver: SQLite (Dev/Mode A) & PostgreSQL (Prod/Mode B) | Enables instant local execution on laptop without Docker, while maintaining production path. | Zero cost | Low |
| Caching | Redis | In-Memory TTL Cache (Mode A) / Redis (Mode B) | Eliminates hard requirement for Redis service during local development. | Zero cost | Low |
| Task Scheduler | Celery + Airflow | APScheduler / Python Background Tasks | Replaces heavy JVM/Airflow stack with lightweight zero-cost in-process scheduler (Rule 15). | Zero cost | Low |
| Machine Learning | scikit-learn, XGBoost, LightGBM | Retain scikit-learn, XGBoost, LightGBM | Standard production ML stack for time-series forecasting. | Zero cost | Low |
| ML Management | MLflow | File-Based ML Artifact Registry (`data/models/`) | Removes MLflow server dependency while preserving versioned model loading (Rule 15). | Zero cost | Low |
| Frontend Stack | React + Recharts Prototype | Modular React + Vanilla CSS Design System | Responsive, zero-cost, high aesthetic quality dashboard. | Zero cost | Low |

## 3. Multi-Campus Domain Architecture

Entities defined for multi-campus isolation:

1. **Campus**: `id` (PK), `code` (e.g. `ISB_CAMPUS`, `KHI_CAMPUS`), `name`, `city`, `contact_name`, `latitude`, `longitude`, `status` (`configuration_required` if coordinates missing).
2. **Station**: `id` (PK), `campus_id` (FK), `name`, `station_type` (`onsite_esp32`, `external_provider`), `is_active`.
3. **Device**: `id` (PK), `station_id` (FK), `mac_address`, `device_token_hash`, `firmware_version`, `status`.
4. **RawReading**: `id` (PK), `timestamp` (UTC), `device_id` (FK), `campus_id` (FK), `raw_payload` (JSONB/Text), `ingest_source` (`esp32_http`, `csv_upload`).
5. **QualityAssessment**: `id` (PK), `raw_reading_id` (FK), `qc_flag` (`pass`, `range_violation`, `stuck_sensor`, `spike`), `score` (0.0 - 1.0).
6. **Observation**: `id` (PK), `timestamp` (UTC), `campus_id` (FK), `station_id` (FK), `pm25`, `pm10`, `temperature`, `humidity`, `qc_status`.
7. **ImportBatch**: `id` (PK), `filename`, `campus_id` (FK), `row_count`, `valid_count`, `committed_at`.
8. **ExternalProviderRun**: `id` (PK), `provider_name`, `campus_id` (FK), `status`, `fetched_records`, `executed_at`.
9. **ModelRun**: `id` (PK), `model_id`, `campus_id` (FK), `algorithm`, `train_mae`, `train_r2`, `val_mae`, `val_r2`, `created_at`.
10. **Prediction**: `id` (PK), `model_run_id` (FK), `campus_id` (FK), `horizon_hours` (1, 3, 6, 24), `target_timestamp` (UTC), `predicted_pm25`, `interval_lower`, `interval_upper`.
11. **ExternalComparison**: `id` (PK), `campus_id` (FK), `timestamp` (UTC), `airsense_pm25`, `provider_pm25`, `provider_name`.
12. **Alert**: `id` (PK), `campus_id` (FK), `severity`, `rule_name`, `triggered_at`, `status`.

## 4. Data-Flow Architecture

- **Flow A (Live Sensor)**: ESP32 -> Token Auth -> Validation -> Idempotency Check -> Raw Reading -> QC Processing -> Accepted Observation -> Station Health -> Model Feature Store.
- **Flow B (CSV Upload)**: User Upload -> CSV Validation -> Mapping & Unit Confirmation -> Preview -> User Commit -> Deduplication -> Raw Storage -> QC Pipeline -> Historical Explorer.
- **Flow C (External Providers)**: Scheduler -> Provider Adapter -> HTTP Request -> Execution Log -> Normalized Observation -> Source Attribution -> Campus Assignment -> Comparison View.
- **Flow D (ML Forecasting)**: Accepted Observations -> Hourly Aggregation -> QC Filtering -> Feature Engineering (Lags, Sin/Cos Hour, Rolling Means) -> Walk-Forward Validation Split -> Model Training -> Registry Persistence -> Prediction with Confidence Intervals.
- **Flow E (Alert Evaluation)**: Prediction / Observation -> Threshold Rule Evaluation -> Alert Log Generation -> Actual Value Reconciliation -> Pilot Metrics View.

## 5. Zero-Cost Deployment Modes

- **Mode A (Development / Local Laptop)**: FastApi + SQLite (`airsense.db`) + Local In-Memory Cache + Local File Models. Zero external service requirement.
- **Mode B (Campus Local Server)**: Docker Compose + FastAPI + PostgreSQL / TimescaleDB + Redis. Baseline reliability mode.
- **Mode C (Free-Tier Hosting)**: Compatible with free cloud application hosting (e.g. Render / Railway free tier) with documented limitations.

## 6. Migration and Future Scalability Path

- SQLite to PostgreSQL schema compatibility is enforced via SQLAlchemy ORM abstractions.
- Database timestamp columns are explicitly typed `DateTime(timezone=True)` storing UTC.
- Future TimescaleDB hypertable conversion maps cleanly to `timestamp` and `campus_id` partitioning keys.

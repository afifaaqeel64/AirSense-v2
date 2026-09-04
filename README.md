# AirSense Pakistan

**Production-Quality, Zero-Cost Campus Air-Quality Intelligence & PM2.5 Forecasting Platform**

AirSense Pakistan provides hyper-local environmental intelligence and PM2.5 forecasting for campus pilot locations in Pakistan:

1. **Islamabad Campus** (Contact: Muhammad M. Qureshi)
2. **Karachi Campus** (Contact: Areesha)

---

## 1. Overview

AirSense Pakistan is designed to:
- Ingest live telemetry from onsite ESP32 sensor stations.
- Accept batch CSV dataset uploads with column mapping and quality checks.
- Synchronize free weather and air quality observations from Tier 1 providers (Open-Meteo).
- Validate readings via automated data quality control (QC) pipelines.
- Generate hourly aggregated datasets for ML model training.
- Train multi-horizon PM2.5 forecasting models (1, 3, 6, 24 hours) using chronological walk-forward validation.
- Compute prediction intervals and model explainability (SHAP).
- Display real-time telemetry, forecasts, and health advisories via an environmental intelligence dashboard.
- Operate locally on standard laptop hardware (SQLite) or campus servers (Docker Compose + PostgreSQL) at zero software licensing cost.

---

## 2. Platform Architecture & Modes

- **Mode A (Development / Local Laptop)**: FastAPI + SQLite (`./data/airsense.db`) + Local In-Memory Cache. Zero external dependencies required.
- **Mode B (Campus Server / Docker Compose)**: Docker Compose + FastAPI + PostgreSQL / TimescaleDB + Redis. Production baseline mode.
- **Mode C (Free Cloud Hosting)**: Compatible with free hosting tiers (e.g. Render, Railway) with documented limitations.

---

## 3. Quick Start (Mode A - Local Python Execution)

### Step 1: Clone & Configure
```bash
cp .env.example .env
```

### Step 2: Install Dependencies
```bash
py -m pip install -r requirements.txt
```

### Step 3: Run Backend API
```bash
py -m uvicorn apps.api.main:app --reload --port 8000
```

### Step 4: Verify System Health
Open your browser or run:
```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
curl http://localhost:8000/api/v1/version
curl http://localhost:8000/api/v1/campuses
```

---

## 4. Operational Principles & Rules

1. **AirSense** is the only active project name.
2. No fabricated readings, metrics, predictions, or system status.
3. No hardcoded credentials or committed `.env` files.
4. Future timestamps are stored in **UTC** and displayed in **Asia/Karachi** time.
5. **Islamabad campus** and **Karachi campus** are logically separated.
6. Unknown rooftop coordinates or missing configurations are marked `configuration_required`.

---

## 5. Repository Documentation Index

- [Repository Audit](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/REPOSITORY_AUDIT.md)
- [Architecture Decision Record](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/ARCHITECTURE_DECISION_RECORD.md)
- [Implementation Plan](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/IMPLEMENTATION_PLAN.md)
- [Requirements Traceability Matrix](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/REQUIREMENTS_TRACEABILITY_MATRIX.md)
- [API Integration Matrix](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/API_INTEGRATION_MATRIX.md)
- [Data Dictionary](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/DATA_DICTIONARY.md)
- [Security Notes](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/SECURITY_NOTES.md)
- [Deployment Guide](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/DEPLOYMENT_GUIDE.md)
- [Zero-Cost Deployment Guide](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/ZERO_COST_DEPLOYMENT.md)
- [Sensor Onboarding Guide](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/SENSOR_ONBOARDING.md)
- [Operations Runbook](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/OPERATIONS_RUNBOOK.md)
- [Handover Summary](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/HANDOVER_SUMMARY.md)
- [Remaining Actions](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/REMAINING_ACTIONS.md)

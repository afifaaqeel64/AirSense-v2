# AirSense — Master Technical Blueprint
## From Ready Frontend to Live, Self-Sustaining Platform

> **Author:** AirSense Strategy & Architecture Team  
> **Phase:** Lahore Launch (Phase 1)  
> **Status:** Implementation Ready  
> **Date:** April 2026

---

## TABLE OF CONTENTS

1. [Executive Vision & Architecture Philosophy](#1-executive-vision)
2. [Full System Architecture](#2-full-system-architecture)
3. [Data Infrastructure — Lahore Data Sources & Real-Time APIs](#3-data-infrastructure)
4. [Automated ML Pipeline](#4-automated-ml-pipeline)
5. [Backend API Design](#5-backend-api-design)
6. [Database Schema](#6-database-schema)
7. [Frontend Improvements & Completion](#7-frontend-improvements)
8. [DevOps, Deployment & CI/CD](#8-devops-and-deployment)
9. [Security, Compliance & Monitoring](#9-security-and-monitoring)
10. [Phased Roadmap](#10-phased-roadmap)
11. [Step-by-Step Implementation Guide](#11-step-by-step-implementation-guide)
12. [Budget & Resource Estimation](#12-budget-and-resource-estimation)

---

## 1. EXECUTIVE VISION

AirSense is a real-time, AI-powered air quality intelligence platform. Its core promise: turn fragmented, unreliable environmental data into actionable, hyper-local air quality intelligence — starting with Lahore, one of the most polluted cities on Earth.

### The Core Engine (Three Pillars)

```
┌─────────────────────────────────────────────────────────┐
│                    AIRSENSE CORE ENGINE                 │
├─────────────────┬──────────────────┬────────────────────┤
│   DATA PILLAR   │   MODEL PILLAR   │  INTERFACE PILLAR  │
│                 │                  │                    │
│ Real-time APIs  │ Auto-Training    │ Web Dashboard      │
│ IoT Sensors     │ AQI Prediction   │ Mobile App         │
│ Satellite Data  │ Health Risk      │ Public API         │
│ Weather Feeds   │ Forecast Engine  │ Alert System       │
│ Historical DB   │ Anomaly Detect.  │ Embed Widgets      │
└─────────────────┴──────────────────┴────────────────────┘
```

### Why Lahore First
- Lahore consistently ranks in the Top 5 most polluted cities globally
- Punjab EPA has existing monitoring infrastructure (partial)
- Dense urban population = maximum impact
- Islamabad model provides transfer learning foundation
- Government partnerships more accessible (Punjab govt)

---

## 2. FULL SYSTEM ARCHITECTURE

### 2.1 High-Level Architecture

```
                        ┌─────────────────────────────────┐
                        │         EXTERNAL WORLD          │
                        │                                 │
                        │  [OpenAQ] [IQAir] [WAQI]       │
                        │  [Punjab EPA] [PakMet]          │
                        │  [Sentinel-5P] [MODIS]          │
                        │  [OpenWeather] [IoT Sensors]    │
                        └────────────┬────────────────────┘
                                     │ HTTPS / MQTT / FTP
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION LAYER                        │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │  API Fetcher  │  │ Stream Ingest│  │  Batch File Processor │   │
│  │  (Celery)     │  │  (Kafka)     │  │  (Airflow DAG)        │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬────────────┘   │
│         └─────────────────┴──────────────────────┘                │
│                            │                                       │
│                    ┌───────▼────────┐                             │
│                    │  Data Validator │                             │
│                    │  & Normalizer   │                             │
│                    └───────┬────────┘                             │
└────────────────────────────┼───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER                              │
│                                                                    │
│  ┌────────────────┐  ┌───────────────┐  ┌──────────────────────┐ │
│  │  TimescaleDB   │  │    Redis       │  │    S3 / MinIO        │ │
│  │  (Time-series) │  │  (Cache/Queue) │  │  (Model Artifacts,  │ │
│  │  Raw + Agg.    │  │                │  │   Raw Files, Logs)  │ │
│  └────────────────┘  └───────────────┘  └──────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              PostgreSQL (Metadata, Users, Config)            │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                       ML PIPELINE LAYER                            │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    MLflow + Airflow DAGs                      │ │
│  │                                                               │ │
│  │  [Data Trigger] → [Feature Eng.] → [Training] → [Eval]      │ │
│  │       │                                              │        │ │
│  │       │                                    [Registry]│        │ │
│  │       ▼                                              ▼        │ │
│  │  [Watchdog]                              [Auto Deploy]        │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  Models: AQI Predictor | Health Risk | 24h Forecast | Anomaly     │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                      API / BACKEND LAYER                           │
│                                                                    │
│              FastAPI Application (Python 3.11+)                   │
│                                                                    │
│  /api/v1/aqi          /api/v1/forecast    /api/v1/health          │
│  /api/v1/heatmap      /api/v1/alerts      /api/v1/historical      │
│  /api/v1/stations     /api/v1/compare     /api/v1/export          │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Auth (JWT)  │  │  Rate Limiter │  │  WebSocket Server    │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                      FRONTEND LAYER                                │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   React Web App  │  │  Mobile App  │  │  Embeddable       │   │
│  │   (Dashboard)    │  │  (React Nat.)│  │  Widget (iframe)  │   │
│  └──────────────────┘  └──────────────┘  └──────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Backend Framework | FastAPI (Python 3.11) | Async, fast, auto OpenAPI docs |
| Task Queue | Celery + Redis | Scheduled data fetching, async jobs |
| Workflow Orchestration | Apache Airflow | Complex DAG pipelines, ML triggers |
| Stream Processing | Apache Kafka | Real-time sensor data streams |
| Primary Database | TimescaleDB (PostgreSQL ext.) | Native time-series, SQL, hypertables |
| Cache | Redis | AQI lookups, session, rate limiting |
| Object Storage | AWS S3 / MinIO (self-hosted) | Model files, raw data, exports |
| ML Framework | scikit-learn, XGBoost, PyTorch | Prediction models |
| ML Ops | MLflow | Experiment tracking, model registry |
| Containerization | Docker + Docker Compose | Dev/prod parity |
| Orchestration | Kubernetes (prod) | Scaling, self-healing |
| CI/CD | GitHub Actions | Automated testing + deployment |
| Reverse Proxy | Nginx | SSL termination, load balancing |
| Frontend | React + TypeScript | Existing frontend |
| Maps | Mapbox GL JS / Leaflet | Air quality heatmaps |
| Monitoring | Grafana + Prometheus | System + model metrics |

---

## 3. DATA INFRASTRUCTURE

### 3.1 Lahore-Specific Data Sources

This is the most critical step. AirSense needs authoritative, multi-source data for Lahore.

#### PRIMARY FREE/OPEN SOURCES

```python
LAHORE_DATA_SOURCES = {
    # SOURCE 1: OpenAQ — Best open-air quality database
    "openaq": {
        "url": "https://api.openaq.org/v3/locations",
        "params": {
            "city": "Lahore",
            "country": "PK",
            "limit": 100,
            "parameters": ["pm25", "pm10", "no2", "so2", "co", "o3"]
        },
        "api_key": "OPENAQ_API_KEY",  # Free tier: 10k req/day
        "update_frequency": "hourly",
        "historical_available": True,
        "historical_from": "2018-01-01"
    },
    
    # SOURCE 2: WAQI (World Air Quality Index)
    "waqi": {
        "url": "https://api.waqi.info/feed/@{station_id}/",
        "lahore_stations": {
            "lahore_us_consulate": "@7165",
            "lahore_punjab_epa": "@A316285",
            "lahore_fcc": "@A362621",
            "gulberg": "@A298761",
            "johar_town": "@A316286"
        },
        "api_key": "WAQI_TOKEN",  # Free
        "update_frequency": "real-time (hourly avg)"
    },
    
    # SOURCE 3: Punjab EPA (Pakistan)
    "punjab_epa": {
        "url": "http://epd.punjab.gov.pk/",  # Scrape or formal request
        "note": "File formal data-sharing MOU with Punjab EPA",
        "stations": [
            "Lahore Cantt", "Gulshan Ravi", "Township", 
            "Model Town", "DHA", "Johar Town", "Wapda Town"
        ],
        "update_frequency": "hourly",
        "requires_partnership": True
    },
    
    # SOURCE 4: IQAir (AirVisual)
    "iqair": {
        "url": "https://api.airvisual.com/v2/city",
        "params": {"city": "Lahore", "state": "Punjab", "country": "Pakistan"},
        "api_key": "IQAIR_API_KEY",
        "update_frequency": "hourly",
        "includes": ["aqi_us", "aqi_cn", "weather", "pm25", "pm10"]
    },
    
    # SOURCE 5: NASA FIRMS / Satellite
    "nasa_modis": {
        "url": "https://firms.modaps.eosdis.nasa.gov/api/area/",
        "type": "fire_hotspots",  # Major PM2.5 source in Punjab
        "bbox": "73.9,31.2,74.7,31.8",  # Lahore bounding box
        "api_key": "NASA_FIRMS_KEY",  # Free
        "update_frequency": "daily"
    },
    
    # SOURCE 6: Sentinel-5P (Satellite NO2, SO2, CO, O3)
    "sentinel_5p": {
        "url": "https://dataspace.copernicus.eu/",
        "product": "L2__NO2___",  # NO2 tropospheric column
        "area": {"lat_min": 31.2, "lat_max": 31.8, "lon_min": 73.9, "lon_max": 74.7},
        "update_frequency": "daily",
        "free": True
    },
    
    # SOURCE 7: OpenWeatherMap (Weather context for models)
    "openweathermap": {
        "url": "https://api.openweathermap.org/data/2.5/air_pollution",
        "params": {"lat": 31.5497, "lon": 74.3436},  # Lahore center
        "api_key": "OWM_API_KEY",
        "update_frequency": "hourly",
        "includes": ["pm2_5", "pm10", "no2", "o3", "so2", "co", "nh3"]
    },
    
    # SOURCE 8: Pakistan Meteorological Department
    "pakmet": {
        "url": "http://www.pmd.gov.pk/",
        "note": "File formal request — provides wind, humidity, temperature data",
        "data": ["temperature", "humidity", "wind_speed", "wind_direction", "pressure"],
        "update_frequency": "3-hourly",
        "requires_partnership": True
    }
}
```

#### HISTORICAL LAHORE DATA COLLECTION STRATEGY

```python
# Step 1: Pull all available historical data via OpenAQ
# OpenAQ has Lahore data going back to 2016

import requests
import pandas as pd
from datetime import datetime, timedelta

def fetch_openaq_historical_lahore():
    """Fetch complete historical Lahore dataset from OpenAQ."""
    
    base_url = "https://api.openaq.org/v3/measurements"
    
    # Lahore station IDs from OpenAQ
    lahore_locations = get_lahore_locations()
    
    all_data = []
    
    for location in lahore_locations:
        page = 1
        while True:
            response = requests.get(
                base_url,
                params={
                    "locations_id": location["id"],
                    "date_from": "2018-01-01T00:00:00Z",
                    "date_to": datetime.utcnow().isoformat() + "Z",
                    "limit": 1000,
                    "page": page,
                    "parameters_id": [2, 1, 3, 7, 6, 5]  # pm25,pm10,no2,so2,co,o3
                },
                headers={"X-API-Key": OPENAQ_API_KEY}
            )
            
            data = response.json()
            if not data["results"]:
                break
                
            all_data.extend(data["results"])
            page += 1
            
    return pd.DataFrame(all_data)

def get_lahore_locations():
    """Get all active monitoring stations in Lahore."""
    response = requests.get(
        "https://api.openaq.org/v3/locations",
        params={
            "bbox": "73.9,31.2,74.7,31.8",
            "limit": 100
        },
        headers={"X-API-Key": OPENAQ_API_KEY}
    )
    return response.json()["results"]
```

### 3.2 Real-Time Data Ingestion Pipeline

#### Celery Task Scheduler (`tasks/data_fetchers.py`)

```python
from celery import Celery
from celery.schedules import crontab
import requests, json
from datetime import datetime
from app.db.timescale import insert_measurement
from app.core.validator import validate_and_normalize

app = Celery('airsense', broker='redis://redis:6379/0')

# ─── SCHEDULED TASKS ────────────────────────────────────────────

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Real-time sources: every 30 minutes
    sender.add_periodic_task(1800.0, fetch_waqi_lahore.s(), name='waqi-30min')
    sender.add_periodic_task(1800.0, fetch_openaq_lahore.s(), name='openaq-30min')
    sender.add_periodic_task(1800.0, fetch_iqair_lahore.s(), name='iqair-30min')
    sender.add_periodic_task(3600.0, fetch_owm_lahore.s(), name='owm-1hr')
    
    # Satellite data: daily at 6am
    sender.add_periodic_task(
        crontab(hour=6, minute=0),
        fetch_sentinel5p.s(),
        name='sentinel-daily'
    )
    sender.add_periodic_task(
        crontab(hour=6, minute=30),
        fetch_nasa_firms.s(),
        name='firms-daily'
    )
    
    # Model retrain check: every 6 hours
    sender.add_periodic_task(
        crontab(hour='*/6'),
        check_and_trigger_retraining.s(),
        name='retrain-check-6hr'
    )


@app.task(bind=True, max_retries=3, default_retry_delay=300)
def fetch_waqi_lahore(self):
    """Fetch real-time AQI from WAQI for all Lahore stations."""
    
    LAHORE_STATIONS = {
        "us_consulate": "@7165",
        "punjab_epa": "@A316285",
        "gulberg": "@A298761",
    }
    
    results = []
    for station_name, station_id in LAHORE_STATIONS.items():
        try:
            url = f"https://api.waqi.info/feed/{station_id}/?token={WAQI_TOKEN}"
            r = requests.get(url, timeout=10)
            data = r.json()
            
            if data["status"] == "ok":
                measurement = validate_and_normalize({
                    "source": "waqi",
                    "station": station_name,
                    "city": "lahore",
                    "timestamp": datetime.utcnow(),
                    "aqi": data["data"]["aqi"],
                    "pm25": data["data"]["iaqi"].get("pm25", {}).get("v"),
                    "pm10": data["data"]["iaqi"].get("pm10", {}).get("v"),
                    "no2": data["data"]["iaqi"].get("no2", {}).get("v"),
                    "so2": data["data"]["iaqi"].get("so2", {}).get("v"),
                    "co": data["data"]["iaqi"].get("co", {}).get("v"),
                    "o3": data["data"]["iaqi"].get("o3", {}).get("v"),
                    "temperature": data["data"]["iaqi"].get("t", {}).get("v"),
                    "humidity": data["data"]["iaqi"].get("h", {}).get("v"),
                    "wind_speed": data["data"]["iaqi"].get("w", {}).get("v"),
                    "lat": data["data"]["city"]["geo"][0],
                    "lon": data["data"]["city"]["geo"][1],
                })
                
                insert_measurement(measurement)
                results.append(measurement)
                
        except Exception as exc:
            raise self.retry(exc=exc)
    
    # Signal to check if retraining is needed
    check_data_threshold.delay()
    return {"fetched": len(results), "source": "waqi"}


@app.task
def fetch_openaq_lahore():
    """Fetch latest measurements from OpenAQ for Lahore."""
    url = "https://api.openaq.org/v3/measurements"
    
    response = requests.get(
        url,
        params={
            "city": "Lahore",
            "country": "PK",
            "limit": 500,
            "date_from": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"
        },
        headers={"X-API-Key": OPENAQ_API_KEY},
        timeout=30
    )
    
    measurements = response.json().get("results", [])
    
    for m in measurements:
        normalized = validate_and_normalize({
            "source": "openaq",
            "station": m["location"],
            "city": "lahore",
            "timestamp": m["date"]["utc"],
            m["parameter"]: m["value"],
            "lat": m["coordinates"]["latitude"],
            "lon": m["coordinates"]["longitude"],
            "unit": m["unit"]
        })
        insert_measurement(normalized)
    
    return {"fetched": len(measurements), "source": "openaq"}


@app.task
def check_data_threshold():
    """Check if enough new data has arrived to trigger model retraining."""
    from app.db.timescale import count_new_records_since_last_train
    from app.ml.pipeline import trigger_retraining
    
    new_records = count_new_records_since_last_train()
    
    # Retrain when 500+ new records OR 24 hours have passed
    if new_records >= 500:
        trigger_retraining.delay(reason="data_threshold", new_records=new_records)
        return {"triggered": True, "reason": "threshold", "records": new_records}
    
    return {"triggered": False, "records": new_records}
```

### 3.3 Data Validation & Normalization

```python
# app/core/validator.py

from dataclasses import dataclass
from typing import Optional
import numpy as np

# WHO & US EPA AQI limits for validation
PARAMETER_LIMITS = {
    "pm25":  {"min": 0, "max": 1000, "unit": "µg/m³"},
    "pm10":  {"min": 0, "max": 2000, "unit": "µg/m³"},
    "no2":   {"min": 0, "max": 5000, "unit": "µg/m³"},
    "so2":   {"min": 0, "max": 3000, "unit": "µg/m³"},
    "co":    {"min": 0, "max": 50000, "unit": "µg/m³"},
    "o3":    {"min": 0, "max": 1000, "unit": "µg/m³"},
    "aqi":   {"min": 0, "max": 999},
    "temperature": {"min": -30, "max": 60, "unit": "°C"},
    "humidity":    {"min": 0, "max": 100, "unit": "%"},
    "wind_speed":  {"min": 0, "max": 150, "unit": "m/s"},
}

def validate_and_normalize(raw: dict) -> dict:
    """Validate incoming measurement data and normalize units."""
    
    cleaned = {}
    
    for param, limits in PARAMETER_LIMITS.items():
        val = raw.get(param)
        if val is None:
            continue
        
        # Type coercion
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue
        
        # Range validation
        if not (limits["min"] <= val <= limits["max"]):
            # Log anomaly but don't discard — flag it
            cleaned[f"{param}_flagged"] = True
            val = np.clip(val, limits["min"], limits["max"])
        
        cleaned[param] = val
    
    # Unit conversions (some sources report ppb, we store µg/m³)
    if "no2_ppb" in raw:
        cleaned["no2"] = raw["no2_ppb"] * 1.88  # ppb to µg/m³
    
    if "so2_ppb" in raw:
        cleaned["so2"] = raw["so2_ppb"] * 2.62
    
    # Metadata
    cleaned["source"] = raw.get("source", "unknown")
    cleaned["station"] = raw.get("station")
    cleaned["city"] = raw.get("city", "lahore").lower()
    cleaned["lat"] = raw.get("lat")
    cleaned["lon"] = raw.get("lon")
    cleaned["timestamp"] = raw.get("timestamp")
    cleaned["data_quality_score"] = compute_quality_score(cleaned)
    
    return cleaned


def compute_quality_score(measurement: dict) -> float:
    """Score data quality 0-1 based on completeness and consistency."""
    key_params = ["pm25", "pm10", "aqi", "temperature", "humidity"]
    present = sum(1 for p in key_params if p in measurement)
    completeness = present / len(key_params)
    
    flagged = sum(1 for k in measurement if k.endswith("_flagged"))
    flags_penalty = flagged * 0.1
    
    return max(0.0, min(1.0, completeness - flags_penalty))
```

---

## 4. AUTOMATED ML PIPELINE

This is the heart of what makes AirSense "live." Models must train themselves as data flows in.

### 4.1 Pipeline Architecture

```
NEW DATA ARRIVES
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA WATCHDOG SERVICE                         │
│  Monitors new_records_count, time_since_last_train              │
│  Triggers: ≥500 new records OR 24h elapsed                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │  TRIGGER
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  AIRFLOW DAG: airsense_retrain                   │
│                                                                  │
│  Task 1: extract_features                                        │
│    └─ Pull last N days from TimescaleDB                         │
│    └─ Generate lag features, rolling averages                   │
│    └─ Merge weather + pollution + satellite                     │
│                                                                  │
│  Task 2: validate_dataset                                        │
│    └─ Min row count check                                        │
│    └─ Feature completeness check                                 │
│    └─ Distribution drift detection                               │
│                                                                  │
│  Task 3: train_models (parallel)                                 │
│    ├─ AQI Predictor (XGBoost)                                   │
│    ├─ 24h Forecaster (LSTM)                                     │
│    ├─ Health Risk Classifier (Random Forest)                     │
│    └─ Anomaly Detector (Isolation Forest)                       │
│                                                                  │
│  Task 4: evaluate_models                                         │
│    └─ Compare vs production model                               │
│    └─ Must improve RMSE by ≥1% to promote                       │
│                                                                  │
│  Task 5: promote_or_rollback                                     │
│    └─ Register in MLflow Model Registry                         │
│    └─ Tag as "Production" if metrics pass                       │
│    └─ Hot-reload in API (zero downtime)                         │
│                                                                  │
│  Task 6: notify                                                  │
│    └─ Slack/Email: training summary + metrics                   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Airflow DAG Definition

```python
# airflow/dags/airsense_retrain_dag.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

default_args = {
    'owner': 'airsense',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['ml-alerts@airsense.pk'],
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

with DAG(
    'airsense_model_retrain',
    default_args=default_args,
    description='Auto-retrain AirSense ML models when new data arrives',
    schedule_interval=None,   # Triggered by data watchdog, not schedule
    start_date=days_ago(1),
    catchup=False,
    tags=['ml', 'lahore', 'airsense'],
    max_active_runs=1,        # Never run two retrains simultaneously
) as dag:

    extract = PythonOperator(
        task_id='extract_features',
        python_callable=extract_feature_set,
        op_kwargs={'city': 'lahore', 'lookback_days': 90}
    )

    validate = PythonOperator(
        task_id='validate_dataset',
        python_callable=validate_training_data,
    )

    # Parallel training of all model types
    train_aqi = PythonOperator(
        task_id='train_aqi_predictor',
        python_callable=train_aqi_model,
        op_kwargs={'city': 'lahore'}
    )

    train_forecast = PythonOperator(
        task_id='train_forecast_model',
        python_callable=train_lstm_forecaster,
        op_kwargs={'city': 'lahore', 'horizon_hours': 24}
    )

    train_health = PythonOperator(
        task_id='train_health_classifier',
        python_callable=train_health_risk_model,
        op_kwargs={'city': 'lahore'}
    )

    train_anomaly = PythonOperator(
        task_id='train_anomaly_detector',
        python_callable=train_anomaly_model,
        op_kwargs={'city': 'lahore'}
    )

    evaluate = PythonOperator(
        task_id='evaluate_all_models',
        python_callable=evaluate_and_compare,
    )

    promote = PythonOperator(
        task_id='promote_or_rollback',
        python_callable=promote_best_models,
    )

    notify = PythonOperator(
        task_id='send_training_report',
        python_callable=send_training_notification,
    )

    # DAG topology
    extract >> validate >> [train_aqi, train_forecast, train_health, train_anomaly]
    [train_aqi, train_forecast, train_health, train_anomaly] >> evaluate
    evaluate >> promote >> notify
```

### 4.3 Feature Engineering

```python
# ml/features/engineer.py

import pandas as pd
import numpy as np
from app.db.timescale import get_measurements

def extract_feature_set(city: str, lookback_days: int = 90) -> pd.DataFrame:
    """Build ML-ready feature matrix from raw measurements."""
    
    df = get_measurements(city=city, days=lookback_days)
    
    # ── TEMPORAL FEATURES ─────────────────────────────────────
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['month'] = df['timestamp'].dt.month
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['is_rush_hour'] = df['hour'].isin([7,8,9,17,18,19]).astype(int)
    
    # Lahore-specific: Friday prayers spike (12-2pm Friday)
    df['is_friday_peak'] = (
        (df['day_of_week'] == 4) & (df['hour'].between(12, 14))
    ).astype(int)
    
    # Winter crop burning season (Oct-Nov)
    df['is_burning_season'] = df['month'].isin([10, 11]).astype(int)
    
    # ── LAG FEATURES (past pollution levels) ──────────────────
    for pollutant in ['pm25', 'pm10', 'no2']:
        for lag in [1, 2, 3, 6, 12, 24]:  # hours
            df[f'{pollutant}_lag_{lag}h'] = df[pollutant].shift(lag)
    
    # ── ROLLING STATISTICS ────────────────────────────────────
    for pollutant in ['pm25', 'pm10']:
        for window in [3, 6, 12, 24, 48]:
            df[f'{pollutant}_roll_mean_{window}h'] = (
                df[pollutant].rolling(window, min_periods=1).mean()
            )
            df[f'{pollutant}_roll_std_{window}h'] = (
                df[pollutant].rolling(window, min_periods=1).std()
            )
    
    # ── METEOROLOGICAL FEATURES ───────────────────────────────
    # Wind direction as cyclical features
    df['wind_sin'] = np.sin(np.radians(df['wind_direction']))
    df['wind_cos'] = np.cos(np.radians(df['wind_direction']))
    
    # Temperature inversions (key for Lahore smog)
    df['temp_change_3h'] = df['temperature'].diff(3)
    df['low_wind_high_pm'] = (
        (df['wind_speed'] < 2) & (df['pm25'] > 100)
    ).astype(int)
    
    # ── INTERACTION FEATURES ──────────────────────────────────
    df['pm25_temp_interaction'] = df['pm25'] * df['temperature']
    df['pm25_humidity_ratio'] = df['pm25'] / (df['humidity'] + 1)
    
    # Drop rows with too many NaN (first few hours)
    df = df.dropna(thresh=int(len(df.columns) * 0.7))
    
    return df


def compute_aqi_from_pm25(pm25: float) -> int:
    """US EPA AQI breakpoints for PM2.5."""
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]
    for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
        if bp_lo <= pm25 <= bp_hi:
            return int(((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm25 - bp_lo) + aqi_lo)
    return 500  # Beyond scale
```

### 4.4 Model Definitions

```python
# ml/models/aqi_predictor.py — XGBoost AQI Prediction

import mlflow
import mlflow.xgboost
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np

def train_aqi_model(city: str, **context):
    """Train XGBoost AQI prediction model with MLflow tracking."""
    
    mlflow.set_experiment(f"aqi-predictor-{city}")
    
    with mlflow.start_run(run_name=f"lahore-xgb-{context['ds']}"):
        
        # Load feature set from XCom (Airflow inter-task communication)
        df = context['ti'].xcom_pull(task_ids='extract_features', key='feature_df')
        
        feature_cols = [c for c in df.columns if c not in [
            'aqi', 'pm25', 'pm10', 'timestamp', 'station', 'source'
        ]]
        
        X = df[feature_cols].fillna(0)
        y = df['aqi']
        
        # Time-series cross validation (no data leakage)
        tscv = TimeSeriesSplit(n_splits=5)
        
        params = {
            'n_estimators': 500,
            'max_depth': 6,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'gamma': 0.1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'tree_method': 'hist',
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
        }
        
        mlflow.log_params(params)
        
        cv_scores = []
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            model = xgb.XGBRegressor(**params, early_stopping_rounds=50)
            model.fit(
                X.iloc[train_idx], y.iloc[train_idx],
                eval_set=[(X.iloc[val_idx], y.iloc[val_idx])],
                verbose=False
            )
            preds = model.predict(X.iloc[val_idx])
            rmse = np.sqrt(mean_squared_error(y.iloc[val_idx], preds))
            mae = mean_absolute_error(y.iloc[val_idx], preds)
            cv_scores.append({'rmse': rmse, 'mae': mae})
        
        avg_rmse = np.mean([s['rmse'] for s in cv_scores])
        avg_mae = np.mean([s['mae'] for s in cv_scores])
        
        mlflow.log_metric("cv_rmse", avg_rmse)
        mlflow.log_metric("cv_mae", avg_mae)
        
        # Final model on full data
        final_model = xgb.XGBRegressor(**params)
        final_model.fit(X, y)
        
        mlflow.xgboost.log_model(
            final_model,
            artifact_path="model",
            registered_model_name=f"aqi-predictor-lahore"
        )
        
        return {"rmse": avg_rmse, "mae": avg_mae, "run_id": mlflow.active_run().info.run_id}


# ml/models/forecaster.py — LSTM 24h Forecast

import torch
import torch.nn as nn
import numpy as np

class AirQualityLSTM(nn.Module):
    """LSTM model for 24-hour AQI forecasting."""
    
    def __init__(self, input_size=20, hidden_size=128, num_layers=2, 
                 output_size=24, dropout=0.2):
        super().__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout
        )
        
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size, 
            num_heads=4, 
            batch_first=True
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, output_size)  # 24 hourly predictions
        )
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        out = self.fc(attn_out[:, -1, :])  # Last timestep
        return out
```

### 4.5 Model Promotion & Hot-Reload

```python
# ml/registry.py — Zero-downtime model updates

import mlflow
from mlflow.tracking import MlflowClient
import threading
import time

client = MlflowClient()

# Thread-safe model holder
_model_lock = threading.RLock()
_models = {}

def get_production_model(model_name: str):
    """Get current production model (thread-safe)."""
    with _model_lock:
        return _models.get(model_name)


def hot_reload_models():
    """Background thread that checks for new production models every 5 minutes."""
    while True:
        for model_name in ["aqi-predictor-lahore", "forecaster-lahore", 
                           "health-risk-lahore", "anomaly-lahore"]:
            try:
                latest = client.get_latest_versions(model_name, stages=["Production"])
                if latest:
                    model = mlflow.pyfunc.load_model(f"models:/{model_name}/Production")
                    with _model_lock:
                        _models[model_name] = model
            except Exception as e:
                print(f"Model reload failed for {model_name}: {e}")
        
        time.sleep(300)  # Check every 5 minutes


def promote_best_models(**context):
    """Compare new model metrics against production, promote if better."""
    
    results = context['ti'].xcom_pull(task_ids=[
        'train_aqi_predictor', 'train_forecast_model',
        'train_health_classifier', 'train_anomaly_detector'
    ])
    
    for model_name, result in zip(
        ["aqi-predictor-lahore", "forecaster-lahore", 
         "health-risk-lahore", "anomaly-lahore"],
        results
    ):
        # Get production model metrics
        try:
            prod_versions = client.get_latest_versions(model_name, stages=["Production"])
            if prod_versions:
                prod_run = client.get_run(prod_versions[0].run_id)
                prod_rmse = prod_run.data.metrics.get("cv_rmse", float('inf'))
                new_rmse = result.get("rmse", float('inf'))
                
                # Only promote if ≥1% improvement
                if new_rmse < prod_rmse * 0.99:
                    client.transition_model_version_stage(
                        name=model_name,
                        version=result["version"],
                        stage="Production",
                        archive_existing_versions=True
                    )
                    print(f"✓ Promoted {model_name}: RMSE {prod_rmse:.2f} → {new_rmse:.2f}")
                else:
                    print(f"✗ {model_name} not promoted: {new_rmse:.2f} vs {prod_rmse:.2f}")
            else:
                # No production model yet — always promote first one
                client.transition_model_version_stage(
                    name=model_name,
                    version=result["version"],
                    stage="Production"
                )
        except Exception as e:
            print(f"Promotion failed for {model_name}: {e}")
```

---

## 5. BACKEND API DESIGN

### 5.1 FastAPI Application Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── core/
│   │   ├── config.py            # Settings (env vars)
│   │   ├── security.py          # JWT auth
│   │   └── validator.py         # Data validation
│   ├── api/
│   │   └── v1/
│   │       ├── router.py        # All routes
│   │       ├── aqi.py           # AQI endpoints
│   │       ├── forecast.py      # Forecast endpoints
│   │       ├── health.py        # Health risk endpoints
│   │       ├── heatmap.py       # Spatial heatmap data
│   │       ├── alerts.py        # Alert management
│   │       ├── historical.py    # Historical data + export
│   │       ├── stations.py      # Station metadata
│   │       └── auth.py          # Auth endpoints
│   ├── db/
│   │   ├── timescale.py         # TimescaleDB queries
│   │   ├── postgres.py          # PostgreSQL (users, config)
│   │   └── redis.py             # Cache layer
│   ├── ml/
│   │   ├── predictor.py         # Inference wrapper
│   │   ├── registry.py          # MLflow model loading
│   │   └── features/
│   │       └── engineer.py      # Feature engineering
│   └── services/
│       ├── aqi_service.py       # Business logic
│       ├── alert_service.py     # Alert logic
│       └── notification.py     # Email/SMS/Push
├── tasks/                       # Celery tasks
├── airflow/dags/               # Airflow DAGs
├── ml/                         # ML model training code
├── tests/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### 5.2 Core API Endpoints

```python
# app/api/v1/aqi.py

from fastapi import APIRouter, Query, Depends
from app.services.aqi_service import AQIService
from app.db.redis import cache_response

router = APIRouter(prefix="/aqi", tags=["AQI"])

@router.get("/current/{city}")
@cache_response(ttl=300)  # Cache 5 minutes
async def get_current_aqi(
    city: str,
    station: str = Query(None, description="Specific station ID")
):
    """Get current real-time AQI for a city or specific station."""
    return await AQIService.get_current(city=city, station=station)


@router.get("/heatmap/{city}")
@cache_response(ttl=600)
async def get_aqi_heatmap(
    city: str,
    resolution: float = Query(0.01, description="Grid resolution in degrees"),
    parameter: str = Query("aqi", enum=["aqi","pm25","pm10","no2"])
):
    """Get interpolated spatial AQI grid for heatmap rendering."""
    return await AQIService.get_spatial_grid(
        city=city, 
        resolution=resolution,
        parameter=parameter
    )


@router.get("/forecast/{city}")
@cache_response(ttl=1800)
async def get_forecast(
    city: str,
    hours: int = Query(24, ge=1, le=72),
    station: str = Query(None)
):
    """Get ML-powered 24-72 hour AQI forecast."""
    return await AQIService.get_forecast(city=city, hours=hours, station=station)


@router.get("/historical/{city}")
async def get_historical(
    city: str,
    start_date: str = Query(..., description="ISO 8601 date"),
    end_date: str = Query(..., description="ISO 8601 date"),
    parameter: str = Query("aqi"),
    aggregation: str = Query("hourly", enum=["raw","hourly","daily","monthly"]),
    station: str = Query(None)
):
    """Get historical AQI data with flexible aggregation."""
    return await AQIService.get_historical(
        city=city, start=start_date, end=end_date,
        param=parameter, agg=aggregation, station=station
    )


@router.websocket("/live/{city}")
async def aqi_live_stream(websocket, city: str):
    """WebSocket stream for real-time AQI updates."""
    await websocket.accept()
    try:
        while True:
            data = await AQIService.get_current(city=city)
            await websocket.send_json(data)
            await asyncio.sleep(30)  # Push every 30s
    except WebSocketDisconnect:
        pass


# app/api/v1/health.py

@router.get("/risk/{city}")
async def get_health_risk(
    city: str,
    sensitive_group: bool = Query(False, description="Elevated risk for children/elderly/asthma")
):
    """Get health risk assessment + recommendations."""
    aqi_data = await AQIService.get_current(city=city)
    risk = await HealthService.assess_risk(
        aqi=aqi_data["aqi"], 
        pm25=aqi_data.get("pm25"),
        sensitive=sensitive_group
    )
    return {
        "aqi": aqi_data["aqi"],
        "category": risk["category"],
        "color": risk["color"],
        "health_message": risk["message"],
        "recommendations": risk["recommendations"],
        "outdoor_activity": risk["outdoor_ok"],
        "mask_recommended": risk["mask_needed"],
        "predicted_24h_risk": risk["forecast_risk"]
    }
```

### 5.3 AQI Service Business Logic

```python
# app/services/aqi_service.py

from scipy.interpolate import RBFInterpolator
import numpy as np

class AQIService:
    
    @staticmethod
    async def get_spatial_grid(city: str, resolution: float, parameter: str):
        """
        Interpolate station measurements into a smooth spatial grid
        using Radial Basis Function interpolation.
        Returns GeoJSON FeatureCollection for Mapbox heatmap layer.
        """
        
        # Get latest station readings
        stations = await db.fetch_latest_station_readings(city, parameter)
        
        if len(stations) < 3:
            return {"error": "Insufficient stations for interpolation"}
        
        points = np.array([[s["lon"], s["lat"]] for s in stations])
        values = np.array([s[parameter] for s in stations])
        
        # Build grid for Lahore bounding box
        lon_range = np.arange(73.9, 74.7, resolution)
        lat_range = np.arange(31.2, 31.8, resolution)
        
        grid_lon, grid_lat = np.meshgrid(lon_range, lat_range)
        grid_points = np.column_stack([grid_lon.ravel(), grid_lat.ravel()])
        
        # RBF Interpolation
        interpolator = RBFInterpolator(points, values, kernel='thin_plate_spline')
        grid_values = interpolator(grid_points).reshape(grid_lon.shape)
        grid_values = np.clip(grid_values, 0, 999)
        
        # Convert to GeoJSON
        features = []
        for i, lat in enumerate(lat_range):
            for j, lon in enumerate(lon_range):
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {parameter: float(grid_values[i, j])}
                })
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "parameter": parameter,
                "timestamp": datetime.utcnow().isoformat(),
                "station_count": len(stations),
                "city": city
            }
        }
    
    @staticmethod
    def categorize_aqi(aqi: int) -> dict:
        """Map AQI value to category, color, and health message."""
        categories = [
            (0, 50,   "Good",       "#00E400", "Air quality is satisfactory."),
            (51, 100,  "Moderate",   "#FFFF00", "Acceptable; some pollutants may affect very sensitive people."),
            (101, 150, "Unhealthy for Sensitive Groups", "#FF7E00", "Sensitive groups may experience health effects."),
            (151, 200, "Unhealthy",  "#FF0000", "Everyone may begin to experience health effects."),
            (201, 300, "Very Unhealthy", "#8F3F97", "Health alert: everyone may experience serious effects."),
            (301, 500, "Hazardous",  "#7E0023", "Emergency conditions. Entire population likely affected."),
        ]
        for lo, hi, cat, color, msg in categories:
            if lo <= aqi <= hi:
                return {"category": cat, "color": color, "message": msg}
        return {"category": "Beyond Index", "color": "#000000", "message": "Extremely hazardous."}
```

---

## 6. DATABASE SCHEMA

### 6.1 TimescaleDB (Time-Series Data)

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ─── CORE MEASUREMENTS TABLE ─────────────────────────────────────
CREATE TABLE measurements (
    id              BIGSERIAL,
    timestamp       TIMESTAMPTZ NOT NULL,
    city            VARCHAR(50) NOT NULL DEFAULT 'lahore',
    station_id      VARCHAR(100),
    source          VARCHAR(50) NOT NULL,  -- openaq, waqi, iqair, punjab_epa
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    
    -- Pollutants (µg/m³)
    pm25            FLOAT,
    pm10            FLOAT,
    no2             FLOAT,
    so2             FLOAT,
    co              FLOAT,
    o3              FLOAT,
    nh3             FLOAT,
    
    -- Derived
    aqi             INTEGER,
    aqi_category    VARCHAR(50),
    
    -- Meteorological
    temperature     FLOAT,
    humidity        FLOAT,
    wind_speed      FLOAT,
    wind_direction  FLOAT,
    pressure        FLOAT,
    
    -- Quality
    data_quality_score  FLOAT DEFAULT 1.0,
    pm25_flagged        BOOLEAN DEFAULT FALSE,
    
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable (TimescaleDB magic — automatic partitioning by time)
SELECT create_hypertable('measurements', 'timestamp',
    chunk_time_interval => INTERVAL '7 days'
);

-- Compression policy (data older than 30 days compressed)
SELECT add_compression_policy('measurements', INTERVAL '30 days');

-- Retention policy (raw data kept for 2 years)
SELECT add_retention_policy('measurements', INTERVAL '2 years');

-- Continuous aggregate: hourly averages (auto-updated)
CREATE MATERIALIZED VIEW measurements_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS hour,
    city,
    station_id,
    AVG(pm25)  AS pm25,
    AVG(pm10)  AS pm10,
    AVG(no2)   AS no2,
    AVG(so2)   AS so2,
    AVG(aqi)   AS aqi,
    AVG(temperature) AS temperature,
    AVG(humidity)    AS humidity,
    COUNT(*)   AS reading_count
FROM measurements
GROUP BY hour, city, station_id
WITH NO DATA;

-- Auto-refresh hourly aggregate
SELECT add_continuous_aggregate_policy('measurements_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- Daily aggregates
CREATE MATERIALIZED VIEW measurements_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day,
    city,
    AVG(pm25) AS pm25_avg,
    MAX(pm25) AS pm25_max,
    MIN(pm25) AS pm25_min,
    AVG(aqi)  AS aqi_avg,
    MAX(aqi)  AS aqi_max
FROM measurements
GROUP BY day, city
WITH NO DATA;

-- ─── ML TRAINING REGISTRY ─────────────────────────────────────
CREATE TABLE ml_training_log (
    id              SERIAL PRIMARY KEY,
    run_id          VARCHAR(100) UNIQUE NOT NULL,
    model_name      VARCHAR(100) NOT NULL,
    city            VARCHAR(50)  NOT NULL,
    triggered_by    VARCHAR(50),     -- 'data_threshold', 'scheduled', 'manual'
    new_records     INTEGER,
    training_rows   INTEGER,
    cv_rmse         FLOAT,
    cv_mae          FLOAT,
    promoted        BOOLEAN DEFAULT FALSE,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'running'  -- running, success, failed
);
```

### 6.2 PostgreSQL (Application Data)

```sql
-- ─── USERS ─────────────────────────────────────────────────────
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),
    full_name       VARCHAR(100),
    city            VARCHAR(50) DEFAULT 'lahore',
    role            VARCHAR(20) DEFAULT 'user',  -- user, admin, partner
    api_key         VARCHAR(64) UNIQUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE
);

-- ─── ALERT SUBSCRIPTIONS ───────────────────────────────────────
CREATE TABLE alert_subscriptions (
    id              SERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    city            VARCHAR(50) NOT NULL,
    station_id      VARCHAR(100),
    threshold_aqi   INTEGER NOT NULL DEFAULT 150,
    channel         VARCHAR(20) NOT NULL,  -- email, sms, push, webhook
    contact_info    VARCHAR(255) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── MONITORING STATIONS ───────────────────────────────────────
CREATE TABLE stations (
    id              VARCHAR(100) PRIMARY KEY,
    city            VARCHAR(50) NOT NULL,
    name            VARCHAR(100),
    source          VARCHAR(50),
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    area_type       VARCHAR(50),  -- residential, industrial, traffic, background
    is_active       BOOLEAN DEFAULT TRUE,
    added_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Lahore stations seed data
INSERT INTO stations VALUES
    ('lahore_us_consulate', 'lahore', 'US Consulate Lahore', 'waqi', 31.5204, 74.3587, 'urban', TRUE, NOW()),
    ('lahore_punjab_epa',   'lahore', 'Punjab EPA HQ',       'waqi', 31.5167, 74.3500, 'urban', TRUE, NOW()),
    ('lahore_gulberg',      'lahore', 'Gulberg',             'waqi', 31.5120, 74.3500, 'residential', TRUE, NOW()),
    ('lahore_johar_town',   'lahore', 'Johar Town',          'waqi', 31.4697, 74.2728, 'residential', TRUE, NOW()),
    ('lahore_dha',          'lahore', 'DHA Phase 5',         'waqi', 31.4812, 74.4022, 'residential', TRUE, NOW()),
    ('lahore_kot_lakhpat',  'lahore', 'Kot Lakhpat Industrial', 'punjab_epa', 31.5200, 74.2700, 'industrial', TRUE, NOW());
```

---

## 7. FRONTEND IMPROVEMENTS

### 7.1 What Needs to Be Fixed/Added

The existing frontend needs these critical additions to become production-ready:

#### A) Real WebSocket Integration (Replace Mock Data)

```javascript
// src/hooks/useAirQuality.js — Replace any mock/static data

import { useState, useEffect, useRef, useCallback } from 'react';

export const useAirQuality = (city = 'lahore', stationId = null) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const wsRef = useRef(null);
    const reconnectRef = useRef(null);
    
    const connectWebSocket = useCallback(() => {
        const wsUrl = `${process.env.REACT_APP_WS_URL}/api/v1/aqi/live/${city}`;
        
        wsRef.current = new WebSocket(wsUrl);
        
        wsRef.current.onopen = () => {
            setError(null);
            console.log('AirSense live feed connected');
        };
        
        wsRef.current.onmessage = (event) => {
            const payload = JSON.parse(event.data);
            setData(payload);
            setLoading(false);
        };
        
        wsRef.current.onclose = () => {
            // Exponential backoff reconnect
            const delay = Math.min(1000 * 2 ** reconnectRef.current, 30000);
            reconnectRef.current = (reconnectRef.current || 0) + 1;
            setTimeout(connectWebSocket, delay);
        };
        
        wsRef.current.onerror = (e) => {
            setError('Live feed unavailable. Showing last known data.');
        };
    }, [city]);
    
    useEffect(() => {
        reconnectRef.current = 0;
        connectWebSocket();
        return () => wsRef.current?.close();
    }, [connectWebSocket]);
    
    return { data, loading, error };
};
```

#### B) Dynamic Heatmap Layer (Mapbox Integration)

```javascript
// src/components/AirQualityMap.jsx

import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';

mapboxgl.accessToken = process.env.REACT_APP_MAPBOX_TOKEN;

const AQI_COLOR_STOPS = [
    [0,   '#00E400'],
    [51,  '#FFFF00'],
    [101, '#FF7E00'],
    [151, '#FF0000'],
    [201, '#8F3F97'],
    [301, '#7E0023'],
];

export const AirQualityMap = ({ city = 'lahore', parameter = 'aqi' }) => {
    const mapRef = useRef(null);
    const mapInstance = useRef(null);
    
    useEffect(() => {
        mapInstance.current = new mapboxgl.Map({
            container: mapRef.current,
            style: 'mapbox://styles/mapbox/dark-v11',
            center: [74.3436, 31.5497],  // Lahore center
            zoom: 11,
        });
        
        mapInstance.current.on('load', () => {
            loadHeatmapData(parameter);
        });
        
        // Refresh heatmap every 10 minutes
        const interval = setInterval(() => loadHeatmapData(parameter), 600000);
        return () => {
            clearInterval(interval);
            mapInstance.current?.remove();
        };
    }, []);
    
    const loadHeatmapData = async (param) => {
        const res = await fetch(
            `${process.env.REACT_APP_API_URL}/api/v1/aqi/heatmap/${city}?parameter=${param}`
        );
        const geojson = await res.json();
        
        const map = mapInstance.current;
        
        if (map.getSource('aqi-grid')) {
            map.getSource('aqi-grid').setData(geojson);
        } else {
            map.addSource('aqi-grid', { type: 'geojson', data: geojson });
            
            // Interpolated color heatmap
            map.addLayer({
                id: 'aqi-heat',
                type: 'heatmap',
                source: 'aqi-grid',
                paint: {
                    'heatmap-weight': ['interpolate', ['linear'], ['get', param], 0, 0, 500, 1],
                    'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 11, 1, 15, 3],
                    'heatmap-color': [
                        'interpolate', ['linear'], ['heatmap-density'],
                        0, 'rgba(0,228,0,0)',
                        0.2, '#00E400',
                        0.4, '#FFFF00',
                        0.6, '#FF7E00',
                        0.8, '#FF0000',
                        1.0, '#7E0023'
                    ],
                    'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 11, 20, 15, 60],
                    'heatmap-opacity': 0.75,
                }
            });
        }
    };
    
    return (
        <div 
            ref={mapRef} 
            style={{ width: '100%', height: '100%', borderRadius: '12px' }}
        />
    );
};
```

#### C) Real-Time AQI Gauge Component

```javascript
// src/components/AQIGauge.jsx

import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const AQI_ZONES = [
    { max: 50,  label: 'Good',       color: '#00E400', bg: '#001a00' },
    { max: 100, label: 'Moderate',   color: '#FFFF00', bg: '#1a1a00' },
    { max: 150, label: 'Unhealthy*', color: '#FF7E00', bg: '#1a0d00' },
    { max: 200, label: 'Unhealthy',  color: '#FF0000', bg: '#1a0000' },
    { max: 300, label: 'Very Unhlty',color: '#8F3F97', bg: '#150013' },
    { max: 500, label: 'Hazardous',  color: '#7E0023', bg: '#1a0007' },
];

const getZone = (aqi) => AQI_ZONES.find(z => aqi <= z.max) || AQI_ZONES[5];

export const AQIGauge = ({ aqi, pm25, location, lastUpdated }) => {
    const zone = getZone(aqi);
    const angle = Math.min((aqi / 500) * 180, 180) - 90;
    
    return (
        <motion.div
            className="aqi-gauge-container"
            style={{ background: zone.bg }}
            animate={{ background: zone.bg }}
            transition={{ duration: 1.5 }}
        >
            <svg viewBox="0 0 200 120" className="gauge-svg">
                {/* Background arc */}
                <path d="M 20 100 A 80 80 0 0 1 180 100" 
                      fill="none" stroke="#333" strokeWidth="12" strokeLinecap="round"/>
                
                {/* Colored progress arc */}
                <motion.path 
                    d="M 20 100 A 80 80 0 0 1 180 100"
                    fill="none" 
                    stroke={zone.color} 
                    strokeWidth="12" 
                    strokeLinecap="round"
                    style={{ filter: `drop-shadow(0 0 8px ${zone.color})` }}
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: aqi / 500 }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                />
                
                {/* Needle */}
                <motion.line
                    x1="100" y1="100" x2="100" y2="30"
                    stroke="white" strokeWidth="2" strokeLinecap="round"
                    animate={{ rotate: angle }}
                    style={{ transformOrigin: '100px 100px' }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                />
                
                {/* Center AQI value */}
                <text x="100" y="88" textAnchor="middle" 
                      fill="white" fontSize="28" fontWeight="700">
                    {aqi}
                </text>
                <text x="100" y="108" textAnchor="middle" 
                      fill={zone.color} fontSize="11" fontWeight="600">
                    {zone.label.toUpperCase()}
                </text>
            </svg>
            
            <div className="gauge-details">
                <div className="gauge-location">{location}</div>
                <div className="gauge-meta">
                    PM2.5: <span style={{ color: zone.color }}>{pm25 || '—'} µg/m³</span>
                </div>
                <div className="gauge-updated">
                    Updated: {new Date(lastUpdated).toLocaleTimeString()}
                </div>
            </div>
        </motion.div>
    );
};
```

#### D) Environment Configuration

```bash
# .env.production
REACT_APP_API_URL=https://api.airsense.pk
REACT_APP_WS_URL=wss://api.airsense.pk
REACT_APP_MAPBOX_TOKEN=pk.eyJ1IjoiYWlyc2Vuc2UiLCJhIjoiY...
REACT_APP_SENTRY_DSN=https://...@sentry.io/...
REACT_APP_GA_ID=G-XXXXXXXXXX

# .env.development  
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

---

## 8. DEVOPS AND DEPLOYMENT

### 8.1 Docker Compose (Development + Staging)

```yaml
# docker-compose.yml

version: '3.9'

services:
  
  # ─── DATABASES ─────────────────────────────────────────────
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: airsense
      POSTGRES_USER: airsense
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - timescale_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U airsense"]
      interval: 10s
      retries: 5
  
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
  
  # ─── MESSAGE QUEUE ─────────────────────────────────────────
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
  
  kafka:
    image: confluentinc/cp-kafka:7.4.0
    depends_on: [zookeeper]
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
    volumes:
      - kafka_data:/var/lib/kafka/data
  
  # ─── BACKEND ───────────────────────────────────────────────
  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      DATABASE_URL: postgresql://airsense:${DB_PASSWORD}@timescaledb:5432/airsense
      REDIS_URL: redis://redis:6379/0
      MLFLOW_TRACKING_URI: http://mlflow:5000
      OPENAQ_API_KEY: ${OPENAQ_API_KEY}
      WAQI_TOKEN: ${WAQI_TOKEN}
      IQAIR_API_KEY: ${IQAIR_API_KEY}
      JWT_SECRET: ${JWT_SECRET}
    depends_on:
      timescaledb:
        condition: service_healthy
      redis:
        condition: service_started
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    restart: unless-stopped
  
  # ─── CELERY WORKERS ────────────────────────────────────────
  celery-worker:
    build: ./backend
    command: celery -A tasks.app worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: postgresql://airsense:${DB_PASSWORD}@timescaledb:5432/airsense
      REDIS_URL: redis://redis:6379/0
      OPENAQ_API_KEY: ${OPENAQ_API_KEY}
      WAQI_TOKEN: ${WAQI_TOKEN}
    depends_on: [redis, timescaledb, kafka]
    restart: unless-stopped
  
  celery-beat:
    build: ./backend
    command: celery -A tasks.app beat --loglevel=info
    environment:
      REDIS_URL: redis://redis:6379/0
    depends_on: [redis]
    restart: unless-stopped
  
  # ─── ML PIPELINE ───────────────────────────────────────────
  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.11.0
    command: mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri postgresql://airsense:${DB_PASSWORD}@timescaledb:5432/mlflow --default-artifact-root s3://airsense-models/
    environment:
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
    ports:
      - "5000:5000"
    restart: unless-stopped
  
  airflow-webserver:
    image: apache/airflow:2.8.1
    command: webserver
    environment:
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql://airsense:${DB_PASSWORD}@timescaledb:5432/airflow
      AIRFLOW__CELERY__BROKER_URL: redis://redis:6379/1
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
    volumes:
      - ./airflow/dags:/opt/airflow/dags
    ports:
      - "8080:8080"
    depends_on: [timescaledb, redis]
  
  airflow-scheduler:
    image: apache/airflow:2.8.1
    command: scheduler
    environment:
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql://airsense:${DB_PASSWORD}@timescaledb:5432/airflow
    volumes:
      - ./airflow/dags:/opt/airflow/dags
    depends_on: [timescaledb, redis]
  
  # ─── FRONTEND ──────────────────────────────────────────────
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      REACT_APP_API_URL: http://localhost:8000
    restart: unless-stopped
  
  # ─── REVERSE PROXY ─────────────────────────────────────────
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - certbot_data:/var/www/certbot
    depends_on: [api, frontend]
    restart: unless-stopped
  
  # ─── MONITORING ────────────────────────────────────────────
  prometheus:
    image: prom/prometheus:v2.49.0
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:10.2.0
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3001:3000"

volumes:
  timescale_data:
  redis_data:
  kafka_data:
  grafana_data:
  certbot_data:
```

### 8.2 GitHub Actions CI/CD

```yaml
# .github/workflows/deploy.yml

name: AirSense Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: timescale/timescaledb:latest-pg15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: airsense_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      redis:
        image: redis:7-alpine
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r backend/requirements.txt
        pip install pytest pytest-asyncio httpx
    
    - name: Run tests
      run: pytest backend/tests/ -v --tb=short
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost:5432/airsense_test
        REDIS_URL: redis://localhost:6379/0
    
    - name: Build frontend
      run: |
        cd frontend && npm ci && npm run build
      env:
        REACT_APP_API_URL: https://api.airsense.pk
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Build and push Docker images
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u airsense --password-stdin
        docker build -t airsense/api:${{ github.sha }} ./backend
        docker push airsense/api:${{ github.sha }}
    
    - name: Deploy to production
      uses: appleboy/ssh-action@v1
      with:
        host: ${{ secrets.PROD_HOST }}
        username: deploy
        key: ${{ secrets.SSH_PRIVATE_KEY }}
        script: |
          cd /opt/airsense
          git pull origin main
          export API_IMAGE=airsense/api:${{ github.sha }}
          docker-compose -f docker-compose.prod.yml up -d --no-deps api celery-worker
          docker system prune -f
```

### 8.3 Nginx Configuration

```nginx
# nginx/nginx.conf

upstream api_backend {
    server api:8000;
    keepalive 64;
}

server {
    listen 80;
    server_name airsense.pk www.airsense.pk api.airsense.pk;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.airsense.pk;
    
    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    # API proxy
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # CORS
        add_header 'Access-Control-Allow-Origin' 'https://airsense.pk' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
    }
    
    # WebSocket
    location /api/v1/aqi/live/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;
    limit_req zone=api_limit burst=20 nodelay;
}

server {
    listen 443 ssl http2;
    server_name airsense.pk www.airsense.pk;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Static assets caching
    location ~* \.(js|css|png|jpg|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 9. SECURITY AND MONITORING

### 9.1 Alert System

```python
# app/services/alert_service.py

async def check_and_send_alerts(measurement: dict):
    """Run after every measurement insert — check thresholds and notify."""
    
    # Get all active subscriptions for this city
    subscriptions = await db.get_active_subscriptions(city=measurement["city"])
    
    for sub in subscriptions:
        if measurement.get("aqi", 0) >= sub["threshold_aqi"]:
            await send_alert(sub, measurement)


async def send_alert(subscription: dict, measurement: dict):
    """Send alert via configured channel."""
    
    aqi = measurement["aqi"]
    zone = AQIService.categorize_aqi(aqi)
    
    message = f"""
🚨 AirSense Alert — {measurement['city'].title()}

Current AQI: {aqi} ({zone['category']})
PM2.5: {measurement.get('pm25', 'N/A')} µg/m³
Station: {measurement.get('station', 'City Average')}
Time: {measurement['timestamp']}

{zone['message']}

Stay safe. Check airsense.pk for live updates.
    """.strip()
    
    if subscription["channel"] == "email":
        await send_email(subscription["contact_info"], 
                        f"AirSense Alert: AQI {aqi} in {measurement['city'].title()}", 
                        message)
    
    elif subscription["channel"] == "sms":
        await send_sms(subscription["contact_info"], message[:160])  # SMS limit
    
    elif subscription["channel"] == "webhook":
        await send_webhook(subscription["contact_info"], {
            "aqi": aqi, "city": measurement["city"],
            "category": zone["category"], "timestamp": measurement["timestamp"]
        })
```

### 9.2 Prometheus Metrics

```python
# app/core/metrics.py

from prometheus_client import Counter, Histogram, Gauge, generate_latest

# API metrics
REQUEST_COUNT = Counter('airsense_requests_total', 
                        'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('airsense_request_duration_seconds', 
                             'Request latency', ['endpoint'])

# Data pipeline metrics
DATA_INGESTION_COUNT = Counter('airsense_measurements_ingested_total', 
                                'Total measurements ingested', ['source', 'city'])
DATA_QUALITY_GAUGE = Gauge('airsense_data_quality_score',
                            'Average data quality score', ['source'])

# Model metrics
MODEL_PREDICTION_COUNT = Counter('airsense_predictions_total', ['model', 'city'])
MODEL_RMSE_GAUGE = Gauge('airsense_model_rmse', 'Current model RMSE', ['model', 'city'])
LAST_TRAIN_TIMESTAMP = Gauge('airsense_last_training_timestamp', 
                              'Unix timestamp of last training', ['model'])
```

---

## 10. PHASED ROADMAP

### PHASE 0 — Foundation (Weeks 1-2)
**Goal: Core infrastructure running locally**

- [ ] Set up Docker Compose with all services
- [ ] Initialize TimescaleDB with schema + Lahore stations seed
- [ ] Configure environment variables and secrets
- [ ] Pull 2 years of historical Lahore data from OpenAQ
- [ ] Verify data pipeline: fetcher → validator → database
- [ ] Run first manual model training on Lahore data
- [ ] Basic FastAPI running with 3 core endpoints
- [ ] Connect frontend env vars to local API

**Deliverable:** Local stack running, historical data loaded, first models trained

---

### PHASE 1 — MVP Live Launch (Weeks 3-5)
**Goal: Platform live at airsense.pk with real data**

- [ ] Deploy to cloud server (DigitalOcean / AWS / Hetzner)
- [ ] SSL certificate via Let's Encrypt
- [ ] All 8 real-time data sources connected and scheduled
- [ ] Celery beat running all fetch tasks on schedule
- [ ] Auto-retraining pipeline active (Airflow DAGs deployed)
- [ ] Model hot-reload working (verify with log output)
- [ ] Frontend: Replace ALL mock data with live API calls
- [ ] Frontend: Lahore heatmap with live data
- [ ] Email alert system working
- [ ] Basic monitoring (Grafana dashboard)
- [ ] WAQI, OpenAQ, IQAir all confirmed ingesting

**Deliverable:** airsense.pk is LIVE with Lahore real-time AQI

---

### PHASE 2 — Intelligence Layer (Weeks 6-8)
**Goal: AI forecasting visible and accurate**

- [ ] 24h forecast model deployed and accessible
- [ ] Health risk assessment per station
- [ ] Anomaly detection: alert on unusual pollution spikes
- [ ] Punjab EPA data partnership initiated (formal letter)
- [ ] PMD weather data integration
- [ ] Model performance dashboard in Grafana
- [ ] A/B testing framework for model versions
- [ ] Frontend: Forecast chart (24h/48h/72h toggle)
- [ ] Frontend: Health recommendations module
- [ ] Push notifications for mobile

**Deliverable:** Full AI platform working — predict, forecast, alert

---

### PHASE 3 — Scale & Polish (Weeks 9-12)
**Goal: Production-grade, scalable, partnership-ready**

- [ ] Migrate to Kubernetes
- [ ] API rate limiting + API key management (for partners)
- [ ] Public API documentation (Swagger/Redoc)
- [ ] Multi-city: Add Karachi, Islamabad alongside Lahore
- [ ] Mobile app (React Native) — basic version
- [ ] Embeddable widget for media/news sites
- [ ] Partnership integrations (Punjab EPA, PMD MOU)
- [ ] Data export (CSV/JSON) for researchers
- [ ] SEO optimization + Google indexing
- [ ] Load testing + performance optimization

**Deliverable:** Scalable multi-city platform with partner integrations

---

### PHASE 4 — Revenue & Growth (Month 4+)
**Goal: Sustainable business model**

- [ ] Premium API tier (commercial)
- [ ] Government dashboard (Punjab EPA white-label)
- [ ] Corporate AQI monitoring plans
- [ ] Research data licensing
- [ ] Expand to 10 Pakistani cities
- [ ] International: India, Bangladesh, Nepal
- [ ] iOS App Store + Google Play publishing
- [ ] NGO/UN partnerships (WHO, UNICEF environment)

---

## 11. STEP-BY-STEP IMPLEMENTATION GUIDE

### STEP 1: Environment Setup (Day 1)

```bash
# Clone and set up project structure
git clone https://github.com/airsense/platform.git
cd platform

# Create all directories
mkdir -p backend/app/{api/v1,core,db,ml/{features,models},services}
mkdir -p backend/{tasks,tests}
mkdir -p airflow/dags
mkdir -p frontend/src/{components,hooks,pages,services}
mkdir -p ml/{data,models,experiments}
mkdir -p monitoring/{dashboards,alerts}
mkdir -p nginx/ssl
mkdir -p db

# Create .env file
cat > .env << 'EOF'
DB_PASSWORD=your_secure_password_here
JWT_SECRET=your_jwt_secret_256bit
OPENAQ_API_KEY=your_openaq_key
WAQI_TOKEN=your_waqi_token
IQAIR_API_KEY=your_iqair_key
OWM_API_KEY=your_openweathermap_key
NASA_FIRMS_KEY=your_nasa_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
GRAFANA_PASSWORD=admin_password
AIRFLOW_FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
EOF

# Start all services
docker-compose up -d

# Verify all containers are healthy
docker-compose ps
```

### STEP 2: Database Initialization (Day 1)

```bash
# Run schema migrations
docker-compose exec timescaledb psql -U airsense -d airsense -f /docker-entrypoint-initdb.d/init.sql

# Verify hypertables created
docker-compose exec timescaledb psql -U airsense -d airsense -c "\d measurements"

# Verify stations seeded
docker-compose exec timescaledb psql -U airsense -d airsense -c "SELECT * FROM stations WHERE city='lahore';"
```

### STEP 3: Pull Historical Lahore Data (Day 2)

```bash
# Run the historical data pull (this takes ~2-3 hours for full history)
docker-compose exec api python -c "
from tasks.data_fetchers import fetch_openaq_historical_lahore
result = fetch_openaq_historical_lahore()
print(f'Loaded {len(result)} historical records for Lahore')
"

# Verify data loaded
docker-compose exec timescaledb psql -U airsense -d airsense -c "
SELECT 
    date_trunc('month', timestamp) as month,
    COUNT(*) as records,
    AVG(pm25) as avg_pm25,
    AVG(aqi) as avg_aqi
FROM measurements 
WHERE city = 'lahore'
GROUP BY month 
ORDER BY month DESC 
LIMIT 24;
"
```

### STEP 4: Run First Model Training (Day 2-3)

```bash
# Manually trigger the full ML pipeline
docker-compose exec airflow-webserver airflow dags trigger airsense_model_retrain

# Watch the training progress
docker-compose exec airflow-webserver airflow tasks logs airsense_model_retrain train_aqi_predictor

# Check MLflow for registered models
open http://localhost:5000

# Verify model is in production stage
docker-compose exec api python -c "
import mlflow
client = mlflow.tracking.MlflowClient()
versions = client.get_latest_versions('aqi-predictor-lahore', stages=['Production'])
print('Production model:', versions[0].version if versions else 'None registered')
"
```

### STEP 5: Activate Real-Time Data Feeds (Day 3)

```bash
# Test each data source manually first
docker-compose exec celery-worker celery -A tasks.app call tasks.data_fetchers.fetch_waqi_lahore
docker-compose exec celery-worker celery -A tasks.app call tasks.data_fetchers.fetch_openaq_lahore
docker-compose exec celery-worker celery -A tasks.app call tasks.data_fetchers.fetch_iqair_lahore

# Verify data is flowing into database
docker-compose exec timescaledb psql -U airsense -d airsense -c "
SELECT source, COUNT(*), MAX(timestamp) as latest 
FROM measurements 
WHERE city='lahore' AND timestamp > NOW() - INTERVAL '2 hours'
GROUP BY source;
"

# Confirm Celery Beat is scheduling tasks
docker-compose logs celery-beat | tail -50
```

### STEP 6: Test API Endpoints (Day 3-4)

```bash
# Test current AQI
curl http://localhost:8000/api/v1/aqi/current/lahore | python3 -m json.tool

# Test heatmap data
curl "http://localhost:8000/api/v1/aqi/heatmap/lahore?parameter=pm25" | python3 -m json.tool

# Test 24h forecast
curl "http://localhost:8000/api/v1/aqi/forecast/lahore?hours=24" | python3 -m json.tool

# Test health risk
curl "http://localhost:8000/api/v1/health/risk/lahore" | python3 -m json.tool

# Test WebSocket (requires wscat: npm install -g wscat)
wscat -c ws://localhost:8000/api/v1/aqi/live/lahore
```

### STEP 7: Connect Frontend to Live API (Day 4-5)

```bash
cd frontend

# Update .env.development
echo "REACT_APP_API_URL=http://localhost:8000" > .env.development
echo "REACT_APP_WS_URL=ws://localhost:8000" >> .env.development
echo "REACT_APP_MAPBOX_TOKEN=your_mapbox_token" >> .env.development

# Install any missing dependencies
npm install framer-motion mapbox-gl axios socket.io-client

# Replace all hardcoded/mock data with hooks
# See Section 7 for component implementations

# Test the full frontend → API → DB flow
npm start
```

### STEP 8: Production Deployment (Week 2)

```bash
# On your production server (Ubuntu 22.04)
# Minimum specs: 4 CPU, 8GB RAM, 100GB SSD

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Clone repo
git clone https://github.com/airsense/platform.git /opt/airsense
cd /opt/airsense

# Configure production env
cp .env.example .env.production
# Fill in all production values

# Get SSL certificate
sudo certbot certonly --standalone -d airsense.pk -d www.airsense.pk -d api.airsense.pk

# Deploy production stack
docker-compose -f docker-compose.prod.yml up -d

# Set up automated SSL renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -

# Verify all services running
docker-compose ps
curl https://api.airsense.pk/api/v1/aqi/current/lahore
```

### STEP 9: Verify Auto-Retraining is Working (Week 2)

```bash
# Insert a batch of test records to trigger threshold
docker-compose exec api python -c "
from app.db.timescale import bulk_insert_test_records
bulk_insert_test_records(count=600)  # Exceeds 500 threshold
"

# Check if Airflow DAG was triggered automatically
docker-compose exec airflow-webserver airflow dags list-runs airsense_model_retrain

# Expected: You should see a new run triggered by 'data_threshold'
# Check Grafana to see model metrics updated
open http://localhost:3001
```

---

## 12. BUDGET AND RESOURCE ESTIMATION

### Infrastructure Costs (Monthly)

| Service | Option | Cost/Month |
|---|---|---|
| Cloud Server | Hetzner CX31 (4vCPU, 8GB, 80GB) | ~$15 |
| Cloud Server | DigitalOcean 4vCPU 8GB | ~$48 |
| Cloud Server | AWS t3.xlarge | ~$120 |
| Object Storage (S3) | 50GB models + data | ~$5 |
| Domain (airsense.pk) | Annual | ~$2/mo |
| Mapbox | Free tier (50k loads/mo) | $0 |
| SSL Certificate | Let's Encrypt | $0 |
| **Total (Hetzner)** | | **~$22/mo** |
| **Total (AWS)** | | **~$130/mo** |

### API Costs (All Free Tiers Initially)

| API | Free Tier | Paid Starts |
|---|---|---|
| OpenAQ | 10,000 req/day | $0 initially |
| WAQI | Unlimited (personal token) | $0 |
| IQAir | 10,000 req/month | $0 initially |
| OpenWeatherMap | 1,000 req/day | $0 initially |
| NASA FIRMS | Unlimited | $0 |
| Sentinel-5P | Unlimited | $0 |

### Phase 1 Launch Budget
- Server (6 months, Hetzner): **~$90**
- Domain registration: **~$10**
- API keys (all free tier): **$0**
- Total to go live: **~$100**

---

## QUICK REFERENCE: KEY COMMANDS

```bash
# Start everything
docker-compose up -d

# View all logs
docker-compose logs -f

# Manually trigger data fetch
docker-compose exec celery-worker celery -A tasks.app call tasks.data_fetchers.fetch_waqi_lahore

# Manually trigger retraining
docker-compose exec airflow-webserver airflow dags trigger airsense_model_retrain

# Check database stats
docker-compose exec timescaledb psql -U airsense -d airsense -c "SELECT city, COUNT(*), MAX(timestamp) FROM measurements GROUP BY city;"

# View model registry
open http://localhost:5000  # MLflow

# View pipeline status
open http://localhost:8080  # Airflow

# View system metrics
open http://localhost:3001  # Grafana

# View API docs
open http://localhost:8000/docs  # Swagger UI
```

---

*AirSense Platform — Built to Revolutionize Environmental Intelligence in Pakistan*  
*First deployed: Lahore Phase 1 | Target: All Major Pakistani Cities*

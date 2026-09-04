# AirSense Pakistan Zero-Cost Deployment Architecture

This document details how AirSense Pakistan operates with zero paid software software licenses or recurring cloud bills.

## 1. Zero-Cost Technology Choices

| Subsystem | Commercial Solution | AirSense Zero-Cost Alternative | Savings Rationale |
| --- | --- | --- | --- |
| Database | Paid Managed DB (AWS RDS) | Local SQLite (Dev) / Self-Hosted PostgreSQL (Prod) | $0/mo vs $50-200/mo |
| Data Ingestion | Managed IoT Service (AWS IoT Core) | FastAPI Async HTTP Ingestion Endpoint | $0/mo vs $20-100/mo |
| Task Scheduler | Airflow Managed / Paid SaaS | In-Process APScheduler / Python Background Tasks | $0/mo vs $150+/mo |
| Mapping Engine | Mapbox / Google Maps API | OpenStreetMap / Leaflet / Static SVG interpolation | $0/mo vs Metered API charges |
| Weather & AQI APIs | Paid Commercial APIs | Tier 1 Free Providers (Open-Meteo Weather & AQI) | $0/mo vs $100+/mo |

## 2. Infrastructure Footprint

AirSense requires no enterprise cloud services (Rule 15: No Kubernetes, Kafka, Airflow, MLflow, Celery, paid maps, billing).

Running on a single campus server or laptop provides complete operational independence with zero monthly expense.

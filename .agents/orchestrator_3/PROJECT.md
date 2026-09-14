# Project: AirSense-v2 Production Cloud Deployment & Live HTTPS Telemetry Pipeline

## Architecture
AirSense-v2 is an industrial-grade environmental monitoring and predictive intelligence platform. The system ingests physical microclimate and particulate packets from an ESP32 hardware node via serial bridge or direct MQTT, processes readings through FastAPI backend services with asynchronous PostgreSQL / SQLite storage, executes 24/7 background meteorological telemetry generation and quality control, and serves live feeds and dashboards over secure public HTTPS.

```
+-------------------------------------------------------------+
|                     ESP32 Hardware Node                     |
|  - Physical UART (PMS7003 PM1.0/2.5/10)                     |
|  - Physical I2C (BME280 Temp/Humidity/Pressure)             |
|  - Firmware outputs structured JSON over Serial & Wi-Fi     |
+------------------------------+------------------------------+
                               |
            +------------------+------------------+
            | (USB Serial COM UART)               | (Direct Wi-Fi)
            v                                     v
+-----------------------------+       +-----------------------------+
| Python Serial Bridge Daemon |       | ESP32 Standalone MQTT Pub   |
| - Dynamic USB/COM Scanner   |       | - Dual MQTT Broker Publish  |
| - Non-blocking ThreadPool   |       +--------------+--------------+
| - Dual-Routing HTTP Forward |                      |
|   * Local API (127.0.0.1)   |                      |
|   * Live Cloud Public HTTPS |                      |
+--------------+--------------+                      |
               |                                     |
               +------------------+------------------+
                                  |
                                  v
+-------------------------------------------------------------+
|         Live Public HTTPS Ingress & FastAPI Backend         |
|  - Public HTTPS: Cloudflare Tunnel / Render Cloud PaaS      |
|  - FastAPI (apps.api.main:app)                              |
|  - Lifespan DB Engine (PostgreSQL / SQLite via SQLAlchemy)   |
|  - Production Security Middleware & Rate Limiting           |
+------------------------------+------------------------------+
                               |
        +----------------------+----------------------+
        |                                             |
        v                                             v
+-----------------------------+       +-----------------------------+
| 24/7 Background Scheduler   |       | Verified Production APIs    |
| - 60s Minute Weather Engine |       | 1. /health/liveness (200)   |
| - 10s Node Watchdog         |       | 2. /health/readiness (200)  |
| - Hourly QC Rollup          |       | 3. /ingest/reading (200)    |
| - Daily Compressed Backups  |       | 4. /sensors/diagnostic (200)|
+-----------------------------+       | 5. /telemetry-feed (200)    |
                                      +-----------------------------+
```

## Feature Inventory
| # | Feature | Description | Milestone | Status | Source |
|---|---|---|---|---|---|
| 1 | DB Sessionmaker Alias Fix | Add `async_session_maker = AsyncSessionLocal` in `apps/api/db/session.py` for scheduler | M1 | PENDING | Survey |
| 2 | 24/7 Background Scheduler Autonomy | Verify 60s weather telemetry, 10s hardware watchdog, hourly QC, and daily backups | M1 | PENDING | Survey |
| 3 | Hardware Serial Bridge Dual-Routing | Add `--cloud-url` / `AIRSENSE_CLOUD_API_URL` with non-blocking `ThreadPoolExecutor` | M2 | PENDING | Survey |
| 4 | Git & GitHub Synchronization | Initialize local git repo, stage files, commit, and link to GitHub remote for Render | M3 | PENDING | User Req / Survey |
| 5 | Public HTTPS Endpoint Provisioning | Launch backend and establish persistent secure HTTPS endpoint via Cloudflare Tunnel / Render | M3 | PENDING | User Req |
| 6 | E2E Live 5-Endpoint Verification | Verify `/health/liveness`, `/health/readiness`, `/ingest/reading`, `/sensors/diagnostic`, `/telemetry-feed` over public HTTPS | M4 | PENDING | User Req |
| 7 | Packet Forwarding Verification | Programmatically forward serial packet to public cloud URL and verify status in diagnostic | M4 | PENDING | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Backend & 24/7 Autonomous Scheduler Hardening | Resolve `apps/api/db/session.py` sessionmaker alias, test background scheduler jobs, verify SQLite/Postgres ORM lifespan | none | IN_PROGRESS |
| M2 | Hardware Serial Bridge Cloud Multi-Destination Dual-Routing | Update `scripts/airsense_serial_live_bridge.py` with `--cloud-url`, non-blocking HTTP threadpool, and tests | M1 | PLANNED |
| M3 | Live Public HTTPS Endpoint Provisioning & GitHub Sync | Setup Git repository, sync for Render blueprint, launch backend and expose live public HTTPS endpoint via Cloudflare Tunnel | M1, M2 | PLANNED |
| M4 | End-to-End Live Routing & Ingestion Verification | Run programmatic HTTPS test harness against public URL for all 5 production endpoints and bridge simulation | M3 | PLANNED |

## Interface Contracts

### 1. Ingestion Reading (`POST /api/v1/ingest/reading`)
- Header: `X-Device-Token: airsense_dev_token_khi_01` (or `Authorization: Bearer airsense_dev_token_khi_01`)
- Body: `ESP32IngestPayload` (schema_version: "1.0", device_uid: "AIRSENSE-NODE-KHI-01", station_code: "BIC-KHI-ROOF-01", campus_code: "KARACHI", pm1, pm2_5, pm10, temperature, humidity, pressure, gas_resistance_kohm, rain_flag, sensor_health, transmission_mode)
- Response: HTTP 200/201 with `{"accepted": true, "ingestion_id": "...", ...}`

### 2. Sensor Diagnostic (`GET /api/v1/ingest/sensors/diagnostic`)
- Query Params: `station_id` (optional)
- Response: HTTP 200 with `{"overall_state": "LIVE_ACTIVE"|"PARTIAL_DEGRADED"|"OFFLINE", "sensors": {...}, "heartbeat": {...}}`

### 3. Weather Telemetry Feed (`GET /api/v1/providers/weather/telemetry-feed`)
- Query Params: `limit` (default 30), `force_refresh` (bool), `latitude` (float), `longitude` (float)
- Response: HTTP 200 with `{"status": "success", "cadence_seconds": 60, "records": [...]}`

### 4. Health Probes
- `GET /api/v1/health/liveness` -> HTTP 200 `{"status": "healthy", "process": "running"}`
- `GET /api/v1/health/readiness` -> HTTP 200 `{"status": "ready", "database": {"connected": true}}`

## Code Layout
- `apps/api/main.py` — FastAPI application entry point, lifespan, routers, static mounts
- `apps/api/core/config.py` — Application settings and environment variables
- `apps/api/core/security.py` — Device and admin token authentication
- `apps/api/db/session.py` — SQLAlchemy async engine and session factory
- `apps/api/db/models.py` — Declarative ORM models
- `apps/api/routers/ingest_router.py` — Ingestion routes and sensor health diagnostics
- `apps/api/routers/provider_router.py` — Weather telemetry feed and external provider endpoints
- `services/background_scheduler.py` — 24/7 background scheduler (weather, watchdog, QC, backups)
- `scripts/airsense_serial_live_bridge.py` — Hardware serial bridge with dual-routing
- `scripts/verify_live_endpoints.py` — Live HTTPS E2E verification test harness
- `render.yaml` — Render Cloud Blueprint IaC definition
- `cloudflared.exe` — Cloudflare Tunnel binary for instant, persistent public HTTPS ingress

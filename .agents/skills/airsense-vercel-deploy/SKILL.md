---
name: airsense-vercel-deploy
description: >-
  Step-by-step automated workflow and checklist for deploying AirSense Pakistan
  FastAPI backend, serverless catch-all ingress, /tmp SQLite database, and real-time
  physical telemetry pipeline on Vercel with zero credit card requirements.
---

# AirSense Pakistan: Real-Time Vercel Serverless Deployment Skill

This skill documents and executes the 100% free, zero-credit-card deployment of the AirSense Pakistan FastAPI core backend, live SQLite telemetry storage, and hardware ingestion pipeline to Vercel Serverless Functions.

## 1. Architectural Principles & Free-Tier Guardrails
- **Zero Credit Card**: Bypasses Render/HuggingFace billing credit card walls by leveraging Vercel Hobby tier Serverless Functions.
- **Serverless ASGI Bridge**: Bridges FastAPI ASGI application to Vercel's Python runtime via `api/index.py` and `api/[...path].py`.
- **Writable Cold-Start SQLite**: Vercel provides a read-only root container except for `/tmp`. The ASGI ingress automatically configures `DATABASE_URL=sqlite+aiosqlite:////tmp/data/airsense.db` and runs table initialization and default device seeding on the very first incoming request.
- **Path Normalization**: `VercelPathNormalizer` inspects ASGI headers (`x-matched-path`, `x-invoke-path`, `raw_path`) to preserve original API routes (`/api/v1/*`) across Vercel URL rewrites.
- **Lean Serverless Bundle**: Excludes heavy archival datasets (>500MB) via `.vercelignore` while retaining required scientific dependencies (`numpy`, `pandas`, `scikit-learn`, `sqlalchemy`, `aiosqlite`).

## 2. Key Configuration Assets
- `api/index.py`: Serverless ASGI ingress handler, path normalizer, root `/api` endpoint, and cold-start database migration.
- `api/[...path].py`: Catch-all ingress ensuring all dynamic routes (`/api/v1/health/*`, `/api/v1/ingest/*`, `/api/v1/providers/*`) route directly to FastAPI.
- `api/requirements.txt`: Curated Python runtime dependencies optimized for Vercel's 250MB bundle limit.
- `vercel.json`: Rewrites mapping `/api/(.*)`, `/docs`, and `/openapi.json` to `/api`, and mapping static HTML pages to `/public/*.html`.
- `.vercelignore`: Excludes `.venv`, `data/`, heavy `.zip`/`.bin` archives, and dev scratchpads.

## 3. Deployment Procedure
Execute from the project workspace root:

```powershell
# Deploy directly to Vercel Production using the cached Vercel CLI
node "C:\Users\HP\AppData\Local\npm-cache\_npx\69f9afb961c37556\node_modules\vercel\dist\index.js" --prod --yes
```

## 4. Production Health & Telemetry Verification Checklist
Verify all key endpoints return `HTTP 200`:

1. **Root API Welcome**:
   `GET https://airsense-team.vercel.app/api`
   *Expected: HTTP 200 `{"status": "healthy", "service": "AirSense Pakistan Real-Time API Engine"}`*

2. **Liveness Probe**:
   `GET https://airsense-team.vercel.app/api/v1/health/liveness`
   *Expected: HTTP 200 `{"status": "healthy", "process": "running"}`*

3. **Readiness Probe**:
   `GET https://airsense-team.vercel.app/api/v1/health/readiness`
   *Expected: HTTP 200 `{"status": "ready", "database": {"connected": true}, "storage": {"disk_writable": true}}`*

4. **Continuous Meteorological Feed**:
   `GET https://airsense-team.vercel.app/api/v1/providers/weather/telemetry-feed`
   *Expected: HTTP 200 `{"status": "success", "cadence_seconds": 60, "records": [...]}`*

5. **Hardware Sensor Diagnostics**:
   `GET https://airsense-team.vercel.app/api/v1/ingest/sensors/diagnostic`
   *Expected: HTTP 200 with sensor connectivity breakdown (PMS7003, BME280, Rain Plate, MicroSD)*

6. **Live ESP32 Telemetry Ingestion**:
   ```bash
   curl -X POST https://airsense-team.vercel.app/api/v1/ingest/reading \
     -H "X-Device-Token: airsense_dev_token_khi_01" \
     -H "Content-Type: application/json" \
     -d '{
       "device_uid": "AIRSENSE-NODE-KHI-01",
       "station_code": "BIC-KHI-ROOF-01",
       "pm1": 10.0,
       "pm2_5": 15.0,
       "pm10": 25.0,
       "temperature": 28.0,
       "humidity": 60.0,
       "pressure": 1010.0,
       "rain_flag": false,
       "sequence_number": 1
     }'
   ```
   *Expected: HTTP 200 `{"accepted": true, "quality_processing_state": "accepted"}`*
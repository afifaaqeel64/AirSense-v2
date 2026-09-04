# AirSense Platform — Complete Deployment Guide

> **"The world is not ready for what's coming."**
> Real-time AI-powered air quality intelligence for Pakistan — starting Lahore.

---

## What's In This Package

```
airsense/
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── main.py            # FastAPI entry point
│   │   ├── api/v1/            # REST + WebSocket endpoints
│   │   ├── core/              # Config, security, validator, metrics
│   │   ├── db/                # TimescaleDB + Redis clients
│   │   ├── ml/                # Model inference + hot-reload
│   │   └── services/          # AQI service, alert service
│   ├── tasks/                 # Celery: data fetchers + ML pipeline
│   ├── tests/                 # pytest test suite
│   ├── requirements.txt
│   └── Dockerfile
├── airflow/dags/              # ML retraining DAGs (event-driven)
├── db/
│   ├── init.sql               # TimescaleDB schema + Lahore seed
│   └── multi_db.sh            # Creates mlflow + airflow databases
├── nginx/nginx.conf           # Reverse proxy + SSL + rate limiting
├── monitoring/                # Prometheus + Grafana configs
├── frontend_patches/          # Drop-in React components + hooks
│   └── src/
│       ├── services/api.js    # Complete API service layer
│       ├── hooks/useAQI.js    # useLiveAQI, useForecast, useHistorical
│       ├── utils/aqi.js       # AQI levels, formatters
│       └── components/        # Map, Gauge, ForecastChart, StationTable
├── scripts/
│   ├── setup.sh               # First-time setup
│   ├── deploy.sh              # Production deployment
│   └── seed_lahore.sh         # Trigger historical data load
├── .github/workflows/         # CI/CD pipeline
├── docker-compose.yml         # Full stack
└── .env.example               # Configuration template
```

---

## DEPLOYMENT IN 8 STEPS

### Step 1 — Server Setup (Ubuntu 22.04+)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone the repo
git clone https://github.com/your-org/airsense.git /opt/airsense
cd /opt/airsense
```

### Step 2 — Configure Environment

```bash
bash scripts/setup.sh       # Creates .env + self-signed SSL
nano .env                   # Add your API keys (see below)
```

**Required API keys (all free):**

| Key | Get it from |
|-----|-------------|
| `WAQI_TOKEN` | https://aqicn.org/data-platform/token/ |
| `OPENAQ_API_KEY` | https://api.openaq.org/register |
| `IQAIR_API_KEY` | https://www.iqair.com/dashboard/api |
| `OWM_API_KEY` | https://openweathermap.org/api |
| `NASA_FIRMS_KEY` | https://firms.modaps.eosdis.nasa.gov/api/ |
| `MAPBOX_TOKEN` | https://account.mapbox.com/ |

### Step 3 — Start All Services

```bash
docker-compose up -d

# Check all containers are healthy
docker-compose ps

# Wait for database to be ready (30-60 seconds)
docker-compose logs timescaledb | grep "database system is ready"
```

### Step 4 — Load Historical Lahore Data

```bash
# Trigger the Airflow historical data DAG
bash scripts/seed_lahore.sh

# Monitor progress at http://your-server:8080
# (Airflow UI — admin/admin by default)
# This loads 2018–present Lahore data from OpenAQ (~2-3 hours)
```

### Step 5 — Run First Model Training

```bash
# Wait for historical load to complete, then trigger training
curl -X POST "http://localhost:8080/api/v1/dags/airsense_model_retrain/dagRuns" \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d '{"conf": {"city": "lahore", "reason": "initial_training"}}'

# Watch training in Airflow UI: http://your-server:8080
# Check MLflow for registered models: http://your-server:5000
```

### Step 6 — Verify Everything Works

```bash
# API health
curl http://localhost:8000/health

# Current AQI (should return live data)
curl http://localhost:8000/api/v1/aqi/current/lahore | python3 -m json.tool

# Forecast
curl "http://localhost:8000/api/v1/aqi/forecast/lahore?hours=24" | python3 -m json.tool

# Check data sources are flowing
curl http://localhost:8000/api/v1/admin/pipeline-health \
  -H "Authorization: Bearer YOUR_TOKEN"

# Swagger docs
open http://localhost:8000/docs

# Pipeline monitoring
open http://localhost:5555   # Flower (Celery)
open http://localhost:5000   # MLflow
open http://localhost:8080   # Airflow
open http://localhost:3001   # Grafana
```

### Step 7 — SSL + Domain (Production)

```bash
# Install Certbot
sudo apt install certbot -y

# Get Let's Encrypt certificate
sudo certbot certonly --standalone \
  -d airsense.pk -d www.airsense.pk -d api.airsense.pk \
  --email you@airsense.pk --agree-tos

# Copy certs
sudo cp /etc/letsencrypt/live/airsense.pk/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/airsense.pk/privkey.pem nginx/ssl/

# Restart nginx
docker-compose restart nginx

# Auto-renewal cron
echo "0 12 * * * root certbot renew --quiet && docker-compose -f /opt/airsense/docker-compose.yml restart nginx" \
  | sudo tee /etc/cron.d/certbot-renewal
```

### Step 8 — Connect Frontend

```bash
# Copy patches into your existing frontend
cp -r frontend_patches/src/services/* ../your-frontend/src/services/
cp -r frontend_patches/src/hooks/*    ../your-frontend/src/hooks/
cp -r frontend_patches/src/utils/*    ../your-frontend/src/utils/
cp -r frontend_patches/src/components/* ../your-frontend/src/components/

# Set frontend environment
echo "REACT_APP_API_URL=https://api.airsense.pk" >> ../your-frontend/.env.production
echo "REACT_APP_WS_URL=wss://api.airsense.pk"   >> ../your-frontend/.env.production
echo "REACT_APP_MAPBOX_TOKEN=pk.eyJ1..."         >> ../your-frontend/.env.production

# Build and deploy frontend
cd ../your-frontend && npm run build
docker-compose restart frontend
```

---

## HOW THE AUTO-RETRAINING WORKS

```
Every 30 minutes:
  Celery Beat → fetch_waqi_lahore()
              → fetch_openaq_lahore()
              → fetch_iqair_lahore()
              → fetch_owm_lahore()
              → insert into TimescaleDB
              → check_data_threshold()

  If new_records >= 500  ──────────────────────┐
  OR 24h since last train ─────────────────────┤
                                               ▼
                              Airflow DAG: airsense_model_retrain
                              ├── extract_features (90 days of data)
                              ├── validate_data
                              ├── train_aqi (XGBoost)      ─┐
                              ├── train_forecast (GB)       ├── parallel
                              ├── train_health (RF)         ├── training
                              ├── train_anomaly (IsoForest)─┘
                              ├── evaluate (compare vs prod, need ≥1% RMSE improvement)
                              ├── promote to Production (MLflow registry)
                              └── hot-reload in API (zero downtime, every 5 min)
```

---

## API ENDPOINTS REFERENCE

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/aqi/current/{city}` | Real-time AQI + all stations |
| GET | `/api/v1/aqi/heatmap/{city}` | Interpolated spatial grid (GeoJSON) |
| GET | `/api/v1/aqi/forecast/{city}?hours=24` | ML forecast 1–72h |
| GET | `/api/v1/aqi/historical/{city}` | Historical time-series |
| GET | `/api/v1/aqi/health/{city}` | Health risk + recommendations |
| GET | `/api/v1/aqi/compare` | Multi-city comparison |
| WS  | `/api/v1/aqi/live/{city}` | WebSocket live stream |
| GET | `/api/v1/stations/{city}` | Station list + metadata |
| POST| `/api/v1/auth/register` | User registration |
| POST| `/api/v1/auth/login` | Login → JWT token |
| GET | `/api/v1/admin/pipeline-health` | Data source health |
| GET | `/api/v1/admin/training-log` | ML training history |
| POST| `/api/v1/admin/trigger-retrain/{city}` | Manual retrain trigger |
| GET | `/health` | System health check |
| GET | `/metrics` | Prometheus metrics |
| GET | `/docs` | Swagger UI |

---

## MONITORING URLS (LOCAL)

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | — |
| API + Swagger | http://localhost:8000/docs | — |
| Airflow (ML Orchestration) | http://localhost:8080 | admin/admin |
| MLflow (Model Registry) | http://localhost:5000 | — |
| Flower (Celery Tasks) | http://localhost:5555 | admin/admin |
| Grafana (Dashboards) | http://localhost:3001 | admin/airsense123 |
| Prometheus | http://localhost:9090 | — |

---

## FRONTEND INTEGRATION EXAMPLE

```jsx
// In your dashboard component
import { useLiveAQI, useForecast } from './hooks/useAQI';
import { AQIGauge, ForecastChart, StationTable } from './components/AirQualityComponents';
import { AirQualityMap } from './components/AirQualityComponents';

function Dashboard() {
  const { data, loading, connected } = useLiveAQI('lahore');
  const { forecast } = useForecast('lahore', 24);

  if (loading) return <div>Loading live data...</div>;

  return (
    <div>
      {/* Connection status indicator */}
      <div style={{ color: connected ? '#00E400' : '#FF6B35' }}>
        {connected ? '● LIVE' : '○ Polling'}
      </div>

      {/* Main AQI gauge */}
      <AQIGauge
        aqi={data.aqi}
        pm25={data.pm25}
        location="Lahore"
        lastUpdated={data.timestamp}
      />

      {/* Heatmap */}
      <div style={{ height: 400 }}>
        <AirQualityMap parameter="aqi" />
      </div>

      {/* 24h Forecast */}
      <ForecastChart forecast={forecast} city="lahore" />

      {/* Station table */}
      <StationTable stations={data.stations || []} />
    </div>
  );
}
```

---

## COST SUMMARY

| Item | Monthly Cost |
|------|-------------|
| Hetzner CX31 (4 vCPU, 8GB, 80GB SSD) | ~€15 (~$16) |
| Domain (airsense.pk) | ~$1 |
| All API keys (free tiers) | $0 |
| SSL (Let's Encrypt) | $0 |
| **Total Phase 1** | **~$17/month** |

Free tier limits (sufficient for Phase 1):
- OpenAQ: 10,000 req/day ✓
- WAQI: Unlimited (personal token) ✓
- IQAir: 10,000 req/month ✓
- OpenWeatherMap: 1,000 req/day ✓
- NASA FIRMS: Unlimited ✓

---

## NEXT CITIES: 4–8 WEEKS TO EXPAND

1. Update `LAHORE_BBOX` in `config.py` to new city bounding box
2. Add city station IDs to `WAQI_LAHORE_STATIONS` in `data_fetchers.py`
3. Run historical load DAG with `{"city": "karachi"}`
4. Trigger retraining with new city data
5. Done — the architecture is fully city-agnostic

**Expansion targets:** Karachi → Islamabad → Faisalabad → Multan
**International:** Delhi → Dhaka → Jakarta → Lagos

---

*AirSense — Built in Pakistan. Built for the world.*
*"Others provide information. We enable decisions."*

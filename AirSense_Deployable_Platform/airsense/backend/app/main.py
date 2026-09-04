"""AirSense FastAPI Application Entry Point."""
import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.metrics import (
    REQUEST_COUNT, REQUEST_LATENCY, metrics_endpoint
)
from app.api.v1 import aqi, stations, admin, auth
import structlog

log = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background services on startup."""
    log.info("airsense_starting", version=settings.APP_VERSION, env=settings.ENVIRONMENT)
    
    # Start hot-reload thread for ML models
    from app.ml.predictor import start_hot_reload
    start_hot_reload()
    log.info("model_hot_reload_started")
    
    yield
    log.info("airsense_shutting_down")

app = FastAPI(
    title="AirSense API",
    description="""
## Real-time Air Quality Intelligence Platform

AirSense provides hyper-local, AI-powered air quality data for Pakistani cities.

### Features
- **Real-time AQI** from 15+ monitoring stations across Lahore
- **Spatial heatmaps** — interpolated pollution maps at any resolution
- **24–72 hour forecasts** powered by LSTM + XGBoost models
- **Health risk assessments** with actionable recommendations
- **WebSocket streams** for live dashboard updates
- **Historical data** from 2018 onwards

### Phase 1: Lahore | Coming Soon: Karachi, Islamabad, Faisalabad
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── MIDDLEWARE ────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    endpoint = request.url.path
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(endpoint).observe(duration)
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    response.headers["X-AirSense-Version"] = settings.APP_VERSION
    return response

@app.middleware("http")
async def api_key_rate_limit(request: Request, call_next):
    """Rate limiting: 1000 req/day for free, unlimited for authenticated."""
    api_key = request.headers.get("X-API-Key")
    if api_key and request.url.path.startswith("/api/"):
        from app.db.redis_client import increment_counter
        count = await increment_counter(f"ratelimit:{api_key}")
        if count > 10000:
            return JSONResponse({"error": "Rate limit exceeded", "limit": "10,000/day"}, status_code=429)
    return await call_next(request)

# ── ROUTES ────────────────────────────────────────────────────
prefix = "/api/v1"
app.include_router(aqi.router,      prefix=prefix)
app.include_router(stations.router, prefix=prefix)
app.include_router(admin.router,    prefix=prefix)
app.include_router(auth.router,     prefix=prefix)

@app.get("/metrics")
def prometheus_metrics():
    return metrics_endpoint()

@app.get("/health")
async def health_check():
    from app.db.timescale import get_conn
    db_ok = False
    try:
        conn = await get_conn()
        await conn.fetchval("SELECT 1")
        await conn.close()
        db_ok = True
    except Exception:
        pass
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }

@app.get("/")
async def root():
    return {
        "name": "AirSense API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "cities": ["lahore"],
        "endpoints": {
            "current_aqi": "/api/v1/aqi/current/{city}",
            "heatmap":     "/api/v1/aqi/heatmap/{city}",
            "forecast":    "/api/v1/aqi/forecast/{city}",
            "historical":  "/api/v1/aqi/historical/{city}",
            "health_risk": "/api/v1/aqi/health/{city}",
            "live_stream": "ws://api.airsense.pk/api/v1/aqi/live/{city}",
        }
    }

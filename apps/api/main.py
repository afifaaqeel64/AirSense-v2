"""AirSense Pakistan FastAPI Foundation & Data Platform Application."""

import os
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from apps.api.core.config import settings
from apps.api.db.session import engine, Base, get_db_session
from apps.api.db.models import Campus, Station, Device

from apps.api.routers.admin_router import router as admin_router
from apps.api.routers.ingest_router import router as ingest_router
from apps.api.routers.import_router import router as import_router
from apps.api.routers.quality_router import router as quality_router
from apps.api.routers.provider_router import router as provider_router
from apps.api.routers.export_router import router as export_router

try:
    from apps.api.routers.model_router import router as model_router
    from apps.api.routers.forecast_router import router as forecast_router
    from apps.api.routers.comparison_router import router as comparison_router
    from apps.api.routers.evaluation_router import router as evaluation_router
    from apps.api.routers.inference_router import router as inference_router
    HAS_ML_MODULES = True
except ImportError as _ml_err:
    HAS_ML_MODULES = False
    print(f"[AirSense Info] Running in lightweight serverless mode without ML training modules: {_ml_err}")

from apps.api.routers.hardware_router import router as hardware_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Database initialization and campus bootstrap startup tasks."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial campus records if they do not exist
    async with engine.connect() as conn:
        async with AsyncSession(conn) as session:
            # Islamabad
            result_isb = await session.execute(select(Campus).where(Campus.code == settings.ISLAMABAD_CAMPUS_CODE))
            isb = result_isb.scalar_one_or_none()
            if not isb:
                isb_status = "active" if settings.is_islamabad_configured() else "configuration_required"
                isb = Campus(
                    code=settings.ISLAMABAD_CAMPUS_CODE,
                    name=settings.ISLAMABAD_CAMPUS_NAME,
                    city="Islamabad",
                    contact_name=settings.ISLAMABAD_CONTACT_NAME,
                    latitude=settings.ISLAMABAD_LATITUDE,
                    longitude=settings.ISLAMABAD_LONGITUDE,
                    status=isb_status
                )
                session.add(isb)

            # Karachi
            result_khi = await session.execute(select(Campus).where(Campus.code == settings.KARACHI_CAMPUS_CODE))
            khi = result_khi.scalar_one_or_none()
            if not khi:
                khi_status = "active" if settings.is_karachi_configured() else "configuration_required"
                khi = Campus(
                    code=settings.KARACHI_CAMPUS_CODE,
                    name=settings.KARACHI_CAMPUS_NAME,
                    city="Karachi",
                    contact_name=settings.KARACHI_CONTACT_NAME,
                    latitude=settings.KARACHI_LATITUDE,
                    longitude=settings.KARACHI_LONGITUDE,
                    status=khi_status
                )
                session.add(khi)
                await session.flush()

            # Default Station for Karachi
            result_st = await session.execute(select(Station).where(Station.station_code == "BIC-KHI-ROOF-01"))
            st_khi = result_st.scalar_one_or_none()
            if not st_khi and khi:
                st_khi = Station(
                    campus_id=khi.id,
                    station_code="BIC-KHI-ROOF-01",
                    station_name="Karachi BIC Rooftop Station",
                    installation_location="BIC Rooftop",
                    latitude=settings.KARACHI_LATITUDE,
                    longitude=settings.KARACHI_LONGITUDE,
                    status="active"
                )
                session.add(st_khi)
                await session.flush()

            # Default Registered ESP32 Device
            from apps.api.core.security import hash_token
            dev_token = "airsense_dev_token_khi_01"
            dev_hash = hash_token(dev_token)
            result_dev = await session.execute(select(Device).where(Device.device_uid == "AIRSENSE-NODE-KHI-01"))
            dev = result_dev.scalar_one_or_none()
            if not dev and st_khi:
                dev = Device(
                    station_id=st_khi.id,
                    device_uid="AIRSENSE-NODE-KHI-01",
                    token_hash=dev_hash,
                    firmware_version="v3.5.0-PROD",
                    status="active"
                )
                session.add(dev)

            await session.commit()

    # Start 24/7 autonomous background engine
    if getattr(settings, "BACKGROUND_SCHEDULER_ENABLED", True):
        from services.background_scheduler import BackgroundScheduler
        await BackgroundScheduler.get_instance().start()

    yield

    # Clean shutdown of background tasks
    if getattr(settings, "BACKGROUND_SCHEDULER_ENABLED", True):
        from services.background_scheduler import BackgroundScheduler
        await BackgroundScheduler.get_instance().stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AirSense Pakistan Campus Air Quality Intelligence and PM2.5 Forecasting Platform",
    lifespan=lifespan
)

# Production Security Headers & Rate Limiting Middleware
from services.security_middleware import ProductionSecurityMiddleware
app.add_middleware(ProductionSecurityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Phase 4 & Phase 5 Routers
app.include_router(admin_router)
app.include_router(ingest_router)
app.include_router(import_router)
app.include_router(quality_router)
app.include_router(provider_router)
app.include_router(export_router)

if HAS_ML_MODULES:
    app.include_router(model_router)
    app.include_router(forecast_router)
    app.include_router(comparison_router)
    app.include_router(evaluation_router)
    app.include_router(inference_router)

app.include_router(hardware_router)

# Operational Interface Static Serving
web_dir = Path(__file__).resolve().parent.parent / "web"
if not web_dir.exists():
    web_dir = Path(__file__).resolve().parent.parent.parent / "public"

enterprise_dir = Path(__file__).resolve().parent.parent / "web_enterprise"
if not enterprise_dir.exists():
    enterprise_dir = Path(__file__).resolve().parent.parent.parent / "public"

if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/ops", include_in_schema=False)
    async def serve_ops_interface():
        return FileResponse(web_dir / "index.html")

    @app.get("/hardware", include_in_schema=False)
    async def serve_hardware_dashboard():
        return FileResponse(web_dir / "hardware_dashboard.html")

    @app.get("/opensource", include_in_schema=False)
    async def serve_opensource_dashboard():
        return FileResponse(web_dir / "opensource_dashboard.html")

    @app.get("/diagnostics", include_in_schema=False)
    @app.get("/sensor-health-dashboard", include_in_schema=False)
    async def serve_diagnostics_dashboard():
        return FileResponse(web_dir / "diagnostics_dashboard.html")

    @app.get("/command", include_in_schema=False)
    @app.get("/command_center", include_in_schema=False)
    @app.get("/command-center", include_in_schema=False)
    async def serve_command_center():
        return FileResponse(web_dir / "command_center.html")

    @app.get("/paho-mqtt.js", include_in_schema=False)
    async def serve_paho_mqtt_root():
        paho_file = web_dir / "paho-mqtt.js"
        if paho_file.exists():
            return FileResponse(paho_file, media_type="application/javascript")
        return FileResponse(web_dir / "index.html")

if enterprise_dir.exists():
    @app.get("/enterprise", include_in_schema=False)
    async def serve_enterprise_interface():
        return FileResponse(enterprise_dir / "index.html")

# Assets & Official Branding Static Serving
assets_dir = Path(__file__).resolve().parent.parent.parent / "assets"
assets_logo_dir = assets_dir / "logo-files"
public_dir = Path(__file__).resolve().parent.parent.parent / "public"

if assets_logo_dir.exists():
    app.mount("/assets/logo-files", StaticFiles(directory=str(assets_logo_dir)), name="assets_logo_files")
elif (public_dir / "assets" / "logo-files").exists():
    app.mount("/assets/logo-files", StaticFiles(directory=str(public_dir / "assets" / "logo-files")), name="assets_logo_files")
elif (web_dir / "assets" / "logo-files").exists():
    app.mount("/assets/logo-files", StaticFiles(directory=str(web_dir / "assets" / "logo-files")), name="assets_logo_files")

if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

FAVICON_ROUTES = {
    "/favicon.ico": ("favicon.ico", "image/x-icon"),
    "/favicon-16x16.png": ("favicon-16x16.png", "image/png"),
    "/favicon-32x32.png": ("favicon-32x32.png", "image/png"),
    "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
    "/android-chrome-192x192.png": ("android-chrome-192x192.png", "image/png"),
    "/android-chrome-512x512.png": ("android-chrome-512x512.png", "image/png"),
    "/site.webmanifest": ("site.webmanifest", "application/manifest+json"),
}

for route_path, (file_name, media_type) in FAVICON_ROUTES.items():
    def _create_static_responder(target_name=file_name, mime_type=media_type):
        async def _serve_branding_file():
            candidates = [
                assets_logo_dir / target_name,
                public_dir / target_name,
                web_dir / target_name,
            ]
            for candidate in candidates:
                if candidate.exists():
                    return FileResponse(candidate, media_type=mime_type)
            raise HTTPException(status_code=404, detail=f"Branding asset {target_name} not found")
        return _serve_branding_file

    app.get(route_path, include_in_schema=False)(_create_static_responder(file_name, media_type))



class CopilotChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None


@app.post("/api/v1/copilot/chat")
async def copilot_chat_endpoint(req: CopilotChatRequest):
    """Local environmental intelligence copilot answering queries based on live telemetry."""
    msg = req.message.lower().strip()
    ctx = req.context or {}
    pm25 = ctx.get("pm2_5", 12.0)
    temp = ctx.get("temperature", 29.5)
    hum = ctx.get("humidity", 65.0)
    rain = ctx.get("rain", False)

    # Determine AQI category
    if pm25 <= 12.0:
        aqi_cat = "Good (US-EPA 0-50)"
        health_advice = "Air quality is satisfactory and poses little or no risk. Ideal for outdoor sports and campus activities."
    elif pm25 <= 35.4:
        aqi_cat = "Moderate (US-EPA 51-100)"
        health_advice = "Air quality is acceptable. Sensitive individuals with respiratory conditions should monitor prolonged heavy exertion."
    elif pm25 <= 55.4:
        aqi_cat = "Unhealthy for Sensitive Groups (US-EPA 101-150)"
        health_advice = "Members of sensitive groups may experience health effects. General public is less likely to be affected."
    else:
        aqi_cat = "Unhealthy (US-EPA 151+)"
        health_advice = "Everyone may begin to experience health effects. Keep outdoor physical activities to a minimum."

    if any(w in msg for w in ["sport", "exercise", "run", "outdoor", "play", "activity"]):
        if pm25 <= 25.0 and not rain:
            reply = f"Outdoor conditions are favorable. Current PM2.5 is {pm25:.1f} µg/m³ ({aqi_cat}) with temperature at {temp:.1f}°C and humidity at {hum:.0f}%. Outdoor sports and campus walks are safe."
        elif rain:
            reply = f"Precipitation is currently detected on campus (Rain Plate Active). Ground surfaces are wet. While air is clean (PM2.5: {pm25:.1f} µg/m³), outdoor sports are not recommended due to slippery surfaces."
        else:
            reply = f"Caution advised for vigorous outdoor sports. Ambient PM2.5 is currently {pm25:.1f} µg/m³ ({aqi_cat}). Sensitive students should limit strenuous exertion."
    elif any(w in msg for w in ["rain", "wet", "precipitation", "rainy"]):
        rain_text = "actively raining / wet surface detected" if rain else "dry (no precipitation)"
        reply = f"Campus precipitation status: {rain_text}. Current temperature is {temp:.1f}°C, relative humidity is {hum:.0f}%, and barometric pressure is {ctx.get('pressure', 1012.0):.1f} hPa."
    elif any(w in msg for w in ["pm", "air", "quality", "pollution", "smog", "dust", "breathe"]):
        reply = f"Current campus air quality is {aqi_cat}. Live PM2.5 is {pm25:.1f} µg/m³, PM1.0 is {ctx.get('pm1', 9.0):.1f} µg/m³, and PM10 is {ctx.get('pm10', 14.0):.1f} µg/m³. {health_advice}"
    elif any(w in msg for w in ["temp", "heat", "hot", "cold", "weather", "humid"]):
        reply = f"Live campus atmospheric conditions: Temperature {temp:.1f}°C, Relative Humidity {hum:.0f}%, Barometric Pressure {ctx.get('pressure', 1012.0):.1f} hPa. Station BIC-KHI-ROOF-01 is operating normally."
    else:
        reply = f"AirSense Copilot telemetry summary: Station BIC-KHI-ROOF-01 reports PM2.5 at {pm25:.1f} µg/m³ ({aqi_cat}), Temperature at {temp:.1f}°C, Humidity at {hum:.0f}%, and Rain condition: {'WET' if rain else 'DRY'}. {health_advice}"

    return {"reply": reply, "status": "success", "station": "BIC-KHI-ROOF-01"}


@app.get("/api/v1/health")
@app.get("/api/v1/health/liveness")
async def health_check():
    """Reports application process health and basic liveness status."""
    return {
        "status": "healthy",
        "process": "running",
        "environment": settings.AIR_SENSE_ENV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "display_timezone": settings.AIR_SENSE_TIMEZONE
    }


@app.get("/api/v1/ready")
@app.get("/api/v1/health/readiness")
async def readiness_check(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Deep readiness probe verifying database connectivity, disk health, and background worker status."""
    db_ok = False
    error_detail = None
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_ok = False
        error_detail = str(e)

    db_type = "sqlite" if "sqlite" in settings.DATABASE_URL else "postgresql"

    # Check background scheduler status
    from services.background_scheduler import BackgroundScheduler
    scheduler_status = BackgroundScheduler.get_status()

    # Check disk writable
    disk_writable = False
    try:
        write_dir = Path("/tmp/data/backups") if (os.environ.get("VERCEL") or not os.access(".", os.W_OK)) else Path("./data/backups")
        test_file = write_dir / ".healthcheck_write_test"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("ok", encoding="utf-8")
        if test_file.exists():
            test_file.unlink()
            disk_writable = True
    except Exception:
        disk_writable = False

    is_healthy = db_ok and disk_writable

    is_ready_endpoint = request.url.path.rstrip("/").endswith("/ready")
    if is_ready_endpoint:
        db_field = "connected" if db_ok else "disconnected"
    else:
        db_field = {
            "connected": db_ok,
            "type": db_type,
            "error": error_detail
        }

    payload = {
        "status": "ready" if is_healthy else "degraded",
        "database": db_field,
        "storage": {
            "disk_writable": disk_writable
        },
        "background_scheduler": scheduler_status,
        "pilots": {
            "islamabad": {
                "name": settings.ISLAMABAD_CAMPUS_NAME,
                "code": settings.ISLAMABAD_CAMPUS_CODE,
                "contact": settings.ISLAMABAD_CONTACT_NAME,
                "configured": settings.is_islamabad_configured()
            },
            "karachi": {
                "name": settings.KARACHI_CAMPUS_NAME,
                "code": settings.KARACHI_CAMPUS_CODE,
                "contact": settings.KARACHI_CONTACT_NAME,
                "configured": settings.is_karachi_configured()
            }
        }
    }

    if not is_healthy:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)

    return payload


@app.get("/api/v1/health/metrics")
@app.get("/metrics")
async def system_metrics(db: AsyncSession = Depends(get_db_session)):
    """Exposes production operational diagnostics and system performance metrics."""
    from services.background_scheduler import BackgroundScheduler
    scheduler_status = BackgroundScheduler.get_status()

    # Query counts safely
    from apps.api.db.models import RawReading, Station
    from sqlalchemy import func

    readings_count = 0
    stations_count = 0
    try:
        r_res = await db.execute(select(func.count(RawReading.id)))
        readings_count = r_res.scalar() or 0
        s_res = await db.execute(select(func.count(Station.id)))
        stations_count = s_res.scalar() or 0
    except Exception:
        pass

    # Database file size if SQLite
    db_file_size_mb = 0.0
    db_path = Path("./data/airsense.db")
    if db_path.exists():
        db_file_size_mb = round(db_path.stat().st_size / (1024 * 1024), 2)

    return {
        "environment": settings.AIR_SENSE_ENV,
        "app_version": settings.APP_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "database": {
            "type": "sqlite" if "sqlite" in settings.DATABASE_URL else "postgresql",
            "size_mb": db_file_size_mb,
            "total_raw_readings": readings_count,
            "total_stations": stations_count
        },
        "background_workers": scheduler_status
    }


@app.get("/api/v1/version")
async def version_info():
    """Reports platform version and pilot deployment metadata."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "stage": "Campus Pilot Phase 1",
        "pilots": ["Islamabad", "Karachi"],
        "contacts": {
            "Islamabad": settings.ISLAMABAD_CONTACT_NAME,
            "Karachi": settings.KARACHI_CONTACT_NAME
        }
    }

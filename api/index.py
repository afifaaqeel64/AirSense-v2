"""AirSense Pakistan - Vercel Serverless Function Ingress.

Exports the production FastAPI ASGI application to Vercel's Python runtime
with automated writable /tmp SQLite initialization, security middleware,
and live real-time ingestion routing.
"""

import os
import sys
import shutil
from pathlib import Path

# Add workspace root to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Production Cloud Database Configuration (Supabase PostgreSQL)
SUPABASE_CLOUD_URL = "postgresql+asyncpg://postgres.vppczkvawiaptiygrqhx:7EZgyMcqYi%269qUE@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres"

# When executing in Vercel Serverless, guarantee connection to persistent Supabase cloud database.
# Ephemeral /tmp SQLite resets on every serverless hibernation, destroying background telemetry history.
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = SUPABASE_CLOUD_URL
elif "sqlite" in os.environ.get("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = SUPABASE_CLOUD_URL

os.environ["AIR_SENSE_ENV"] = "production"

# Import core FastAPI application
from apps.api.main import app as fastapi_app


# Register Root /api Welcome & Diagnostics endpoints
@fastapi_app.get("/api", include_in_schema=False)
@fastapi_app.get("/api/", include_in_schema=False)
@fastapi_app.get("/api/index.py", include_in_schema=False)
async def api_root_index():
    return {
        "status": "healthy",
        "service": "AirSense Pakistan Real-Time API Engine",
        "version": "v3.5.0-PROD",
        "docs": "/docs",
        "database": "postgresql_supabase_active" if ("postgresql" in (os.environ.get("DATABASE_URL") or "")) else "sqlite_tmp_active",
        "endpoints": {
            "liveness": "/api/v1/health/liveness",
            "readiness": "/api/v1/health/readiness",
            "telemetry_feed": "/api/v1/providers/weather/telemetry-feed",
            "ingest_reading": "/api/v1/ingest/reading",
            "sensor_diagnostics": "/api/v1/ingest/sensors/diagnostic",
            "latest_readings": "/api/v1/ingest/latest",
            "v2_live_decisions": "/api/v2/decisions/live",
            "v2_sectors": "/api/v2/sectors",
            "v2_biomass_radar": "/api/v2/decisions/radar/biomass-hotspots",
            "v2_10day_horizon": "/api/v2/decisions/10-day-horizon"
        }
    }


class VercelPathNormalizer:
    """ASGI middleware normalizing request path across Vercel URL rewrites and cold-start DB setup."""

    def __init__(self, app):
        self.app = app
        self._db_ready = False

    async def _ensure_db(self):
        if self._db_ready:
            return
        try:
            from apps.api.db.session import engine, Base
            from apps.api.db.models import Campus, Station, Device
            from apps.api.core.config import settings
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy import select
            from apps.api.core.security import hash_token

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async with engine.connect() as conn:
                async with AsyncSession(conn) as session:
                    # Karachi Campus
                    res_khi = await session.execute(select(Campus).where(Campus.code == settings.KARACHI_CAMPUS_CODE))
                    khi = res_khi.scalar_one_or_none()
                    if not khi:
                        khi = Campus(
                            code=settings.KARACHI_CAMPUS_CODE,
                            name=settings.KARACHI_CAMPUS_NAME,
                            city="Karachi",
                            contact_name=settings.KARACHI_CONTACT_NAME,
                            latitude=settings.KARACHI_LATITUDE,
                            longitude=settings.KARACHI_LONGITUDE,
                            status="active"
                        )
                        session.add(khi)
                        await session.flush()

                    # Karachi Station
                    res_st = await session.execute(select(Station).where(Station.station_code == "BIC-KHI-ROOF-01"))
                    st_khi = res_st.scalar_one_or_none()
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

                    # Registered ESP32 Device
                    dev_token = "airsense_dev_token_khi_01"
                    dev_hash = hash_token(dev_token)
                    res_dev = await session.execute(select(Device).where(Device.device_uid == "AIRSENSE-NODE-KHI-01"))
                    dev = res_dev.scalar_one_or_none()
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
        except Exception as e:
            print(f"[Vercel DB Init Error]: {e}", flush=True)
        finally:
            self._db_ready = True

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            await self._ensure_db()

            path = scope.get("path", "")
            raw_path = scope.get("raw_path", b"").decode("utf-8", "replace")

            # Check for headers indicating rewritten destination
            headers_dict = dict(scope.get("headers", []))
            matched_path = headers_dict.get(b"x-matched-path", b"").decode("utf-8", "replace")
            invoke_path = headers_dict.get(b"x-invoke-path", b"").decode("utf-8", "replace")

            # Determine original client path
            orig_path = path
            for candidate in (matched_path, invoke_path, raw_path):
                if candidate and (candidate.startswith("/api/") or candidate.startswith("/v1/") or candidate in ("/docs", "/openapi.json")):
                    orig_path = candidate
                    break

            if orig_path.startswith("/api/index.py/"):
                orig_path = orig_path.replace("/api/index.py/", "/api/")
            elif orig_path.startswith("/api/index/"):
                orig_path = orig_path.replace("/api/index/", "/api/")
            elif orig_path.startswith("/v1/"):
                orig_path = f"/api{orig_path}"
            elif orig_path in ("/health", "/health/liveness", "/health/readiness", "/ready"):
                orig_path = f"/api/v1{orig_path.replace('/health', '') or '/health/liveness'}"

            scope["path"] = orig_path

        await self.app(scope, receive, send)


app = VercelPathNormalizer(fastapi_app)

__all__ = ["app"]

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

# Production Cloud Database Configuration (Supabase PostgreSQL via Port 6543 Transaction Pooler)
SUPABASE_CLOUD_URL = "postgresql+asyncpg://postgres.vppczkvawiaptiygrqhx:7EZgyMcqYi%269qUE@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres"

# When executing in Vercel Serverless, guarantee connection to persistent Supabase cloud database.
# Ephemeral /tmp SQLite resets on every serverless hibernation, destroying background telemetry history.
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = SUPABASE_CLOUD_URL
elif "sqlite" in os.environ.get("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = SUPABASE_CLOUD_URL

os.environ["AIR_SENSE_ENV"] = "production"

import traceback

# Safe import of core FastAPI application with diagnostic fallback
import_error = None
try:
    from apps.api.main import app as fastapi_app
except Exception as e:
    import_error = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    fastapi_app = FastAPI()

    @fastapi_app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def fallback_route(path_name: str):
        return JSONResponse(
            status_code=200,
            content={"status": "app_import_error", "error": str(e), "traceback": import_error}
        )

if import_error is None:
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
        self._db_ready = True
        # If using SQLite fallback, ensure local tables exist
        if "sqlite" in (os.environ.get("DATABASE_URL") or ""):
            try:
                from apps.api.db.session import engine, Base
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            except Exception as e:
                print(f"[Vercel SQLite Init Error]: {e}", flush=True)

    async def __call__(self, scope, receive, send):
        try:
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
        except Exception as e:
            from fastapi.responses import JSONResponse
            tb = traceback.format_exc()
            err_resp = JSONResponse(
                status_code=200,
                content={"status": "asgi_invocation_error", "error": str(e), "traceback": tb}
            )
            await err_resp(scope, receive, send)


app = VercelPathNormalizer(fastapi_app)

__all__ = ["app"]


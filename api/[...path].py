"""AirSense Pakistan - Vercel Serverless Catch-All Ingress for /api/*.

Ensures all dynamic API sub-routes (/api/v1/health/*, /api/v1/ingest/*,
/api/v1/providers/*, etc.) route directly to the core FastAPI ASGI engine.
"""

from api.index import app

__all__ = ["app"]

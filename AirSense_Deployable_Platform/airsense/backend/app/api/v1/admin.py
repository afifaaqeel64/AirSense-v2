"""Admin endpoints — pipeline health, training status, system metrics."""
from fastapi import APIRouter, Depends
from app.core.security import require_auth
from app.db.timescale import get_pipeline_health
import asyncpg
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])
DSN = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

@router.get("/pipeline-health")
async def pipeline_health(user=Depends(require_auth)):
    return {"health": await get_pipeline_health()}

@router.get("/training-log")
async def training_log(limit: int = 20, user=Depends(require_auth)):
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(
            "SELECT * FROM ml_training_log ORDER BY started_at DESC LIMIT $1", limit
        )
        return {"log": [dict(r) for r in rows]}
    finally:
        await conn.close()

@router.post("/trigger-retrain/{city}")
async def trigger_retrain(city: str, user=Depends(require_auth)):
    from app.tasks.data_fetchers import trigger_retraining_task
    trigger_retraining_task.delay(city=city, reason="manual")
    return {"status": "triggered", "city": city}

@router.get("/stats")
async def system_stats(user=Depends(require_auth)):
    conn = await asyncpg.connect(DSN)
    try:
        total = await conn.fetchval("SELECT COUNT(*) FROM measurements")
        cities = await conn.fetch("SELECT city, COUNT(*) as count FROM measurements GROUP BY city")
        return {
            "total_measurements": total,
            "by_city": [dict(r) for r in cities],
        }
    finally:
        await conn.close()

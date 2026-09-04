"""AirSense Pakistan External Provider Benchmarking Router."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.security import verify_admin_token
from apps.api.db.session import get_db_session
from apps.api.db.models import ExternalComparison
from services.forecasting.benchmarking import ExternalBenchmarkingEngine

router = APIRouter(prefix="/api/v1/comparisons", tags=["External Benchmarking"])


@router.get("/summary")
async def get_benchmark_summary(campus_id: str, db: AsyncSession = Depends(get_db_session)):
    return await ExternalBenchmarkingEngine.get_summary_statistics(db, campus_id)


@router.get("/latest")
@router.get("/history")
async def get_benchmark_history(
    campus_id: Optional[str] = None,
    station_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(ExternalComparison).order_by(ExternalComparison.timestamp_bucket.desc()).limit(limit)
    if campus_id:
        stmt = stmt.where(ExternalComparison.campus_id == campus_id)
    if station_id:
        stmt = stmt.where(ExternalComparison.station_id == station_id)

    res = await db.execute(stmt)
    comps = res.scalars().all()
    return [
        {
            "id": c.id,
            "campus_id": c.campus_id,
            "station_id": c.station_id,
            "timestamp_bucket_utc": c.timestamp_bucket.isoformat(),
            "airsense_prediction": c.airsense_prediction,
            "onsite_actual_pm2_5": c.onsite_actual_pm2_5,
            "open_meteo_pm2_5": c.open_meteo_pm2_5,
            "comparable_errors": c.comparable_errors_json
        }
        for c in comps
    ]


@router.post("/admin/rebuild", dependencies=[Depends(verify_admin_token)])
async def rebuild_comparisons(campus_id: str, station_id: str, db: AsyncSession = Depends(get_db_session)):
    return await ExternalBenchmarkingEngine.rebuild_comparisons(db, campus_id, station_id)

"""AirSense Pakistan Quality Control, Health, and Data Readiness Router."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.api.db.session import get_db_session
from apps.api.db.models import Station, Campus, QualityAssessment, RawReading, Observation, HourlyObservation
from services.forecasting.readiness_and_health import DataReadinessCalculator, SensorHealthEngine

router = APIRouter(prefix="/api/v1", tags=["Quality Control & Health"])


@router.get("/data-readiness")
async def get_data_readiness(
    campus_id: Optional[str] = None,
    station_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Returns model readiness indicators based on eligible hourly dataset completeness."""
    return await DataReadinessCalculator.compute_readiness(db, campus_id=campus_id, station_id=station_id)


@router.get("/sensor-health")
async def get_all_sensor_health(db: AsyncSession = Depends(get_db_session)):
    """Returns system-wide sensor health summary across all registered stations."""
    stmt = select(Station)
    res = await db.execute(stmt)
    stations = res.scalars().all()

    station_healths = []
    for s in stations:
        h = await SensorHealthEngine.compute_station_health(db, s.id)
        station_healths.append(h)

    active_count = sum(1 for h in station_healths if h.get("health_status") == "healthy" or h.get("status") == "active")
    overall_status = "healthy" if active_count > 0 else "configuration_required" if len(stations) == 0 else "degraded"

    return {
        "status": overall_status,
        "total_stations": len(stations),
        "active_stations": active_count,
        "stations_health": station_healths
    }


@router.get("/campuses/{campus_id}/health")
async def get_campus_health(campus_id: str, db: AsyncSession = Depends(get_db_session)):
    campus = await db.get(Campus, campus_id)
    if not campus:
        raise HTTPException(status_code=404, detail={"error": {"code": "CAMPUS_NOT_FOUND", "message": "Campus not found."}})

    stmt = select(Station).where(Station.campus_id == campus_id)
    res = await db.execute(stmt)
    stations = res.scalars().all()

    station_healths = []
    for s in stations:
        h = await SensorHealthEngine.compute_station_health(db, s.id)
        station_healths.append(h)

    overall_status = "healthy" if any(h["health_status"] == "healthy" for h in station_healths) else "configuration_required" if campus.status == "configuration_required" else "degraded"

    return {
        "campus_id": campus.id,
        "campus_code": campus.code,
        "campus_name": campus.name,
        "overall_status": overall_status,
        "station_count": len(stations),
        "stations_health": station_healths
    }


@router.get("/stations/{station_id}/health")
async def get_station_health(station_id: str, db: AsyncSession = Depends(get_db_session)):
    health = await SensorHealthEngine.compute_station_health(db, station_id)
    if health.get("error"):
        raise HTTPException(status_code=404, detail={"error": {"code": "STATION_NOT_FOUND", "message": health["error"]}})
    return health


@router.get("/quality/summary")
async def get_quality_summary(db: AsyncSession = Depends(get_db_session)):
    """Returns system-wide quality assessment breakdown."""
    stmt = select(QualityAssessment.quality_status, func.count(QualityAssessment.id)).group_by(QualityAssessment.quality_status)
    res = await db.execute(stmt)
    counts = dict(res.all())
    return {
        "status_counts": counts,
        "qc_version": "1.0.0"
    }

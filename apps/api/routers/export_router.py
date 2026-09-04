"""AirSense Pakistan Data Access and Streaming CSV Export Router."""

import csv
import io
from datetime import datetime, timezone
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.db.session import get_db_session
from apps.api.db.models import RawReading, Observation, HourlyObservation, QualityAssessment, Campus, Station

router = APIRouter(prefix="/api/v1", tags=["Data Access & Exports"])


def sanitize_csv_cell(val: Any) -> str:
    """Sanitizes text value to prevent CSV formula injection."""
    if val is None:
        return ""
    s = str(val)
    if s.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{s}"
    return s


# --- Data Access Routes ---

@router.get("/readings")
async def get_raw_readings(
    campus_id: Optional[str] = None,
    station_id: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(RawReading).order_by(RawReading.observed_at.desc()).limit(limit)
    if campus_id:
        stmt = stmt.where(RawReading.campus_id == campus_id)
    if station_id:
        stmt = stmt.where(RawReading.station_id == station_id)

    res = await db.execute(stmt)
    readings = res.scalars().all()
    return [
        {
            "id": r.id,
            "campus_id": r.campus_id,
            "station_id": r.station_id,
            "observed_at_utc": r.observed_at.isoformat(),
            "source": r.source,
            "pm1": r.pm1,
            "pm2_5": r.pm2_5,
            "pm10": r.pm10,
            "temperature_c": r.temperature_c,
            "humidity_pct": r.humidity_pct,
            "pressure_hpa": r.pressure_hpa,
            "rain_flag": r.rain_flag
        }
        for r in readings
    ]


@router.get("/observations")
async def get_observations(
    campus_id: Optional[str] = None,
    station_id: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Observation).order_by(Observation.observed_at.desc()).limit(limit)
    if campus_id:
        stmt = stmt.where(Observation.campus_id == campus_id)
    if station_id:
        stmt = stmt.where(Observation.station_id == station_id)

    res = await db.execute(stmt)
    obs = res.scalars().all()
    return [
        {
            "id": o.id,
            "campus_id": o.campus_id,
            "station_id": o.station_id,
            "observed_at_utc": o.observed_at.isoformat(),
            "source": o.source,
            "source_type": o.source_type,
            "pm2_5": o.pm2_5,
            "pm10": o.pm10,
            "temperature_c": o.temperature_c,
            "humidity_pct": o.humidity_pct,
            "quality_score": o.quality_score,
            "is_model_eligible": o.is_model_eligible
        }
        for o in obs
    ]


@router.get("/observations/latest")
async def get_latest_observations(db: AsyncSession = Depends(get_db_session)):
    stmt = select(Observation).order_by(Observation.observed_at.desc()).limit(10)
    res = await db.execute(stmt)
    obs = res.scalars().all()
    return [
        {
            "id": o.id,
            "station_id": o.station_id,
            "observed_at_utc": o.observed_at.isoformat(),
            "pm2_5": o.pm2_5,
            "quality_score": o.quality_score
        }
        for o in obs
    ]


@router.get("/hourly-observations")
@router.get("/observations/hourly")
async def get_hourly_observations(
    campus_id: Optional[str] = None,
    station_id: Optional[str] = None,
    limit: int = Query(48, le=500),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(HourlyObservation).order_by(HourlyObservation.hour_start.desc()).limit(limit)
    if campus_id:
        stmt = stmt.where(HourlyObservation.campus_id == campus_id)
    if station_id:
        stmt = stmt.where(HourlyObservation.station_id == station_id)

    res = await db.execute(stmt)
    hourly = res.scalars().all()
    return [
        {
            "id": h.id,
            "campus_id": h.campus_id,
            "station_id": h.station_id,
            "source": h.source,
            "hour_start": h.hour_start.isoformat(),
            "hour_start_utc": h.hour_start.isoformat(),
            "pm1_mean": h.pm1_mean,
            "pm2_5_mean": h.pm2_5_mean,
            "pm10_mean": h.pm10_mean,
            "temperature_mean": h.temperature_mean,
            "humidity_mean": h.humidity_mean,
            "pressure_mean": h.pressure_mean,
            "average_quality_score": h.average_quality_score,
            "completeness_pct": h.completeness_pct,
            "is_model_eligible": h.is_model_eligible
        }
        for h in hourly
    ]


# --- CSV Export Routes ---

@router.get("/export/csv")
async def export_general_csv(
    dataset: str = Query("hourly", pattern="^(hourly|readings|observations)$"),
    campus_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Unified CSV export endpoint supporting dataset=hourly, readings, observations."""
    if dataset == "readings":
        return await export_readings_csv(campus_id=campus_id, db=db)
    elif dataset == "observations":
        return await export_observations_csv(campus_id=campus_id, db=db)
    else:
        stmt = select(HourlyObservation).order_by(HourlyObservation.hour_start.desc()).limit(1000)
        if campus_id:
            stmt = stmt.where(HourlyObservation.campus_id == campus_id)
        res = await db.execute(stmt)
        hourly_records = res.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["# AirSense Pakistan Hourly Observations Export (UTC Timestamps)"])
        writer.writerow(["id", "campus_id", "station_id", "source", "hour_start_utc", "pm1_mean", "pm2_5_mean", "pm10_mean", "temp_mean", "humidity_mean", "pressure_mean", "quality_score", "completeness_pct", "is_model_eligible"])

        for h in hourly_records:
            writer.writerow([
                sanitize_csv_cell(h.id),
                sanitize_csv_cell(h.campus_id),
                sanitize_csv_cell(h.station_id),
                sanitize_csv_cell(h.source),
                sanitize_csv_cell(h.hour_start.isoformat()),
                sanitize_csv_cell(h.pm1_mean),
                sanitize_csv_cell(h.pm2_5_mean),
                sanitize_csv_cell(h.pm10_mean),
                sanitize_csv_cell(h.temperature_mean),
                sanitize_csv_cell(h.humidity_mean),
                sanitize_csv_cell(h.pressure_mean),
                sanitize_csv_cell(h.average_quality_score),
                sanitize_csv_cell(h.completeness_pct),
                sanitize_csv_cell(h.is_model_eligible)
            ])

        output.seek(0)
        return StreamingResponse(
            content=iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=airsense_hourly_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"}
        )


@router.get("/exports/readings.csv")
async def export_readings_csv(campus_id: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    """Streaming CSV export for raw readings."""
    stmt = select(RawReading).order_by(RawReading.observed_at.desc()).limit(1000)
    if campus_id:
        stmt = stmt.where(RawReading.campus_id == campus_id)
    res = await db.execute(stmt)
    readings = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["# AirSense Pakistan Raw Readings Export (UTC Timestamps)"])
    writer.writerow(["reading_id", "campus_id", "station_id", "observed_at_utc", "source", "pm1", "pm2_5", "pm10", "temp_c", "humidity_pct", "pressure_hpa", "rain_flag"])

    for r in readings:
        writer.writerow([
            sanitize_csv_cell(r.id),
            sanitize_csv_cell(r.campus_id),
            sanitize_csv_cell(r.station_id),
            sanitize_csv_cell(r.observed_at.isoformat()),
            sanitize_csv_cell(r.source),
            sanitize_csv_cell(r.pm1),
            sanitize_csv_cell(r.pm2_5),
            sanitize_csv_cell(r.pm10),
            sanitize_csv_cell(r.temperature_c),
            sanitize_csv_cell(r.humidity_pct),
            sanitize_csv_cell(r.pressure_hpa),
            sanitize_csv_cell(r.rain_flag)
        ])

    output.seek(0)
    return StreamingResponse(
        content=iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=airsense_raw_readings_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"}
    )


@router.get("/exports/observations.csv")
async def export_observations_csv(campus_id: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    """Streaming CSV export for normalized observations."""
    stmt = select(Observation).order_by(Observation.observed_at.desc()).limit(1000)
    if campus_id:
        stmt = stmt.where(Observation.campus_id == campus_id)
    res = await db.execute(stmt)
    obs = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["# AirSense Pakistan Observations Export (UTC Timestamps)"])
    writer.writerow(["observation_id", "campus_id", "station_id", "observed_at_utc", "source", "source_type", "pm2_5", "pm10", "temp_c", "humidity_pct", "quality_score", "is_model_eligible"])

    for o in obs:
        writer.writerow([
            sanitize_csv_cell(o.id),
            sanitize_csv_cell(o.campus_id),
            sanitize_csv_cell(o.station_id),
            sanitize_csv_cell(o.observed_at.isoformat()),
            sanitize_csv_cell(o.source),
            sanitize_csv_cell(o.source_type),
            sanitize_csv_cell(o.pm2_5),
            sanitize_csv_cell(o.pm10),
            sanitize_csv_cell(o.temperature_c),
            sanitize_csv_cell(o.humidity_pct),
            sanitize_csv_cell(o.quality_score),
            sanitize_csv_cell(o.is_model_eligible)
        ])

    output.seek(0)
    return StreamingResponse(
        content=iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=airsense_observations_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"}
    )

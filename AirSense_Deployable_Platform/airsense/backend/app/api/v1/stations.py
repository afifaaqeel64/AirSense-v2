from fastapi import APIRouter, Query
from typing import Optional
import asyncpg
from app.core.config import settings

router = APIRouter(prefix="/stations", tags=["Stations"])
DSN = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

@router.get("/{city}")
async def get_stations(city: str, active_only: bool = Query(True)):
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(
            "SELECT * FROM stations WHERE city=$1" + (" AND is_active=TRUE" if active_only else ""),
            city.lower()
        )
        return {"city": city, "stations": [dict(r) for r in rows]}
    finally:
        await conn.close()

@router.get("/{city}/{station_id}")
async def get_station_detail(city: str, station_id: str):
    conn = await asyncpg.connect(DSN)
    try:
        row = await conn.fetchrow(
            "SELECT * FROM stations WHERE city=$1 AND id=$2", city.lower(), station_id
        )
        if not row:
            from fastapi import HTTPException
            raise HTTPException(404, "Station not found")
        return dict(row)
    finally:
        await conn.close()

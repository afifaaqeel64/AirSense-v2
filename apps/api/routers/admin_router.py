"""AirSense Pakistan Administration & Entity Management Router."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.config import settings
from apps.api.core.security import verify_admin_token, generate_secure_token, hash_token
from apps.api.db.session import get_db_session
from apps.api.db.models import Campus, Station, Device, MaintenanceEvent
from services.backup.backup_service import BackupService

router = APIRouter(prefix="/api/v1", tags=["Administration & Configuration"])


# --- Schemas ---

class CampusCreateSchema(BaseModel):
    code: str = Field(..., json_schema_extra={"example": "ISB_CAMPUS"})
    name: str = Field(..., json_schema_extra={"example": "Islamabad Campus"})
    city: str = Field(..., json_schema_extra={"example": "Islamabad"})
    country: str = Field("Pakistan")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: str = Field("Asia/Karachi")
    contact_name: str = Field(..., json_schema_extra={"example": "Muhammad M. Qureshi"})


class CampusUpdateSchema(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_name: Optional[str] = None
    status: Optional[str] = None


class StationCreateSchema(BaseModel):
    campus_id: str
    station_code: str = Field(..., json_schema_extra={"example": "ISB-CAMPUS-01"})
    station_name: str = Field(..., json_schema_extra={"example": "Islamabad Main Station"})
    installation_location: str = Field("Main Building Rooftop")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_m: Optional[float] = None
    sampling_interval_seconds: int = Field(60, gt=0)


class DeviceCreateSchema(BaseModel):
    station_id: str
    device_uid: str = Field(..., json_schema_extra={"example": "ISB-ROOF-01"})
    device_type: str = Field("ESP32_WROOM_32D")
    model: str = Field("AirSense Station V1")
    serial_number: Optional[str] = None
    firmware_version: str = Field("1.0.0")


class MaintenanceCreateSchema(BaseModel):
    campus_id: str
    station_id: Optional[str] = None
    device_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    event_type: str = Field("servicing")
    description: str
    performed_by: str


class BackupCreateSchema(BaseModel):
    description: str = Field("Manual administrative backup", json_schema_extra={"example": "Pre-maintenance backup"})


# --- Campus Routes ---

@router.get("/campuses")
async def list_campuses(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Campus))
    campuses = result.scalars().all()
    return [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "city": c.city,
            "country": c.country,
            "latitude": c.latitude if c.latitude is not None else "configuration_required",
            "longitude": c.longitude if c.longitude is not None else "configuration_required",
            "timezone": c.timezone,
            "status": c.status,
            "contact_name": c.contact_name,
            "created_at": c.created_at.isoformat()
        }
        for c in campuses
    ]


@router.get("/campuses/{campus_id_or_code}")
async def get_campus(campus_id_or_code: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Campus).where((Campus.id == campus_id_or_code) | (Campus.code == campus_id_or_code))
    result = await db.execute(stmt)
    campus = result.scalar_one_or_none()
    if not campus:
        raise HTTPException(status_code=404, detail={"error": {"code": "CAMPUS_NOT_FOUND", "message": "Campus not found."}})
    return {
        "id": campus.id,
        "code": campus.code,
        "name": campus.name,
        "city": campus.city,
        "latitude": campus.latitude if campus.latitude is not None else "configuration_required",
        "longitude": campus.longitude if campus.longitude is not None else "configuration_required",
        "status": campus.status,
        "contact_name": campus.contact_name
    }


@router.post("/admin/campuses", dependencies=[Depends(verify_admin_token)])
async def create_campus(payload: CampusCreateSchema, db: AsyncSession = Depends(get_db_session)):
    existing = await db.execute(select(Campus).where(Campus.code == payload.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail={"error": {"code": "CAMPUS_CODE_EXISTS", "message": f"Campus code '{payload.code}' already exists."}})

    has_coords = payload.latitude is not None and payload.longitude is not None
    campus_status = "active" if has_coords else "configuration_required"

    campus = Campus(
        code=payload.code,
        name=payload.name,
        city=payload.city,
        country=payload.country,
        latitude=payload.latitude,
        longitude=payload.longitude,
        timezone=payload.timezone,
        status=campus_status,
        contact_name=payload.contact_name
    )
    db.add(campus)
    await db.commit()
    await db.refresh(campus)
    return {"status": "created", "campus_id": campus.id, "code": campus.code}


# --- Station Routes ---

@router.get("/stations")
async def list_stations(campus_id: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Station)
    if campus_id:
        stmt = stmt.where(Station.campus_id == campus_id)
    result = await db.execute(stmt)
    stations = result.scalars().all()
    return [
        {
            "id": s.id,
            "campus_id": s.campus_id,
            "station_code": s.station_code,
            "station_name": s.station_name,
            "installation_location": s.installation_location,
            "sampling_interval_seconds": s.sampling_interval_seconds,
            "status": s.status,
            "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None
        }
        for s in stations
    ]


@router.post("/admin/stations", dependencies=[Depends(verify_admin_token)])
async def create_station(payload: StationCreateSchema, db: AsyncSession = Depends(get_db_session)):
    campus = await db.get(Campus, payload.campus_id)
    if not campus:
        raise HTTPException(status_code=404, detail={"error": {"code": "CAMPUS_NOT_FOUND", "message": "Associated campus not found."}})

    station = Station(
        campus_id=payload.campus_id,
        station_code=payload.station_code,
        station_name=payload.station_name,
        installation_location=payload.installation_location,
        latitude=payload.latitude or campus.latitude,
        longitude=payload.longitude or campus.longitude,
        elevation_m=payload.elevation_m,
        sampling_interval_seconds=payload.sampling_interval_seconds
    )
    db.add(station)
    await db.commit()
    await db.refresh(station)
    return {"status": "created", "station_id": station.id, "station_code": station.station_code}


# --- Device Management Routes ---

@router.get("/admin/devices", dependencies=[Depends(verify_admin_token)])
async def list_devices(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Device))
    devices = result.scalars().all()
    return [
        {
            "id": d.id,
            "station_id": d.station_id,
            "device_uid": d.device_uid,
            "device_type": d.device_type,
            "model": d.model,
            "firmware_version": d.firmware_version,
            "status": d.status,
            "last_authenticated_at": d.last_authenticated_at.isoformat() if d.last_authenticated_at else None
        }
        for d in devices
    ]


@router.post("/admin/devices", dependencies=[Depends(verify_admin_token)])
async def create_device(payload: DeviceCreateSchema, db: AsyncSession = Depends(get_db_session)):
    station = await db.get(Station, payload.station_id)
    if not station:
        raise HTTPException(status_code=404, detail={"error": {"code": "STATION_NOT_FOUND", "message": "Station not found."}})

    raw_token = generate_secure_token()
    token_h = hash_token(raw_token)

    device = Device(
        station_id=payload.station_id,
        device_uid=payload.device_uid,
        device_type=payload.device_type,
        model=payload.model,
        serial_number=payload.serial_number,
        firmware_version=payload.firmware_version,
        token_hash=token_h,
        status="active"
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    return {
        "status": "created",
        "device_id": device.id,
        "device_uid": device.device_uid,
        "device_token": raw_token,
        "warning": "Save this device_token immediately. It will not be shown again."
    }


@router.post("/admin/devices/{device_id}/rotate-token", dependencies=[Depends(verify_admin_token)])
async def rotate_device_token(device_id: str, db: AsyncSession = Depends(get_db_session)):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail={"error": {"code": "DEVICE_NOT_FOUND", "message": "Device not found."}})

    new_raw_token = generate_secure_token()
    device.token_hash = hash_token(new_raw_token)
    device.token_last_rotated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "status": "token_rotated",
        "device_id": device.id,
        "device_uid": device.device_uid,
        "new_device_token": new_raw_token,
        "warning": "Previous token invalidated. Update device firmware immediately."
    }


@router.post("/admin/devices/{device_id}/disable", dependencies=[Depends(verify_admin_token)])
async def disable_device(device_id: str, db: AsyncSession = Depends(get_db_session)):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail={"error": {"code": "DEVICE_NOT_FOUND", "message": "Device not found."}})
    device.status = "disabled"
    await db.commit()
    return {"status": "disabled", "device_id": device.id}


@router.post("/admin/devices/{device_id}/enable", dependencies=[Depends(verify_admin_token)])
async def enable_device(device_id: str, db: AsyncSession = Depends(get_db_session)):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail={"error": {"code": "DEVICE_NOT_FOUND", "message": "Device not found."}})
    device.status = "active"
    await db.commit()
    return {"status": "active", "device_id": device.id}


# --- Maintenance Routes ---

@router.get("/maintenance")
async def list_maintenance(campus_id: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    stmt = select(MaintenanceEvent)
    if campus_id:
        stmt = stmt.where(MaintenanceEvent.campus_id == campus_id)
    result = await db.execute(stmt)
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "campus_id": e.campus_id,
            "station_id": e.station_id,
            "started_at": e.started_at.isoformat(),
            "ended_at": e.ended_at.isoformat() if e.ended_at else None,
            "event_type": e.event_type,
            "description": e.description,
            "performed_by": e.performed_by
        }
        for e in events
    ]


@router.post("/admin/maintenance", dependencies=[Depends(verify_admin_token)])
async def create_maintenance_event(payload: MaintenanceCreateSchema, db: AsyncSession = Depends(get_db_session)):
    event = MaintenanceEvent(
        campus_id=payload.campus_id,
        station_id=payload.station_id,
        device_id=payload.device_id,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        event_type=payload.event_type,
        description=payload.description,
        performed_by=payload.performed_by
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"status": "created", "event_id": event.id}


# --- Backup & Restore Routes ---

@router.post("/admin/backups", dependencies=[Depends(verify_admin_token)])
async def create_backup(payload: BackupCreateSchema, db: AsyncSession = Depends(get_db_session)):
    res = await BackupService.create_backup(db, description=payload.description)
    return res


@router.get("/admin/backups", dependencies=[Depends(verify_admin_token)])
async def list_backups():
    return BackupService.list_backups()


@router.get("/admin/backups/{backup_id}/verify", dependencies=[Depends(verify_admin_token)])
async def verify_backup(backup_id: str):
    return BackupService.verify_backup(backup_id)

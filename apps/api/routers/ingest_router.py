"""AirSense Pakistan Live ESP32 Telemetry Ingestion Router."""

import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import paho.mqtt.publish as mqtt_publish

from apps.api.core.config import settings
from apps.api.core.security import authenticate_device
from apps.api.db.session import get_db_session
from apps.api.db.models import Device, Station, Campus, RawReading, QualityAssessment, Observation
from services.quality_control.qc_engine import QualityControlEngine, compute_content_hash
from services.quality_control.gap_and_aggregation import HourlyAggregationEngine

router = APIRouter(prefix="/api/v1/ingest", tags=["Sensor Telemetry Ingestion"])

def _broadcast_to_hivemq(payload_data: dict):
    try:
        mqtt_publish.single(
            "airsense/karachi/bic_roof/telemetry",
            payload=json.dumps(payload_data),
            hostname="broker.hivemq.com",
            port=1883,
            keepalive=10
        )
    except Exception:
        pass


# --- Schemas ---

class ESP32ReadingsSubschema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pm1: Optional[float] = None
    pm25: Optional[float] = Field(None, alias="pm2_5")
    pm10: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    rain_flag: Optional[bool] = None


class ESP32IngestPayload(BaseModel):
    schema_version: str = Field("1.0")
    device_uid: Optional[str] = None
    station_code: Optional[str] = None
    timestamp: Optional[str] = None
    timestamp_epoch: Optional[int] = None
    pm1: Optional[float] = None
    pm2_5: Optional[float] = None
    pm10: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    rain_flag: Optional[bool] = None
    firmware_version: str = Field("1.0.0")
    sequence_number: Optional[int] = None

    # Alternative / Legacy fields
    device_id: Optional[str] = None
    campus_code: Optional[str] = None
    timestamp_utc: Optional[str] = None
    readings: Optional[Dict[str, Any]] = None


# --- Ingestion Route ---

@router.post("/reading")
async def ingest_esp32_reading(
    payload: ESP32IngestPayload,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    device: Device = Depends(authenticate_device),
    db: AsyncSession = Depends(get_db_session)
):
    """Live ESP32 telemetry ingestion endpoint with authentication, idempotency, raw preservation, and QC."""
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    received_at_utc = datetime.now(timezone.utc)

    # 1. Resolve Station and Campus
    station = await db.get(Station, device.station_id)
    if not station:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "STATION_NOT_FOUND", "message": "Device not bound to a valid station.", "request_id": request_id}}
        )

    campus = await db.get(Campus, station.campus_id)

    # 2. Extract telemetry parameters from canonical or alternative schema
    pm1 = payload.pm1
    pm2_5 = payload.pm2_5
    pm10 = payload.pm10
    temp = payload.temperature
    hum = payload.humidity
    press = payload.pressure
    rain = payload.rain_flag

    if payload.readings:
        pm1 = pm1 if pm1 is not None else payload.readings.get("pm1")
        pm2_5 = pm2_5 if pm2_5 is not None else payload.readings.get("pm25", payload.readings.get("pm2_5"))
        pm10 = pm10 if pm10 is not None else payload.readings.get("pm10")
        temp = temp if temp is not None else payload.readings.get("temperature")
        hum = hum if hum is not None else payload.readings.get("humidity")
        press = press if press is not None else payload.readings.get("pressure")
        rain = rain if rain is not None else payload.readings.get("rain_flag")

    # Sanitize hardware I2C error states (e.g. -148.5C on disconnected BME280)
    if temp is not None:
        try:
            t_f = float(temp)
            if t_f < -40.0 or t_f > 85.0 or t_f == -148.5:
                temp = None
        except (ValueError, TypeError):
            temp = None

    if hum is not None:
        try:
            h_f = float(hum)
            if h_f < 0.0 or h_f > 100.0 or (temp is None and h_f == 0.0):
                hum = None
        except (ValueError, TypeError):
            hum = None

    if press is not None:
        try:
            p_f = float(press)
            if p_f < 300.0 or p_f > 1200.0 or (temp is None and p_f > 1150.0):
                press = None
        except (ValueError, TypeError):
            press = None

    # 3. Parse timestamp
    ts_raw = payload.timestamp or payload.timestamp_utc
    observed_at_utc: datetime
    if ts_raw:
        try:
            observed_at_utc = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            observed_at_utc = received_at_utc
    elif payload.timestamp_epoch and payload.timestamp_epoch > 1000000000:
        observed_at_utc = datetime.fromtimestamp(payload.timestamp_epoch, tz=timezone.utc)
    else:
        observed_at_utc = received_at_utc

    # 4. Content hash calculation & Deduplication check
    c_hash = compute_content_hash(station.station_code, observed_at_utc, pm2_5, temp)

    # Check for existing duplicate reading
    stmt_dup = select(RawReading).where(
        and_(
            RawReading.station_id == station.id,
            RawReading.content_hash == c_hash
        )
    )
    res_dup = await db.execute(stmt_dup)
    existing_raw = res_dup.scalar_one_or_none()

    if existing_raw:
        # Return idempotent duplicate response without inserting a second row
        return {
            "request_id": request_id,
            "ingestion_id": existing_raw.id,
            "raw_reading_id": existing_raw.id,
            "accepted": True,
            "duplicate": True,
            "observed_at_utc": observed_at_utc.isoformat(),
            "received_at_utc": received_at_utc.isoformat(),
            "campus_code": campus.code if campus else "UNKNOWN",
            "station_code": station.station_code,
            "quality_processing_state": "duplicate_skipped",
            "server_schema_version": "1.0"
        }

    # 5. Raw Reading Storage
    raw_payload_dict = payload.model_dump(by_alias=True, exclude_none=True)
    raw_record = RawReading(
        campus_id=station.campus_id,
        station_id=station.id,
        device_id=device.id,
        observed_at=observed_at_utc,
        source_timestamp_original=str(ts_raw) if ts_raw else str(observed_at_utc),
        received_at=received_at_utc,
        source="onsite_esp32",
        pm1=pm1,
        pm2_5=pm2_5,
        pm10=pm10,
        temperature_c=temp,
        humidity_pct=hum,
        pressure_hpa=press,
        rain_flag=rain,
        payload_json=raw_payload_dict,
        ingested_via="esp32_http",
        idempotency_key=idempotency_key,
        sequence_number=payload.sequence_number,
        schema_version=payload.schema_version,
        content_hash=c_hash
    )
    db.add(raw_record)
    await db.flush()

    # 6. Quality Control Evaluation
    reading_for_qc = {
        "observed_at": observed_at_utc,
        "pm1": pm1,
        "pm2_5": pm2_5,
        "pm10": pm10,
        "temperature_c": temp,
        "humidity_pct": hum,
        "pressure_hpa": press
    }
    qc_res = QualityControlEngine.evaluate_reading(reading_for_qc)

    qa_record = QualityAssessment(
        raw_reading_id=raw_record.id,
        quality_score=qc_res.quality_score,
        quality_status=qc_res.quality_status,
        impossible_value_flag=qc_res.impossible_value_flag,
        high_humidity_flag=qc_res.high_humidity_flag,
        spike_review_flag=qc_res.spike_review_flag,
        ordering_consistency_flag=qc_res.ordering_consistency_flag,
        timestamp_flag=qc_res.timestamp_flag,
        validation_messages_json=qc_res.validation_messages,
        qc_version=qc_res.qc_version
    )
    db.add(qa_record)

    # 7. Observation Creation (if not rejected)
    if qc_res.quality_status != "rejected":
        existing_obs_stmt = select(Observation).where(
            and_(
                Observation.station_id == station.id,
                Observation.source == "onsite_esp32",
                Observation.observed_at == observed_at_utc
            )
        )
        existing_obs = await db.execute(existing_obs_stmt)
        if existing_obs.scalars().first() is None:
            obs_record = Observation(
                raw_reading_id=raw_record.id,
                campus_id=station.campus_id,
                station_id=station.id,
                observed_at=observed_at_utc,
                source="onsite_esp32",
                source_type="ground_truth",
                pm1=pm1,
                pm2_5=pm2_5,
                pm10=pm10,
                temperature_c=temp,
                humidity_pct=hum,
                pressure_hpa=press,
                rain_flag=rain,
                quality_score=qc_res.quality_score,
                is_model_eligible=(qc_res.quality_score >= 0.60),
                eligibility_reason="valid_ground_truth" if qc_res.quality_score >= 0.60 else "low_quality_score"
            )
            db.add(obs_record)

    # 8. Update Station Last Seen
    station.last_seen_at = received_at_utc
    await db.commit()

    # Broadcast to Global Cloud MQTT Broker for Vercel / Remote Dashboards
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _broadcast_to_hivemq, {
            "schema_version": "1.0",
            "device_uid": device.device_uid,
            "station_code": station.station_code,
            "campus_code": campus.code if campus else "KARACHI",
            "sequence_number": payload.sequence_number or 0,
            "timestamp_epoch": int(observed_at_utc.timestamp()),
            "pm1": pm1,
            "pm2_5": pm2_5,
            "pm10": pm10,
            "temperature": temp,
            "humidity": hum,
            "pressure": press,
            "rain_flag": bool(rain)
        })
    except Exception:
        pass

    # 9. Aggregate Hourly Observation
    await HourlyAggregationEngine.process_hour(
        db,
        campus_id=station.campus_id,
        station_id=station.id,
        source="onsite_esp32",
        hour_start=observed_at_utc
    )
    await db.commit()

    return {
        "request_id": request_id,
        "ingestion_id": raw_record.id,
        "raw_reading_id": raw_record.id,
        "accepted": True,
        "duplicate": False,
        "observed_at_utc": observed_at_utc.isoformat(),
        "received_at_utc": received_at_utc.isoformat(),
        "campus_code": campus.code if campus else "UNKNOWN",
        "station_code": station.station_code,
        "quality_processing_state": qc_res.quality_status,
        "server_schema_version": "1.0"
    }


@router.get("/health")
async def ingestion_health():
    """Ingestion subsystem health endpoint."""
    return {"subsystem": "sensor_ingestion", "status": "healthy", "supported_paths": ["live_esp32_http", "sd_card_csv"]}


@router.get("/latest")
async def get_latest_readings(
    station_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session)
):
    """Returns recent raw sensor telemetry readings for live dashboard streaming and session history."""
    stmt = select(RawReading).order_by(RawReading.received_at.desc()).limit(limit)
    if station_id:
        stmt = stmt.where(RawReading.station_id == station_id)
        
    res = await db.execute(stmt)
    readings = res.scalars().all()
    
    output = []
    for r in readings:
        output.append({
            "id": r.id,
            "station_id": r.station_id,
            "device_id": r.device_id,
            "sequence_number": r.sequence_number,
            "observed_at": (r.observed_at.isoformat() + "Z") if r.observed_at and not r.observed_at.isoformat().endswith("Z") else (r.observed_at.isoformat() if r.observed_at else None),
            "received_at": (r.received_at.isoformat() + "Z") if r.received_at and not r.received_at.isoformat().endswith("Z") else (r.received_at.isoformat() if r.received_at else None),
            "pm1": r.pm1,
            "pm2_5": r.pm2_5,
            "pm10": r.pm10,
            "temperature_c": r.temperature_c,
            "humidity_pct": r.humidity_pct,
            "pressure_hpa": r.pressure_hpa,
            "rain_flag": r.rain_flag,
            "source": r.source,
            "ingested_via": r.ingested_via,
            "schema_version": r.schema_version
        })
    return output


@router.get("/sensors/diagnostic")
async def get_sensor_diagnostic_status(
    station_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Evaluates the latest sensor telemetry to determine whether physical sensors are truly connected and operational."""
    from services.quality_control.sensor_health_engine import SensorHealthEngine

    stmt = select(RawReading).order_by(RawReading.received_at.desc()).limit(1)
    if station_id:
        stmt = stmt.where(RawReading.station_id == station_id)
        
    res = await db.execute(stmt)
    latest_reading = res.scalar_one_or_none()

    if not latest_reading:
        return SensorHealthEngine.evaluate_sensor_connectivity(None, None)

    reading_dict = {
        "pm1": latest_reading.pm1,
        "pm2_5": latest_reading.pm2_5,
        "pm10": latest_reading.pm10,
        "temperature_c": latest_reading.temperature_c,
        "humidity_pct": latest_reading.humidity_pct,
        "pressure_hpa": latest_reading.pressure_hpa,
        "rain_flag": latest_reading.rain_flag,
        "station_code": "BIC-KHI-ROOF-01",
        "device_uid": "AIRSENSE-NODE-KHI-01"
    }

    return SensorHealthEngine.evaluate_sensor_connectivity(
        latest_reading=reading_dict,
        last_received_at=latest_reading.received_at,
        offline_threshold_seconds=15
    )

"""AirSense Pakistan Open-Meteo Air Quality External Provider Adapter."""

import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.config import settings
from apps.api.db.models import Campus, Station, RawReading, Observation, ExternalProviderRun
from services.quality_control.qc_engine import QualityControlEngine, compute_content_hash


class OpenMeteoAirQualityAdapter:
    PROVIDER_NAME = "open_meteo_air_quality"
    BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    @classmethod
    async def fetch_and_sync(cls, db: AsyncSession, campus_id: str) -> ExternalProviderRun:
        """Fetches current and hourly air quality telemetry for a campus from Open-Meteo AQ API."""
        started_at = datetime.now(timezone.utc)
        campus = await db.get(Campus, campus_id)

        if not campus or campus.latitude is None or campus.longitude is None:
            run = ExternalProviderRun(
                provider=cls.PROVIDER_NAME,
                campus_id=campus_id,
                started_at=started_at,
                completed_at=started_at,
                status="skipped_no_coords",
                sanitized_error_message="Campus coordinates missing (configuration_required)."
            )
            db.add(run)
            await db.commit()
            return run

        params = {
            "latitude": campus.latitude,
            "longitude": campus.longitude,
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi",
            "timezone": "UTC"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.BASE_URL, params=params)
                http_status = response.status_code

                if response.status_code != 200:
                    run = ExternalProviderRun(
                        provider=cls.PROVIDER_NAME,
                        campus_id=campus_id,
                        started_at=started_at,
                        completed_at=datetime.now(timezone.utc),
                        status="failed",
                        http_status=http_status,
                        sanitized_error_message=f"HTTP Error {http_status}: {response.text[:200]}"
                    )
                    db.add(run)
                    await db.commit()
                    return run

                data = response.json()

        except Exception as e:
            run = ExternalProviderRun(
                provider=cls.PROVIDER_NAME,
                campus_id=campus_id,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                status="failed",
                sanitized_error_message=f"Network error: {str(e)[:200]}"
            )
            db.add(run)
            await db.commit()
            return run

        # Process current air quality observation
        current = data.get("current", {})
        ts_str = current.get("time", started_at.isoformat())
        try:
            observed_at = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            observed_at = started_at

        pm2_5 = current.get("pm2_5")
        pm10 = current.get("pm10")
        us_aqi = current.get("us_aqi")

        # Find or create provider station for campus
        stmt_st = select(Station).where(Station.campus_id == campus_id, Station.station_code == f"EXT-OM-AQ-{campus.code}")
        res_st = await db.execute(stmt_st)
        ext_station = res_st.scalar_one_or_none()

        if not ext_station:
            ext_station = Station(
                campus_id=campus_id,
                station_code=f"EXT-OM-AQ-{campus.code}",
                station_name=f"Open-Meteo Air Quality ({campus.name})",
                installation_location="External Air Quality Model Grid",
                latitude=campus.latitude,
                longitude=campus.longitude,
                status="active"
            )
            db.add(ext_station)
            await db.flush()

        c_hash = compute_content_hash(ext_station.station_code, observed_at, pm2_5, None)

        raw_rec = RawReading(
            campus_id=campus_id,
            station_id=ext_station.id,
            observed_at=observed_at,
            received_at=started_at,
            source=cls.PROVIDER_NAME,
            pm2_5=pm2_5,
            pm10=pm10,
            aqi=int(us_aqi) if us_aqi is not None else None,
            aqi_standard="US_EPA",
            payload_json=data,
            ingested_via="provider_sync",
            content_hash=c_hash
        )
        db.add(raw_rec)
        await db.flush()

        obs_rec = Observation(
            raw_reading_id=raw_rec.id,
            campus_id=campus_id,
            station_id=ext_station.id,
            observed_at=observed_at,
            source=cls.PROVIDER_NAME,
            source_type="external_model",
            pm2_5=pm2_5,
            pm10=pm10,
            aqi=int(us_aqi) if us_aqi is not None else None,
            aqi_standard="US_EPA",
            quality_score=0.90,
            is_model_eligible=True,
            eligibility_reason="external_air_quality_grid"
        )
        db.add(obs_rec)

        run = ExternalProviderRun(
            provider=cls.PROVIDER_NAME,
            campus_id=campus_id,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            status="success",
            http_status=200,
            records_received=1,
            records_inserted=1
        )
        db.add(run)
        await db.commit()
        return run

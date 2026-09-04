"""AirSense Pakistan Data Readiness Calculator and Sensor/Campus Health Engine."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from apps.api.db.models import Campus, Station, Device, HourlyObservation, RawReading, QualityAssessment, MaintenanceEvent


class DataReadinessCalculator:
    # Model Thresholds
    PERSISTENCE_THRESHOLD = 25
    LINEAR_THRESHOLD = 168
    TREE_THRESHOLD = 500
    BOOSTING_THRESHOLD = 1000
    DEEP_LEARNING_THRESHOLD = 5000

    @classmethod
    async def compute_readiness(
        cls,
        db: AsyncSession,
        campus_id: Optional[str] = None,
        station_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculates model readiness indicators based on clean eligible hourly observations."""
        stmt = select(HourlyObservation).where(HourlyObservation.is_model_eligible == True)
        if campus_id:
            stmt = stmt.where(HourlyObservation.campus_id == campus_id)
        if station_id:
            stmt = stmt.where(HourlyObservation.station_id == station_id)

        result = await db.execute(stmt)
        eligible_obs = result.scalars().all()

        total_eligible = len(eligible_obs)
        earliest_ts = min([o.hour_start for o in eligible_obs]).isoformat() if eligible_obs else None
        latest_ts = max([o.hour_start for o in eligible_obs]).isoformat() if eligible_obs else None

        return {
            "total_eligible_hourly_observations": total_eligible,
            "earliest_eligible_timestamp": earliest_ts,
            "latest_eligible_timestamp": latest_ts,
            "model_readiness": {
                "persistence": {
                    "ready": total_eligible >= cls.PERSISTENCE_THRESHOLD,
                    "required_count": cls.PERSISTENCE_THRESHOLD,
                    "current_count": total_eligible
                },
                "linear_regression": {
                    "ready": total_eligible >= cls.LINEAR_THRESHOLD,
                    "required_count": cls.LINEAR_THRESHOLD,
                    "current_count": total_eligible
                },
                "tree_models": {
                    "ready": total_eligible >= cls.TREE_THRESHOLD,
                    "required_count": cls.TREE_THRESHOLD,
                    "current_count": total_eligible
                },
                "gradient_boosting": {
                    "ready": total_eligible >= cls.BOOSTING_THRESHOLD,
                    "required_count": cls.BOOSTING_THRESHOLD,
                    "current_count": total_eligible
                },
                "deep_learning": {
                    "ready": total_eligible >= cls.DEEP_LEARNING_THRESHOLD,
                    "required_count": cls.DEEP_LEARNING_THRESHOLD,
                    "current_count": total_eligible
                }
            }
        }


class SensorHealthEngine:

    @classmethod
    async def compute_station_health(
        cls,
        db: AsyncSession,
        station_id: str
    ) -> Dict[str, Any]:
        """Computes telemetry health metrics, uptime %, gaps, and status for a single station."""
        station = await db.get(Station, station_id)
        if not station:
            return {"status": "unknown", "error": "Station not found"}

        campus = await db.get(Campus, station.campus_id)

        now_utc = datetime.now(timezone.utc)
        last_seen = station.last_seen_at.astimezone(timezone.utc) if station.last_seen_at else None

        minutes_since_last = int((now_utc - last_seen).total_seconds() / 60.0) if last_seen else None

        # Determine Health Status
        if not campus or campus.status == "configuration_required":
            health_status = "not_configured"
        elif not station.monitoring_started_at and not last_seen:
            health_status = "not_started"
        elif minutes_since_last is None or minutes_since_last > 1440:  # 24 hours
            health_status = "offline"
        elif minutes_since_last > 60:
            health_status = "stale"
        elif minutes_since_last > 15:
            health_status = "delayed"
        else:
            health_status = "healthy"

        # Raw Reading Counts
        stmt_raw = select(func.count(RawReading.id)).where(RawReading.station_id == station_id)
        raw_count_res = await db.execute(stmt_raw)
        total_raw = raw_count_res.scalar() or 0

        return {
            "station_id": station.id,
            "station_code": station.station_code,
            "station_name": station.station_name,
            "campus_code": campus.code if campus else "UNKNOWN",
            "health_status": health_status,
            "monitoring_started_at": station.monitoring_started_at.isoformat() if station.monitoring_started_at else None,
            "last_seen_at": last_seen.isoformat() if last_seen else None,
            "minutes_since_last_reading": minutes_since_last,
            "total_raw_readings": total_raw,
            "calculated_at": now_utc.isoformat()
        }

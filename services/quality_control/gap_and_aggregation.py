"""AirSense Pakistan Gap Detection, Short-Gap Interpolation, and Hourly Aggregation Engine."""

import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from apps.api.db.models import Station, Observation, HourlyObservation, MaintenanceEvent, RawReading


def calculate_circular_wind_mean(degrees_list: List[float]) -> Optional[float]:
    """Calculates the circular mean of wind direction angles in degrees."""
    valid_deg = [d for d in degrees_list if d is not None and not math.isnan(d)]
    if not valid_deg:
        return None
    sin_sum = sum(math.sin(math.radians(d)) for d in valid_deg)
    cos_sum = sum(math.cos(math.radians(d)) for d in valid_deg)
    if math.isclose(sin_sum, 0.0, abs_tol=1e-7) and math.isclose(cos_sum, 0.0, abs_tol=1e-7):
        return 0.0
    mean_rad = math.atan2(sin_sum, cos_sum)
    mean_deg = math.degrees(mean_rad) % 360.0
    return round(mean_deg, 1) % 360.0


class HourlyAggregationEngine:
    AGGREGATION_VERSION = "1.0.0"

    @classmethod
    async def process_hour(
        cls,
        db: AsyncSession,
        campus_id: str,
        station_id: str,
        source: str,
        hour_start: datetime
    ) -> HourlyObservation:
        """Aggregates raw observations for a single UTC hour into an HourlyObservation record."""
        # Ensure hour_start is floor of hour
        hour_start_utc = hour_start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        hour_end_utc = hour_start_utc + timedelta(hours=1)

        # Query observations in [hour_start_utc, hour_end_utc)
        stmt = select(Observation).where(
            and_(
                Observation.station_id == station_id,
                Observation.source == source,
                Observation.observed_at >= hour_start_utc,
                Observation.observed_at < hour_end_utc
            )
        )
        result = await db.execute(stmt)
        obs_list = result.scalars().all()

        station = await db.get(Station, station_id)
        sampling_interval = station.sampling_interval_seconds if station else 60
        expected_count = max(1, 3600 // sampling_interval)
        contributing_count = len(obs_list)
        completeness_pct = round((contributing_count / expected_count) * 100.0, 1)

        if not obs_list:
            # Empty hour
            hourly_obs = HourlyObservation(
                campus_id=campus_id,
                station_id=station_id,
                source=source,
                hour_start=hour_start_utc,
                expected_count=expected_count,
                contributing_count=0,
                completeness_pct=0.0,
                is_model_eligible=False,
                eligibility_reason="zero_contributing_observations",
                aggregation_version=cls.AGGREGATION_VERSION
            )
            return hourly_obs

        # Extract values
        pm1_vals = [o.pm1 for o in obs_list if o.pm1 is not None]
        pm25_vals = [o.pm2_5 for o in obs_list if o.pm2_5 is not None]
        pm10_vals = [o.pm10 for o in obs_list if o.pm10 is not None]
        temp_vals = [o.temperature_c for o in obs_list if o.temperature_c is not None]
        hum_vals = [o.humidity_pct for o in obs_list if o.humidity_pct is not None]
        press_vals = [o.pressure_hpa for o in obs_list if o.pressure_hpa is not None]
        rain_vals = [o.rain_flag for o in obs_list if o.rain_flag is not None]
        wind_spd_vals = [o.wind_speed_m_s for o in obs_list if o.wind_speed_m_s is not None]
        wind_dir_vals = [o.wind_direction_deg for o in obs_list if o.wind_direction_deg is not None]
        quality_scores = [o.quality_score for o in obs_list if o.quality_score is not None]

        def calc_mean(vals): return round(sum(vals) / len(vals), 2) if vals else None
        def calc_median(vals):
            if not vals: return None
            s = sorted(vals)
            n = len(s)
            return round(s[n//2] if n % 2 == 1 else (s[n//2-1] + s[n//2]) / 2.0, 2)

        pm1_mean = calc_mean(pm1_vals)
        pm25_mean = calc_mean(pm25_vals)
        pm25_median = calc_median(pm25_vals)
        pm10_mean = calc_mean(pm10_vals)
        pm10_median = calc_median(pm10_vals)
        temp_mean = calc_mean(temp_vals)
        hum_mean = calc_mean(hum_vals)
        press_mean = calc_mean(press_vals)
        rain_detected = any(rain_vals) if rain_vals else False
        rain_fraction = round(sum(1 for r in rain_vals if r) / len(rain_vals), 2) if rain_vals else 0.0
        wind_spd_mean = calc_mean(wind_spd_vals)
        wind_dir_circ = calculate_circular_wind_mean(wind_dir_vals)
        avg_quality = calc_mean(quality_scores) or 1.0
        high_hum_count = sum(1 for h in hum_vals if h > 90.0)
        high_hum_frac = round(high_hum_count / len(hum_vals), 2) if hum_vals else 0.0

        is_eligible = completeness_pct >= 75.0 and avg_quality >= 0.60
        eligibility_reason = "sufficient_completeness" if is_eligible else "low_completeness_or_quality"

        # Check existing
        stmt_exist = select(HourlyObservation).where(
            and_(
                HourlyObservation.station_id == station_id,
                HourlyObservation.source == source,
                HourlyObservation.hour_start == hour_start_utc
            )
        )
        res_exist = await db.execute(stmt_exist)
        existing = res_exist.scalar_one_or_none()

        if existing:
            existing.pm1_mean = pm1_mean
            existing.pm2_5_mean = pm25_mean
            existing.pm2_5_median = pm25_median
            existing.pm10_mean = pm10_mean
            existing.pm10_median = pm10_median
            existing.temperature_mean = temp_mean
            existing.humidity_mean = hum_mean
            existing.pressure_mean = press_mean
            existing.rain_detected = rain_detected
            existing.rain_fraction = rain_fraction
            existing.wind_speed_mean = wind_spd_mean
            existing.wind_direction_circular_mean = wind_dir_circ
            existing.contributing_count = contributing_count
            existing.expected_count = expected_count
            existing.completeness_pct = completeness_pct
            existing.average_quality_score = avg_quality
            existing.high_humidity_fraction = high_hum_frac
            existing.is_model_eligible = is_eligible
            existing.eligibility_reason = eligibility_reason
            return existing
        else:
            hourly_obs = HourlyObservation(
                campus_id=campus_id,
                station_id=station_id,
                source=source,
                hour_start=hour_start_utc,
                pm1_mean=pm1_mean,
                pm2_5_mean=pm25_mean,
                pm2_5_median=pm25_median,
                pm10_mean=pm10_mean,
                pm10_median=pm10_median,
                temperature_mean=temp_mean,
                humidity_mean=hum_mean,
                pressure_mean=press_mean,
                rain_detected=rain_detected,
                rain_fraction=rain_fraction,
                wind_speed_mean=wind_spd_mean,
                wind_direction_circular_mean=wind_dir_circ,
                contributing_count=contributing_count,
                expected_count=expected_count,
                completeness_pct=completeness_pct,
                average_quality_score=avg_quality,
                high_humidity_fraction=high_hum_frac,
                is_model_eligible=is_eligible,
                eligibility_reason=eligibility_reason,
                aggregation_version=cls.AGGREGATION_VERSION
            )
            db.add(hourly_obs)
            return hourly_obs


    @classmethod
    async def interpolate_short_gaps(
        cls,
        db: AsyncSession,
        station_id: str,
        source: str,
        start_hour: datetime,
        end_hour: datetime
    ) -> int:
        """Applies controlled linear interpolation to short missing hourly gaps (max 2 consecutive missing hours)."""
        stmt = select(HourlyObservation).where(
            and_(
                HourlyObservation.station_id == station_id,
                HourlyObservation.source == source,
                HourlyObservation.hour_start >= start_hour,
                HourlyObservation.hour_start <= end_hour
            )
        ).order_by(HourlyObservation.hour_start.asc())
        result = await db.execute(stmt)
        records = result.scalars().all()

        if len(records) < 3:
            return 0

        interpolated_count = 0
        for i in range(1, len(records) - 1):
            curr = records[i]
            prev_rec = records[i - 1]
            next_rec = records[i + 1]

            # Condition: current hour is missing data, but previous and next hours are present
            if curr.contributing_count == 0 and prev_rec.contributing_count > 0 and next_rec.contributing_count > 0:
                # Interpolate PM2.5, PM10, Temperature, Humidity
                if prev_rec.pm2_5_mean is not None and next_rec.pm2_5_mean is not None:
                    curr.pm2_5_mean = round((prev_rec.pm2_5_mean + next_rec.pm2_5_mean) / 2.0, 2)
                if prev_rec.pm10_mean is not None and next_rec.pm10_mean is not None:
                    curr.pm10_mean = round((prev_rec.pm10_mean + next_rec.pm10_mean) / 2.0, 2)
                if prev_rec.temperature_mean is not None and next_rec.temperature_mean is not None:
                    curr.temperature_mean = round((prev_rec.temperature_mean + next_rec.temperature_mean) / 2.0, 2)
                if prev_rec.humidity_mean is not None and next_rec.humidity_mean is not None:
                    curr.humidity_mean = round((prev_rec.humidity_mean + next_rec.humidity_mean) / 2.0, 2)

                curr.has_interpolation = True
                curr.average_quality_score = round(min(prev_rec.average_quality_score, next_rec.average_quality_score) * 0.90, 2)
                curr.is_model_eligible = True
                curr.eligibility_reason = "linear_interpolated_short_gap"
                interpolated_count += 1

        await db.commit()
        return interpolated_count

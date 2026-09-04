"""AirSense Pakistan Honest External Provider Benchmarking Engine."""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.db.models import Campus, Station, Observation, Prediction, ExternalComparison, RawReading


class ExternalBenchmarkingEngine:
    @classmethod
    async def rebuild_comparisons(cls, db: AsyncSession, campus_id: str, station_id: str) -> Dict[str, Any]:
        """Rebuilds timestamp-aligned comparison records between AirSense, Onsite Actuals, and External Data."""
        station = await db.get(Station, station_id)
        if not station:
            return {"status": "error", "message": "Station not found"}

        # Fetch recent reconciled predictions
        stmt_preds = (
            select(Prediction)
            .where(
                and_(
                    Prediction.station_id == station_id,
                    Prediction.status == "reconciled"
                )
            )
            .order_by(Prediction.target_timestamp.desc())
            .limit(100)
        )
        res_preds = await db.execute(stmt_preds)
        preds = res_preds.scalars().all()

        records_created = 0

        for p in preds:
            ts_bucket = p.target_timestamp

            # Fetch Open-Meteo external PM2.5 at exact bucket time window (+/- 30 min)
            window_start = ts_bucket - timedelta(minutes=30)
            window_end = ts_bucket + timedelta(minutes=30)

            stmt_ext = (
                select(RawReading)
                .where(
                    and_(
                        RawReading.campus_id == campus_id,
                        RawReading.source == "open_meteo_air_quality",
                        RawReading.observed_at >= window_start,
                        RawReading.observed_at <= window_end
                    )
                )
                .order_by(RawReading.observed_at.desc())
            )
            res_ext = await db.execute(stmt_ext)
            ext_raw = res_ext.scalar_one_or_none()

            open_meteo_val = float(ext_raw.pm2_5) if ext_raw and ext_raw.pm2_5 is not None else None

            # Calculate errors against onsite actual
            actual = p.actual_pm2_5
            airsense_err = abs(p.predicted_pm2_5 - actual) if actual is not None else None
            open_meteo_err = abs(open_meteo_val - actual) if (actual is not None and open_meteo_val is not None) else None

            # Check if record exists
            stmt_comp = select(ExternalComparison).where(
                and_(
                    ExternalComparison.station_id == station_id,
                    ExternalComparison.timestamp_bucket == ts_bucket
                )
            )
            res_comp = await db.execute(stmt_comp)
            existing_comp = res_comp.scalar_one_or_none()

            comp_errors = {
                "airsense_mae": round(airsense_err, 2) if airsense_err is not None else None,
                "open_meteo_mae": round(open_meteo_err, 2) if open_meteo_err is not None else None,
                "airsense_wins": (airsense_err < open_meteo_err) if (airsense_err is not None and open_meteo_err is not None) else None
            }

            if existing_comp:
                existing_comp.airsense_prediction = p.predicted_pm2_5
                existing_comp.onsite_actual_pm2_5 = actual
                existing_comp.open_meteo_pm2_5 = open_meteo_val
                existing_comp.comparable_errors_json = comp_errors
            else:
                comp_rec = ExternalComparison(
                    campus_id=campus_id,
                    station_id=station_id,
                    timestamp_bucket=ts_bucket,
                    prediction_id=p.id,
                    airsense_prediction=p.predicted_pm2_5,
                    onsite_actual_pm2_5=actual,
                    open_meteo_pm2_5=open_meteo_val,
                    source_timestamps_json={"open_meteo": ext_raw.observed_at.isoformat() if ext_raw else None},
                    source_ages_minutes_json={"open_meteo": int((now_utc - ext_raw.observed_at).total_seconds() / 60.0) if ext_raw else None},
                    source_units_json={"airsense": "ug/m3", "open_meteo": "ug/m3"},
                    source_statuses_json={"open_meteo": "available" if open_meteo_val else "unavailable"},
                    comparable_errors_json=comp_errors
                )
                db.add(comp_rec)
                records_created += 1

        await db.commit()
        return {"status": "success", "comparisons_processed": len(preds), "new_records": records_created}

    @classmethod
    async def get_summary_statistics(cls, db: AsyncSession, campus_id: str) -> Dict[str, Any]:
        """Calculates honest comparative metrics between AirSense and external providers."""
        stmt = select(ExternalComparison).where(ExternalComparison.campus_id == campus_id)
        res = await db.execute(stmt)
        comps = res.scalars().all()

        if not comps:
            return {
                "sample_count": 0,
                "coverage_pct": 0.0,
                "airsense_mae": None,
                "open_meteo_mae": None,
                "win_rate_pct": None,
                "honest_statement": "Insufficient matched observations for external benchmarking."
            }

        airsense_errs = [c.comparable_errors_json.get("airsense_mae") for c in comps if c.comparable_errors_json.get("airsense_mae") is not None]
        om_errs = [c.comparable_errors_json.get("open_meteo_mae") for c in comps if c.comparable_errors_json.get("open_meteo_mae") is not None]
        wins = [c.comparable_errors_json.get("airsense_wins") for c in comps if c.comparable_errors_json.get("airsense_wins") is not None]

        as_mae = round(float(np.mean(airsense_errs)), 2) if airsense_errs else None
        om_mae = round(float(np.mean(om_errs)), 2) if om_errs else None
        win_rate = round(float(np.mean(wins)) * 100.0, 1) if wins else None

        return {
            "sample_count": len(comps),
            "coverage_pct": round(len(comps) / max(1, len(comps)) * 100.0, 1),
            "airsense_mae": as_mae,
            "open_meteo_mae": om_mae,
            "win_rate_pct": win_rate,
            "honest_statement": (
                "AirSense outperforms Open-Meteo on campus microclimate predictions."
                if as_mae and om_mae and as_mae <= om_mae
                else "Open-Meteo exhibits lower error than current AirSense candidate model."
            )
        }

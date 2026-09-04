"""TimescaleDB query layer — all time-series data operations."""
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from app.core.config import settings
import structlog

log = structlog.get_logger()

DSN = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

async def get_conn():
    return await asyncpg.connect(DSN)

async def insert_measurement(m: dict) -> bool:
    """Insert a single normalized measurement."""
    conn = await get_conn()
    try:
        await conn.execute("""
            INSERT INTO measurements (
                timestamp, city, station_id, source,
                pm25, pm10, no2, so2, co, o3, nh3,
                aqi, temperature, humidity, wind_speed, wind_direction, pressure,
                aod, no2_col, fire_radiative_power,
                lat, lon, data_quality_score, pm25_flagged
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,
                $12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24
            ) ON CONFLICT DO NOTHING
        """,
            m.get("timestamp", datetime.utcnow()),
            m.get("city", "lahore"),
            m.get("station_id") or m.get("station"),
            m.get("source", "unknown"),
            m.get("pm25"), m.get("pm10"), m.get("no2"),
            m.get("so2"), m.get("co"), m.get("o3"), m.get("nh3"),
            m.get("aqi"),
            m.get("temperature"), m.get("humidity"),
            m.get("wind_speed"), m.get("wind_direction"), m.get("pressure"),
            m.get("aod"), m.get("no2_col"), m.get("fire_radiative_power"),
            m.get("lat"), m.get("lon"),
            m.get("data_quality_score", 1.0),
            m.get("pm25_flagged", False),
        )
        return True
    except Exception as e:
        log.error("insert_measurement_failed", error=str(e))
        return False
    finally:
        await conn.close()

async def bulk_insert_measurements(records: List[dict]) -> int:
    """Bulk insert for historical data loads."""
    if not records:
        return 0
    conn = await get_conn()
    try:
        rows = [
            (
                r.get("timestamp", datetime.utcnow()),
                r.get("city", "lahore"),
                r.get("station_id") or r.get("station"),
                r.get("source", "unknown"),
                r.get("pm25"), r.get("pm10"), r.get("no2"),
                r.get("so2"), r.get("co"), r.get("o3"),
                r.get("aqi"), r.get("temperature"), r.get("humidity"),
                r.get("wind_speed"), r.get("wind_direction"),
                r.get("lat"), r.get("lon"),
                r.get("data_quality_score", 1.0),
            )
            for r in records
        ]
        await conn.copy_records_to_table(
            "measurements",
            records=rows,
            columns=["timestamp","city","station_id","source",
                     "pm25","pm10","no2","so2","co","o3",
                     "aqi","temperature","humidity","wind_speed","wind_direction",
                     "lat","lon","data_quality_score"]
        )
        return len(rows)
    except Exception as e:
        log.error("bulk_insert_failed", error=str(e))
        return 0
    finally:
        await conn.close()

async def get_current_aqi(city: str, station_id: Optional[str] = None) -> List[dict]:
    conn = await get_conn()
    try:
        if station_id:
            rows = await conn.fetch("""
                SELECT * FROM latest_station_readings
                WHERE city=$1 AND station_id=$2
            """, city, station_id)
        else:
            rows = await conn.fetch("""
                SELECT * FROM latest_station_readings WHERE city=$1
            """, city)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_city_summary(city: str) -> dict:
    conn = await get_conn()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM city_current_summary WHERE city=$1", city
        )
        return dict(row) if row else {}
    finally:
        await conn.close()

async def get_historical(
    city: str, start: datetime, end: datetime,
    parameter: str = "aqi", aggregation: str = "hourly",
    station_id: Optional[str] = None
) -> List[dict]:
    conn = await get_conn()
    try:
        agg_map = {
            "raw": "measurements",
            "hourly": "measurements_hourly",
            "daily": "measurements_daily",
        }
        table = agg_map.get(aggregation, "measurements_hourly")
        time_col = {"raw": "timestamp", "hourly": "hour", "daily": "day"}.get(aggregation, "hour")

        query = f"""
            SELECT {time_col} as time, city, station_id,
                   COALESCE({parameter}, 0) as value
            FROM {table}
            WHERE city=$1 AND {time_col} BETWEEN $2 AND $3
            {"AND station_id=$4" if station_id else ""}
            ORDER BY {time_col} ASC
        """
        args = [city, start, end]
        if station_id:
            args.append(station_id)
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def get_measurements_for_training(city: str, days: int = 90) -> List[dict]:
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT timestamp, city, station_id,
                   pm25, pm10, no2, so2, co, o3,
                   aqi, temperature, humidity,
                   wind_speed, wind_direction, pressure,
                   data_quality_score
            FROM measurements
            WHERE city=$1
              AND timestamp > NOW() - ($2 || ' days')::INTERVAL
              AND data_quality_score >= 0.5
            ORDER BY timestamp ASC
        """, city, str(days))
        return [dict(r) for r in rows]
    finally:
        await conn.close()

async def count_new_records_since_last_train(city: str = "lahore") -> int:
    conn = await get_conn()
    try:
        last_train = await conn.fetchval("""
            SELECT completed_at FROM ml_training_log
            WHERE city=$1 AND status='success' AND promoted=TRUE
            ORDER BY completed_at DESC LIMIT 1
        """, city)
        if not last_train:
            last_train = datetime.utcnow() - timedelta(days=7)
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM measurements
            WHERE city=$1 AND timestamp > $2
        """, city, last_train)
        return count or 0
    finally:
        await conn.close()

async def log_ingestion(source: str, city: str, fetched: int,
                        inserted: int, duration_ms: int,
                        status: str = "success", error: str = None):
    conn = await get_conn()
    try:
        await conn.execute("""
            INSERT INTO ingestion_log
                (source, city, records_fetched, records_inserted, duration_ms, status, error_message)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
        """, source, city, fetched, inserted, duration_ms, status, error)
    finally:
        await conn.close()

async def save_predictions(city: str, model_name: str, model_version: str,
                           predictions: List[dict], horizon_hours: int):
    conn = await get_conn()
    try:
        now = datetime.utcnow()
        rows = [
            (now, city, model_name, model_version,
             p["prediction_for"], p.get("predicted_aqi"),
             p.get("predicted_pm25"), p.get("confidence"), horizon_hours)
            for p in predictions
        ]
        await conn.copy_records_to_table(
            "predictions",
            records=rows,
            columns=["timestamp","city","model_name","model_version",
                     "prediction_for","predicted_aqi","predicted_pm25",
                     "confidence","horizon_hours"]
        )
    finally:
        await conn.close()

async def get_pipeline_health() -> List[dict]:
    conn = await get_conn()
    try:
        rows = await conn.fetch("SELECT * FROM pipeline_health")
        return [dict(r) for r in rows]
    finally:
        await conn.close()

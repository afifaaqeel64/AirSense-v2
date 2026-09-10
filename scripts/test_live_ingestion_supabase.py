"""Verification script: Ingest live reading and query Supabase database."""

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from apps.api.main import app
from apps.api.db.session import engine
from apps.api.db.models import RawReading, QualityAssessment, Observation, Station, Device


async def test_ingest_and_query():
    print("[Verification] Starting Supabase live telemetry ingestion and query test...")
    
    # 1. Verify connection to Supabase
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT count(*) FROM stations;"))
        st_count = res.scalar()
        print(f"[Verification] Connected to Supabase. Existing stations count: {st_count}")
        assert st_count >= 1, "Expected at least 1 station in Supabase"

    # 2. Perform ingestion via ASGI test client using the seeded device token
    token = "airsense_dev_token_khi_01"
    now_iso = datetime.now(timezone.utc).isoformat()
    seq_no = int(datetime.now(timezone.utc).timestamp())
    
    payload = {
        "schema_version": "1.0",
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "timestamp": now_iso,
        "pm1": 8.5,
        "pm2_5": 18.2,
        "pm10": 29.0,
        "temperature": 27.8,
        "humidity": 61.5,
        "pressure": 1012.3,
        "rain_flag": False,
        "sequence_number": seq_no
    }
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        resp = await client.post("/api/v1/ingest/reading", json=payload, headers=headers)
        print(f"[Verification] Ingest response status: {resp.status_code}")
        print(f"[Verification] Ingest response payload: {resp.json()}")
        assert resp.status_code == 200, f"Expected status 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        reading_id = data.get("raw_reading_id") or data.get("ingestion_id")
        print(f"[Verification] Ingestion accepted successfully. Reading ID: {reading_id}")

    # 3. Query the ingested record directly from Supabase via SQLAlchemy session
    async with engine.connect() as conn:
        async with AsyncSession(conn) as session:
            # Query RawReading
            q_raw = await session.execute(
                select(RawReading).where(RawReading.id == reading_id)
            )
            raw = q_raw.scalar_one_or_none()
            assert raw is not None, "Raw reading not found in Supabase"
            print(f"[Verification] Found RawReading in Supabase:")
            print(f"  ID: {raw.id}")
            print(f"  Station: {raw.station_id}")
            print(f"  PM2.5: {raw.pm2_5} µg/m³")
            print(f"  Temperature: {raw.temperature_c} °C")
            print(f"  Humidity: {raw.humidity_pct} %")

            # Query QualityAssessment
            q_qc = await session.execute(
                select(QualityAssessment).where(QualityAssessment.raw_reading_id == reading_id)
            )
            qc = q_qc.scalar_one_or_none()
            assert qc is not None, "Quality assessment not found in Supabase"
            print(f"[Verification] Found QualityAssessment in Supabase: status={qc.quality_status}, score={qc.quality_score}")

            # Query Observation
            q_obs = await session.execute(
                select(Observation).where(Observation.raw_reading_id == reading_id)
            )
            obs = q_obs.scalar_one_or_none()
            assert obs is not None, "Observation not found in Supabase"
            print(f"[Verification] Found Observation in Supabase: PM2.5={obs.pm2_5}, AQI={obs.aqi}")

    print("\n[Verification] ALL INGESTION & QUERY CHECKS PASSED ON SUPABASE!")


if __name__ == "__main__":
    asyncio.run(test_ingest_and_query())

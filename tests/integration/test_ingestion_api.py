"""Integration tests for Live ESP32 Telemetry Ingestion, Device Auth, and Idempotency."""

import pytest
from httpx import AsyncClient, ASGITransport
from apps.api.main import app
from apps.api.core.config import settings
from apps.api.core.security import generate_secure_token, hash_token
from apps.api.db.session import engine
from apps.api.db.models import Base, Campus, Station, Device
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text


@pytest.fixture(autouse=True)
async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.connect() as conn:
        async with AsyncSession(conn) as session:
            await session.execute(text("DELETE FROM hourly_observations"))
            await session.execute(text("DELETE FROM observations"))
            await session.execute(text("DELETE FROM quality_assessments"))
            await session.execute(text("DELETE FROM raw_readings"))
            await session.execute(text("DELETE FROM devices"))
            await session.execute(text("DELETE FROM stations"))
            await session.execute(text("DELETE FROM campuses"))
            await session.commit()

            campus = Campus(
                code="ISB_CAMPUS",
                name="Islamabad Campus",
                city="Islamabad",
                contact_name="Muhammad M. Qureshi",
                status="configuration_required"
            )
            session.add(campus)
            await session.flush()

            station = Station(
                campus_id=campus.id,
                station_code="ISB-CAMPUS-01",
                station_name="Islamabad Main Station",
                installation_location="Rooftop"
            )
            session.add(station)
            await session.flush()

            raw_token = "airsense_dev_test_token_12345"
            token_h = hash_token(raw_token)

            device = Device(
                station_id=station.id,
                device_uid="ISB-ROOF-01",
                token_hash=token_h,
                status="active"
            )
            session.add(device)
            await session.commit()


@pytest.mark.asyncio
async def test_live_ingestion_valid_token():
    raw_token = "airsense_dev_test_token_12345"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "schema_version": "1.0",
            "device_uid": "ISB-ROOF-01",
            "station_code": "ISB-CAMPUS-01",
            "timestamp": "2026-07-27T12:00:00Z",
            "pm1": 12.0,
            "pm2_5": 25.5,
            "pm10": 40.0,
            "temperature": 28.5,
            "humidity": 55.0,
            "sequence_number": 1
        }
        headers = {"Authorization": f"Bearer {raw_token}"}
        response = await client.post("/api/v1/ingest/reading", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True
        assert data["duplicate"] is False
        assert data["station_code"] == "ISB-CAMPUS-01"


@pytest.mark.asyncio
async def test_live_ingestion_idempotency_duplicate():
    raw_token = "airsense_dev_test_token_12345"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "schema_version": "1.0",
            "device_uid": "ISB-ROOF-01",
            "station_code": "ISB-CAMPUS-01",
            "timestamp": "2026-07-27T12:00:00Z",
            "pm2_5": 25.5,
            "temperature": 28.5,
            "sequence_number": 1
        }
        headers = {"X-Device-Token": raw_token}
        # First submission
        resp1 = await client.post("/api/v1/ingest/reading", json=payload, headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["duplicate"] is False

        # Duplicate submission
        resp2 = await client.post("/api/v1/ingest/reading", json=payload, headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["duplicate"] is True
        assert resp2.json()["quality_processing_state"] == "duplicate_skipped"


@pytest.mark.asyncio
async def test_live_ingestion_invalid_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"pm2_5": 20.0}
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.post("/api/v1/ingest/reading", json=payload, headers=headers)
        assert response.status_code == 401

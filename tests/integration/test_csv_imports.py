"""Integration tests for Two-Stage CSV Import Pipeline."""

import pytest
import io
from httpx import AsyncClient, ASGITransport
from apps.api.main import app
from apps.api.db.session import engine
from apps.api.db.models import Base, Campus, Station
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


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
            await session.execute(text("DELETE FROM import_batches"))
            await session.execute(text("DELETE FROM devices"))
            await session.execute(text("DELETE FROM stations"))
            await session.execute(text("DELETE FROM campuses"))
            await session.commit()

            campus = Campus(code="ISB_CAMPUS", name="Islamabad Campus", city="Islamabad", contact_name="Muhammad M. Qureshi")
            session.add(campus)
            await session.flush()
            station = Station(campus_id=campus.id, station_code="ISB-CAMPUS-01", station_name="Islamabad Station")
            session.add(station)
            await session.commit()


@pytest.mark.asyncio
async def test_csv_import_preview_and_commit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Fetch campus & station IDs
        campuses_res = await client.get("/api/v1/campuses")
        campus_id = campuses_res.json()[0]["id"]
        stations_res = await client.get("/api/v1/stations")
        station_id = stations_res.json()[0]["id"]

        # 1. Preview
        csv_data = "timestamp,pm2_5,temperature,humidity\n2026-07-27T10:00:00Z,35.0,29.0,50.0\n2026-07-27T11:00:00Z,40.0,30.0,52.0\n"
        files = {"file": ("test_readings.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
        data = {"campus_id": campus_id, "station_id": station_id}

        preview_res = await client.post("/api/v1/imports/csv/preview", data=data, files=files)
        assert preview_res.status_code == 200
        p_data = preview_res.json()
        assert p_data["total_rows"] == 2
        assert p_data["proposed_mapping"]["pm2_5"] == "pm2_5"
        batch_id = p_data["batch_id"]

        # 2. Commit
        commit_payload = {
            "batch_id": batch_id,
            "confirmed_mapping": p_data["proposed_mapping"],
            "confirmed_timezone": "Asia/Karachi"
        }
        commit_res = await client.post("/api/v1/imports/csv/commit", json=commit_payload)
        assert commit_res.status_code == 200
        c_data = commit_res.json()
        assert c_data["status"] == "committed"
        assert c_data["rows_committed"] == 2

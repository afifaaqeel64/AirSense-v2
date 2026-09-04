"""Integration tests for Phase 5 End-to-End Forecasting Pipeline."""

import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from apps.api.main import app
from apps.api.core.config import settings
from apps.api.db.session import engine
from apps.api.db.models import Base, Campus, Station, HourlyObservation, ModelRun, Prediction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text


@pytest.fixture(autouse=True)
async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.connect() as conn:
        async with AsyncSession(conn) as session:
            await session.execute(text("DELETE FROM predictions"))
            await session.execute(text("DELETE FROM model_runs"))
            await session.execute(text("DELETE FROM hourly_observations"))
            await session.execute(text("DELETE FROM observations"))
            await session.execute(text("DELETE FROM quality_assessments"))
            await session.execute(text("DELETE FROM raw_readings"))
            await session.execute(text("DELETE FROM devices"))
            await session.execute(text("DELETE FROM stations"))
            await session.execute(text("DELETE FROM campuses"))
            await session.commit()

            campus = Campus(code="ISB_CAMPUS", name="Islamabad Campus", city="Islamabad", contact_name="Muhammad M. Qureshi")
            session.add(campus)
            await session.flush()

            station = Station(campus_id=campus.id, station_code="ISB-CAMPUS-01", station_name="Islamabad Station")
            session.add(station)
            await session.flush()

            # Seed 30 hourly observations
            base_ts = datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
            for i in range(30):
                obs = HourlyObservation(
                    campus_id=campus.id,
                    station_id=station.id,
                    source="onsite_esp32",
                    hour_start=base_ts + timedelta(hours=i),
                    pm1_mean=15.0 + (i % 5),
                    pm2_5_mean=30.0 + (i % 10),
                    pm10_mean=45.0 + (i % 15),
                    temperature_mean=25.0,
                    humidity_mean=50.0,
                    pressure_mean=1013.25,
                    rain_detected=False,
                    wind_speed_mean=2.0,
                    wind_direction_circular_mean=90.0,
                    completeness_pct=100.0,
                    is_model_eligible=True
                )
                session.add(obs)
            await session.commit()


@pytest.mark.asyncio
async def test_training_and_forecast_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        campuses_res = await client.get("/api/v1/campuses")
        campus_id = campuses_res.json()[0]["id"]
        stations_res = await client.get("/api/v1/stations")
        station_id = stations_res.json()[0]["id"]

        # 1. Trigger Persistence training (requires 25 observations, we seeded 30)
        train_payload = {
            "campus_id": campus_id,
            "station_id": station_id,
            "model_family": "persistence",
            "forecast_horizon_hours": 1
        }
        train_res = await client.post("/api/v1/models/train", json=train_payload)
        assert train_res.status_code == 200, train_res.text
        t_data = train_res.json()
        assert t_data["status"] == "succeeded", f"Training status failed: {t_data}"
        run_id = t_data["run_id"]

        # 2. Promote model to production
        token = settings.ADMIN_API_TOKEN
        headers = {"X-Admin-Token": token}
        promote_res = await client.post(f"/api/v1/models/{run_id}/promote", json={"reason": "Test promotion"}, headers=headers)
        assert promote_res.status_code == 200, promote_res.text
        assert promote_res.json()["is_production"] is True

        # 3. Generate Forecast
        fc_res = await client.post("/api/v1/forecasts/run", json={"campus_id": campus_id, "station_id": station_id, "forecast_horizon_hours": 1})
        fc_data = fc_res.json()
        assert fc_res.status_code == 200, f"Forecast response failed: {fc_data}"
        assert fc_data["status"] == "succeeded", f"Forecast status failed: {fc_data}"
        assert "predicted_pm2_5" in fc_data
        assert "ci_lower" in fc_data
        assert "ci_upper" in fc_data

        # 4. Safe Code Lab Inference Test
        inf_payload = {
            "run_id": run_id,
            "feature_values": {"pm2_5_lag_1": 42.0, "temperature_c": 28.0}
        }
        inf_res = await client.post("/api/v1/inference/run", json=inf_payload)
        assert inf_res.status_code == 200, inf_res.text
        inf_data = inf_res.json()
        assert inf_data["predicted_pm2_5"] == 42.0

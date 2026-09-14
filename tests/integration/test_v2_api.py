"""Integration tests for AirSense v2 Operational Decision Intelligence Endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from apps.api.main import app


@pytest.mark.asyncio
async def test_v2_live_decisions_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/decisions/live?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        assert "risk_tier" in data
        assert "primary_directive" in data
        assert "confidence_pct" in data
        assert "active_triggers" in data


@pytest.mark.asyncio
async def test_v2_sectors_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. All sectors summary
        res = await client.get("/api/v2/sectors?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        assert data["total_sectors"] == 6
        assert len(data["sectors"]) == 6

        # 2. Individual sector detail
        for sec in ["education", "healthcare", "hvac", "municipal", "industrial", "agriculture"]:
            s_res = await client.get(f"/api/v2/sectors/{sec}?campus_code=KARACHI")
            assert s_res.status_code == 200
            s_data = s_res.json()
            assert s_data["sector_id"] == sec
            assert "primary_action" in s_data
            assert "kpis" in s_data
            assert "actuators" in s_data


@pytest.mark.asyncio
async def test_v2_alerts_and_news_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Alerts
        alt_res = await client.get("/api/v2/alerts?campus_code=KARACHI")
        assert alt_res.status_code == 200
        alt_data = alt_res.json()
        assert "alerts" in alt_data
        if alt_data["alerts"]:
            first_alert_id = alt_data["alerts"][0]["id"]
            ack_res = await client.post(f"/api/v2/alerts/{first_alert_id}/acknowledge")
            assert ack_res.status_code == 200
            assert ack_res.json()["status"] == "ACKNOWLEDGED"

        # News
        news_res = await client.get("/api/v2/news")
        assert news_res.status_code == 200
        news_data = news_res.json()
        assert news_data["total_articles"] >= 3

        # Weather
        wx_res = await client.get("/api/v2/weather/live?campus_code=KARACHI")
        assert wx_res.status_code == 200
        wx_data = wx_res.json()
        assert "temperature_c" in wx_data
        assert "humidity_pct" in wx_data
        assert "wind_speed_m_s" in wx_data


@pytest.mark.asyncio
async def test_v2_actuator_trigger_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "sector_id": "hvac",
            "actuator_name": "Main Air Handling Unit (AHU-1)",
            "target_state": "DAMPER_10%_BOOST_HEPA",
            "reason": "Integration Test Automated Directive"
        }
        res = await client.post("/api/v2/actuators/trigger", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert data["applied_state"] == "DAMPER_10%_BOOST_HEPA"


@pytest.mark.asyncio
async def test_both_dashboards_served():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # v1 Ops Dashboard
        v1_res = await client.get("/ops")
        assert v1_res.status_code == 200

        # v2 Command Centre
        v2_res = await client.get("/command")
        assert v2_res.status_code == 200

        v2_alias = await client.get("/ops-v2")
        assert v2_alias.status_code == 200

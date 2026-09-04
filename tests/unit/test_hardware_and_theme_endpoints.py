"""Unit tests for Hardware status, Minute History, CSV Export, GIS Mesh, and Copilot Endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from apps.api.main import app


@pytest.mark.asyncio
async def test_hardware_status_disconnected_flow():
    """Validates that hardware status endpoint correctly returns disconnected status and preserved telemetry."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/hardware/status")
        assert res.status_code == 200
        data = res.json()
        assert "is_connected" in data
        assert "station_code" in data
        assert "sensors" in data
        assert "latest_telemetry" in data
        assert data["latest_telemetry"]["pm2_5"] >= 0.0
        assert data["latest_telemetry"]["temperature_c"] is not None


@pytest.mark.asyncio
async def test_minute_history_endpoint():
    """Validates that minute history returns rows with meteorological summary narrative."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/hardware/minute-history?limit=10")
        assert res.status_code == 200
        rows = res.json()
        assert len(rows) > 0
        first = rows[0]
        assert "timestamp_utc" in first
        assert "pm2_5" in first
        assert "meteorological_summary" in first
        assert len(first["meteorological_summary"]) > 10


@pytest.mark.asyncio
async def test_minute_csv_export_endpoint():
    """Validates CSV export streaming with correct headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/hardware/minute-export.csv")
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("content-type", "")
        content = res.text
        assert "timestamp_utc" in content
        assert "pm2_5_ug_m3" in content
        assert "meteorological_summary" in content


@pytest.mark.asyncio
async def test_gis_mesh_endpoint():
    """Validates GIS spatial mesh returns onsite and open-source nodes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/hardware/open-source-mesh")
        assert res.status_code == 200
        nodes = res.json()
        assert len(nodes) >= 4
        types = [n["type"] for n in nodes]
        assert "onsite_ground_truth" in types
        assert "open_source_model" in types


@pytest.mark.asyncio
async def test_copilot_chat_endpoint():
    """Validates AI copilot grounded responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {"message": "Can students play outdoor sports?"}
        res = await ac.post("/api/v1/copilot/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "reply" in data
        assert "grounded_telemetry" in data
        assert "PM2.5" in data["reply"] or "Optimal" in data["reply"]

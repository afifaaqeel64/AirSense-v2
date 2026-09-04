import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    r = await client.get("/")
    assert r.status_code == 200
    assert "AirSense" in r.json()["name"]

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["version"]

@pytest.mark.asyncio
async def test_current_aqi_endpoint(client: AsyncClient):
    r = await client.get("/api/v1/aqi/current/lahore")
    assert r.status_code == 200
    data = r.json()
    assert data["city"] == "lahore"

@pytest.mark.asyncio
async def test_stations_endpoint(client: AsyncClient):
    r = await client.get("/api/v1/stations/lahore")
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_forecast_endpoint(client: AsyncClient):
    r = await client.get("/api/v1/aqi/forecast/lahore?hours=24")
    assert r.status_code == 200
    data = r.json()
    assert "forecast" in data

"""Unit and Integration Tests for AirSense Multi-Provider Weather & Atmospheric Engine."""

import pytest
from httpx import AsyncClient, ASGITransport
from apps.api.main import app
from services.external_providers.wmo_models import (
    WMO_CODE_REGISTRY,
    get_wmo_metadata,
    StandardizedWeatherResponse
)
from services.external_providers.weatherapi_provider import (
    WeatherAPIProvider,
    weatherapi_condition_to_wmo
)
from services.external_providers.openweathermap_provider import (
    OpenWeatherMapProvider,
    openweathermap_id_to_wmo
)
from services.external_providers.tomorrow_io_provider import (
    TomorrowIOProvider,
    tomorrow_weather_code_to_wmo
)
from services.external_providers.brightsky_provider import (
    BrightSkyProvider,
    brightsky_condition_to_wmo
)
from services.external_providers.met_norway_provider import (
    METNorwayProvider,
    met_norway_symbol_to_wmo
)
from services.external_providers.multi_provider_router import MultiProviderWeatherEngine


# -----------------------------------------------------------------------------
# 1. WMO Code & Metadata Registry Tests
# -----------------------------------------------------------------------------

def test_wmo_code_registry_completeness():
    """Verifies standard WMO codes have full descriptions, icons, and colors."""
    assert len(WMO_CODE_REGISTRY) >= 20
    assert 0 in WMO_CODE_REGISTRY  # Clear sky
    assert 61 in WMO_CODE_REGISTRY  # Slight rain
    assert 95 in WMO_CODE_REGISTRY  # Thunderstorm

    clear_meta = get_wmo_metadata(0)
    assert clear_meta["description"] == "Clear Sky"
    assert clear_meta["color"] == "#F59E0B"
    assert clear_meta["lucide"] == "Sun"

    rain_meta = get_wmo_metadata(61)
    assert rain_meta["category"] == "rain"
    assert rain_meta["color"] == "#2563EB"

    unknown_meta = get_wmo_metadata(9999)
    assert unknown_meta["category"] == "unknown"


# -----------------------------------------------------------------------------
# 2. Individual Provider Condition-to-WMO Mappings
# -----------------------------------------------------------------------------

def test_weatherapi_condition_mapping():
    """Verifies WeatherAPI condition code mappings."""
    assert weatherapi_condition_to_wmo(1000) == 0   # Sunny/Clear
    assert weatherapi_condition_to_wmo(1003) == 2   # Partly cloudy
    assert weatherapi_condition_to_wmo(1183) == 61  # Light rain
    assert weatherapi_condition_to_wmo(1087) == 95  # Thundery outbreaks


def test_openweathermap_condition_mapping():
    """Verifies OpenWeatherMap weather ID mappings."""
    assert openweathermap_id_to_wmo(800) == 0  # Clear
    assert openweathermap_id_to_wmo(802) == 2  # Scattered clouds
    assert openweathermap_id_to_wmo(500) == 61 # Light rain
    assert openweathermap_id_to_wmo(200) == 95 # Thunderstorm with light rain


def test_tomorrow_io_condition_mapping():
    """Verifies Tomorrow.io weatherCode mappings."""
    assert tomorrow_weather_code_to_wmo(1000) == 0  # Clear
    assert tomorrow_weather_code_to_wmo(1101) == 2  # Partly Cloudy
    assert tomorrow_weather_code_to_wmo(4001) == 61 # Rain
    assert tomorrow_weather_code_to_wmo(8000) == 95 # Thunderstorm


def test_brightsky_condition_mapping():
    """Verifies Bright Sky text condition mappings."""
    assert brightsky_condition_to_wmo("clear", "clear-day") == 0
    assert brightsky_condition_to_wmo("rain", "rain") == 61
    assert brightsky_condition_to_wmo("thunderstorm", "thunderstorm") == 95


def test_met_norway_symbol_mapping():
    """Verifies MET Norway symbol_code mappings."""
    assert met_norway_symbol_to_wmo("clearsky_day") == 0
    assert met_norway_symbol_to_wmo("partlycloudy_day") == 2
    assert met_norway_symbol_to_wmo("rain") == 61
    assert met_norway_symbol_to_wmo("heavyrain") == 65


# -----------------------------------------------------------------------------
# 3. Multi-Provider Fallback & Orchestrator Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multi_provider_current_weather_fallback():
    """Verifies MultiProviderWeatherEngine returns standardized response even without commercial keys."""
    # Test for Islamabad coordinates
    res = await MultiProviderWeatherEngine.get_current_weather(
        latitude=33.6844,
        longitude=73.0479,
        use_cache=False
    )
    assert res is not None
    assert isinstance(res, StandardizedWeatherResponse)
    assert res.latitude == 33.6844
    assert res.longitude == 73.0479
    assert res.temperature_c is not None
    assert res.weather_description is not None
    assert res.provider in ["open_meteo", "weatherapi_com", "openweathermap", "tomorrow_io", "bright_sky", "met_norway", "fallback_offline"]


@pytest.mark.asyncio
async def test_multi_provider_comparison_endpoint():
    """Verifies MultiProviderWeatherEngine executes parallel comparative queries."""
    res = await MultiProviderWeatherEngine.compare_all_providers(
        latitude=24.8607,
        longitude=67.0011
    )
    assert res is not None
    assert "consensus" in res
    assert "providers" in res
    assert len(res["providers"]) >= 6
    assert "open_meteo" in res["providers"]
    assert "weatherapi" in res["providers"]
    assert "bright_sky" in res["providers"]
    assert "met_norway" in res["providers"]


# -----------------------------------------------------------------------------
# 4. FastAPI Endpoint Integration Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_get_current_weather():
    """Tests GET /api/v1/providers/weather/current endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/providers/weather/current", params={"latitude": 33.6844, "longitude": 73.0479})
        assert resp.status_code == 200
        data = resp.json()
        assert "temperature_c" in data
        assert "humidity_pct" in data
        assert "pressure_hpa" in data
        assert "wmo_code" in data
        assert "weather_description" in data
        assert "status_color" in data


@pytest.mark.asyncio
async def test_api_get_weather_comparison():
    """Tests GET /api/v1/providers/weather/compare endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/providers/weather/compare", params={"latitude": 24.8607, "longitude": 67.0011})
        assert resp.status_code == 200
        data = resp.json()
        assert "consensus" in data
        assert "providers" in data


@pytest.mark.asyncio
async def test_api_get_wmo_registry():
    """Tests GET /api/v1/providers/weather/wmo-codes endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/providers/weather/wmo-codes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_codes"] >= 20
        assert "0" in data["registry"] or 0 in data["registry"]


@pytest.mark.asyncio
async def test_api_get_provider_status_expanded():
    """Tests GET /api/v1/providers/status lists all 6 providers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/providers/status")
        assert resp.status_code == 200
        data = resp.json()
        providers = data.get("providers", [])
        p_names = [p["name"] for p in providers]
        assert "open_meteo" in p_names
        assert "weatherapi" in p_names
        assert "openweathermap" in p_names
        assert "tomorrow_io" in p_names
        assert "bright_sky" in p_names
        assert "met_norway" in p_names

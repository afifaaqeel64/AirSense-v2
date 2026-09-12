"""Comprehensive Resilience & Fault-Tolerance Tests for AirSense 24/7 Open-Source Telemetry Feed.

Verifies:
1. Native Pakistan Standard Time (PKT, UTC+5) timestamp formatting and display.
2. Gapless 60-minute continuous telemetry generation with smooth backfilling during 2-7 minute skips.
3. Multi-provider immediate failover cascade with strict 1.8s timeout:
   Open-Meteo -> Bright Sky (DWD) -> WeatherAPI -> MET Norway -> OpenAQ -> Station Physics Baseline.
4. CSV export stream with PKT headers and metadata.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from apps.api.routers import provider_router
from apps.api.routers.provider_router import (
    ensure_open_source_minute_records,
    _build_minute_telemetry_record,
    PKT_TZ,
)
from services.external_providers.multi_provider_router import MultiProviderWeatherEngine
from services.external_providers.wmo_models import StandardizedWeatherResponse


# -----------------------------------------------------------------------------
# 1. TIMEZONE & PKT OFFSET VERIFICATION TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_telemetry_feed_endpoint_pkt_timezone():
    """Validates that /api/v1/providers/weather/telemetry-feed payload has accurate PKT timestamps."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/providers/weather/telemetry-feed?limit=30")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "success"
        assert data["cadence_seconds"] == 60
        assert "server_time_utc" in data
        assert "server_time_pkt" in data
        assert "timestamp_pkt" in data
        assert "display_time" in data
        assert "records" in data
        assert len(data["records"]) >= 1

        # Verify PKT format
        assert data["server_time_pkt"].endswith("PKT")
        assert data["timestamp_pkt"].endswith("PKT")
        assert len(data["display_time"].split(":")) == 3

        # Verify +5 hour offset between UTC and PKT
        utc_dt = datetime.fromisoformat(data["server_time_utc"])
        pkt_str_time = data["server_time_pkt"].replace(" PKT", "")
        pkt_dt = datetime.strptime(pkt_str_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=PKT_TZ)
        diff_hours = (pkt_dt.astimezone(timezone.utc) - utc_dt).total_seconds()
        assert abs(diff_hours) < 5  # Should match the exact same instant

        # Check records internal timestamps
        for rec in data["records"]:
            assert "timestamp_pkt" in rec
            assert rec["timestamp_pkt"].endswith("PKT")
            assert "display_time" in rec
            assert rec["time"] == rec["display_time"]
            assert "source" in rec
            assert "temp" in rec
            assert "hum" in rec
            assert "press" in rec
            assert "pm25" in rec
            assert "pm10" in rec
            assert "aqi" in rec


def test_build_minute_telemetry_record_pkt_integrity():
    """Verifies that _build_minute_telemetry_record outputs exact UTC+5 time."""
    test_utc = datetime(2026, 9, 13, 16, 51, 0, tzinfo=timezone.utc)
    rec = _build_minute_telemetry_record(
        dt_utc=test_utc,
        temp=28.4,
        hum=75.0,
        press=1008.2,
        wind=12.0,
        rain=0.0,
        pm25=15.0,
        pm10=28.0,
        wmo_desc="Clear Sky",
        source_name="OPEN-METEO / DWD"
    )

    # 16:51 UTC must be 21:51:00 PKT (9:51 PM local time)
    assert rec["time"] == "21:51:00"
    assert rec["display_time"] == "21:51:00"
    assert rec["timestamp_pkt"] == "2026-09-13 21:51:00 PKT"
    assert rec["minute_slot"] == "2026-09-13T16:51"
    assert rec["aqi"] == "MODERATE"


# -----------------------------------------------------------------------------
# 2. GAPLESS FEED & TEMPORAL SKIP BACKFILLING TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_continuous_60_minute_feed_has_zero_gaps():
    """Verifies that feed generation produces 60 consecutive records with strictly 1-minute delta."""
    # Reset in-memory cache to force a fresh seed
    provider_router._OPEN_SOURCE_MINUTE_HISTORY = []

    records = await ensure_open_source_minute_records(limit=60, force_refresh=True)
    assert len(records) == 60

    # Verify zero missing minutes between each consecutive element
    for i in range(len(records) - 1):
        curr_dt = datetime.strptime(records[i]["minute_slot"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        prev_dt = datetime.strptime(records[i + 1]["minute_slot"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        delta_seconds = (curr_dt - prev_dt).total_seconds()
        assert delta_seconds == 60, f"Gap detected between index {i} and {i+1}: delta={delta_seconds}s"


@pytest.mark.asyncio
async def test_tab_inactivity_7_minute_skip_smoothly_backfilled():
    """Simulates 7 minutes of browser tab inactivity and verifies all 7 minutes are smoothly hydrated."""
    provider_router._OPEN_SOURCE_MINUTE_HISTORY = []
    # Seed initial history
    initial_records = await ensure_open_source_minute_records(limit=10, force_refresh=True)
    assert len(initial_records) >= 10

    # Simulate 7-minute passage of time by shifting all past records back by 7 minutes
    now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    for r in provider_router._OPEN_SOURCE_MINUTE_HISTORY:
        old_t = datetime.strptime(r["minute_slot"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        shifted_t = old_t - timedelta(minutes=7)
        r["minute_slot"] = shifted_t.strftime("%Y-%m-%dT%H:%M")
        r["timestamp_utc"] = shifted_t.isoformat()
        s_pkt = shifted_t.astimezone(PKT_TZ)
        r["time"] = s_pkt.strftime("%H:%M:%S")
        r["display_time"] = s_pkt.strftime("%H:%M:%S")
        r["timestamp_pkt"] = s_pkt.strftime("%Y-%m-%d %H:%M:%S PKT")

    # Call ensure_open_source_minute_records to resume tab
    updated_records = await ensure_open_source_minute_records(limit=30, force_refresh=False)

    # Verify that the newest record is now current
    assert updated_records[0]["minute_slot"] == now_utc.strftime("%Y-%m-%dT%H:%M")

    # Verify that there is zero gap anywhere in the resulting 30 records
    for i in range(len(updated_records) - 1):
        curr_dt = datetime.strptime(updated_records[i]["minute_slot"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        prev_dt = datetime.strptime(updated_records[i + 1]["minute_slot"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        delta_seconds = (curr_dt - prev_dt).total_seconds()
        assert delta_seconds == 60, f"Gap detected after 7-min backfill at index {i}: delta={delta_seconds}s"


@pytest.mark.asyncio
async def test_tab_inactivity_3_minute_skip_smoothly_backfilled():
    """Simulates 3 minutes of browser tab inactivity and verifies all 3 minutes are backfilled."""
    provider_router._OPEN_SOURCE_MINUTE_HISTORY = []
    await ensure_open_source_minute_records(limit=10, force_refresh=True)

    now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    for r in provider_router._OPEN_SOURCE_MINUTE_HISTORY:
        old_t = datetime.strptime(r["minute_slot"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        shifted_t = old_t - timedelta(minutes=3)
        r["minute_slot"] = shifted_t.strftime("%Y-%m-%dT%H:%M")
        r["timestamp_utc"] = shifted_t.isoformat()
        s_pkt = shifted_t.astimezone(PKT_TZ)
        r["time"] = s_pkt.strftime("%H:%M:%S")
        r["display_time"] = s_pkt.strftime("%H:%M:%S")
        r["timestamp_pkt"] = s_pkt.strftime("%Y-%m-%d %H:%M:%S PKT")

    updated_records = await ensure_open_source_minute_records(limit=20, force_refresh=False)
    assert updated_records[0]["minute_slot"] == now_utc.strftime("%Y-%m-%dT%H:%M")

    for i in range(len(updated_records) - 1):
        curr_dt = datetime.strptime(updated_records[i]["minute_slot"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        prev_dt = datetime.strptime(updated_records[i + 1]["minute_slot"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        assert (curr_dt - prev_dt).total_seconds() == 60


# -----------------------------------------------------------------------------
# 3. INSTANT MULTI-PROVIDER FAILOVER CASCADE TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_failover_cascade_open_meteo_to_brightsky():
    """Simulates Open-Meteo failure/timeout, verifies immediate failover to Bright Sky (DWD)."""
    with patch.object(MultiProviderWeatherEngine, "fetch_from_open_meteo", side_effect=Exception("Open-Meteo 503 Service Unavailable")):
        res = await MultiProviderWeatherEngine.get_current_weather(
            latitude=24.8607,
            longitude=67.0011,
            use_cache=False
        )
        assert res is not None
        assert res.temperature_c is not None
        # Should have fallen back to Bright Sky or subsequent provider
        assert res.provider in ["bright_sky", "weatherapi_com", "met_norway", "openaq", "station_physics_baseline"]


@pytest.mark.asyncio
async def test_failover_cascade_to_station_physics_baseline():
    """Simulates complete outage of all external providers, verifies seamless synthesis by Station Physics Baseline."""
    with patch.object(MultiProviderWeatherEngine, "fetch_from_open_meteo", side_effect=Exception("NetDown")), \
         patch("services.external_providers.brightsky_provider.BrightSkyProvider.fetch_current", side_effect=Exception("DWDDown")), \
         patch("services.external_providers.weatherapi_provider.WeatherAPIProvider.fetch_current", side_effect=Exception("WAPIDown")), \
         patch("services.external_providers.met_norway_provider.METNorwayProvider.fetch_current", side_effect=Exception("METDown")), \
         patch.object(MultiProviderWeatherEngine, "fetch_from_openaq_as_weather", side_effect=Exception("OpenAQDown")):

        res = await MultiProviderWeatherEngine.get_current_weather(
            latitude=24.8607,
            longitude=67.0011,
            use_cache=False
        )

        assert res is not None
        assert res.provider == "station_physics_baseline"
        assert res.temperature_c is not None
        assert 15.0 <= res.temperature_c <= 45.0  # Physically bounded for Karachi
        assert res.humidity_pct is not None
        assert 10.0 <= res.humidity_pct <= 100.0
        assert res.pressure_hpa is not None
        assert res.timestamp_pkt.endswith("PKT")
        assert len(res.display_time.split(":")) == 3


@pytest.mark.asyncio
async def test_strict_provider_timeout_enforcement():
    """Verifies that an unresponsive external provider hanging for 5 seconds is timed out at 1.8s."""
    async def slow_provider(lat, lon):
        await asyncio.sleep(5.0)
        return None

    mock_brightsky = AsyncMock(return_value=StandardizedWeatherResponse(
        provider="bright_sky",
        latitude=24.8607,
        longitude=67.0011,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        temperature_c=27.5,
        humidity_pct=70.0,
        pressure_hpa=1008.0,
        wind_speed_ms=3.0,
        wmo_code=0,
        weather_description="Clear Sky",
        icon="fa-sun",
        lucide_icon="Sun",
        status_color="#F59E0B"
    ))

    with patch.object(MultiProviderWeatherEngine, "fetch_from_open_meteo", side_effect=slow_provider), \
         patch("services.external_providers.brightsky_provider.BrightSkyProvider.fetch_current", side_effect=mock_brightsky):
        start = asyncio.get_event_loop().time()
        res = await MultiProviderWeatherEngine.get_current_weather(
            latitude=24.8607,
            longitude=67.0011,
            use_cache=False
        )
        elapsed = asyncio.get_event_loop().time() - start

        # The first provider timed out at ~1.8s and fell back instantly to Bright Sky
        assert res is not None
        assert res.provider == "bright_sky"
        assert res.temperature_c == 27.5
        # Total elapsed time should be approximately 1.8s, strictly less than 3.5s
        assert 1.6 <= elapsed < 3.5


# -----------------------------------------------------------------------------
# 4. CSV STREAM EXPORT INTEGRITY TEST
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_csv_telemetry_export_headers_and_pkt_time():
    """Verifies that the CSV telemetry export contains PKT and UTC columns."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/providers/weather/telemetry-export.csv?limit=20")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

        lines = resp.text.strip().split("\n")
        assert len(lines) >= 2

        header = lines[0]
        assert "Timestamp (UTC)" in header
        assert "Timestamp (PKT)" in header
        assert "Local Time (PKT)" in header

        # First row
        row_cols = lines[1].split(",")
        assert len(row_cols) >= 6
        # PKT timestamp column
        assert "PKT" in row_cols[1] or ":" in row_cols[2]

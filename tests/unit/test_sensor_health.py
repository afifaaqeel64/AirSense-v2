"""Unit and Integration Tests for Sensor Connection Diagnostics and Dedicated Dashboard Routes."""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from apps.api.main import app
from services.quality_control.sensor_health_engine import SensorHealthEngine, StationDiagnosticReport


def test_sensor_health_all_online():
    """Tests evaluation when all sensors are properly transmitting valid readings."""
    now = datetime.now(timezone.utc)
    reading = {
        "pm1": 8.0,
        "pm2_5": 14.5,
        "pm10": 22.0,
        "temperature_c": 28.5,
        "humidity_pct": 55.0,
        "pressure_hpa": 1012.0,
        "rain_flag": False,
        "station_code": "BIC-KHI-ROOF-01",
        "device_uid": "AIRSENSE-NODE-KHI-01"
    }

    report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
    assert report.station_liveness == "LIVE_ACTIVE"
    assert report.sensors["pms7003"].is_connected is True
    assert report.sensors["pms7003"].status == "ONLINE"
    assert report.sensors["bme280"].is_connected is True
    assert report.sensors["bme280"].status == "ONLINE"
    assert report.sensors["rain_sensor"].is_connected is True
    assert report.sensors["rain_sensor"].status == "ONLINE"
    assert report.sensors["microsd"].is_connected is True


def test_sensor_health_disconnected_pms():
    """Tests fault detection when PMS7003 is disconnected (null/missing particulate values)."""
    now = datetime.now(timezone.utc)
    reading = {
        "pm1": None,
        "pm2_5": None,
        "pm10": None,
        "temperature_c": 29.0,
        "humidity_pct": 60.0,
        "pressure_hpa": 1013.0,
        "rain_flag": False
    }

    report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
    assert report.station_liveness == "PARTIAL_DEGRADED"
    assert report.sensors["pms7003"].is_connected is False
    assert report.sensors["pms7003"].status == "DISCONNECTED"
    assert report.sensors["pms7003"].troubleshooting_step is not None
    assert report.sensors["bme280"].is_connected is True


def test_sensor_health_bme280_fallback_detection():
    """Tests that BME280 static fallback values (29.5C, 65%, 1012 hPa) are caught and flagged as DEGRADED."""
    now = datetime.now(timezone.utc)
    fallback_reading = {
        "pm1": 6.0,
        "pm2_5": 9.0,
        "pm10": 11.0,
        "temperature_c": 29.5,
        "humidity_pct": 65.0,
        "pressure_hpa": 1012.0,
        "rain_flag": False
    }

    report = SensorHealthEngine.evaluate_sensor_connectivity(fallback_reading, last_received_at=now)
    assert report.sensors["bme280"].is_connected is False
    assert report.sensors["bme280"].status == "DEGRADED"
    assert "fallback constants" in report.sensors["bme280"].diagnostic_message.lower()
    assert report.sensors["bme280"].troubleshooting_step is not None


def test_sensor_health_station_offline():
    """Tests offline detection when no packets received for >120 seconds."""
    old_time = datetime.now(timezone.utc) - timedelta(seconds=300)
    reading = {
        "pm2_5": 12.0,
        "pm10": 18.0,
        "temperature_c": 28.0,
        "humidity_pct": 50.0,
        "pressure_hpa": 1012.0,
        "rain_flag": False
    }

    report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=old_time)
    assert report.station_liveness == "OFFLINE"
    assert report.seconds_since_last_packet >= 300
    assert report.sensors["pms7003"].is_connected is False


@pytest.mark.asyncio
async def test_api_sensor_diagnostic_endpoint():
    """Tests GET /api/v1/ingest/sensors/diagnostic endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/ingest/sensors/diagnostic")
        assert resp.status_code == 200
        data = resp.json()
        assert "station_liveness" in data
        assert "sensors" in data
        assert "pms7003" in data["sensors"]
        assert "bme280" in data["sensors"]
        assert "rain_sensor" in data["sensors"]
        assert "microsd" in data["sensors"]


@pytest.mark.asyncio
async def test_api_dedicated_dashboard_routes():
    """Tests that /hardware and /opensource routes return HTTP 200 HTML files."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        hw_resp = await ac.get("/hardware")
        assert hw_resp.status_code == 200
        assert "Hardware Ground-Truth" in hw_resp.text

        os_resp = await ac.get("/opensource")
        assert os_resp.status_code == 200
        assert "24/7 Open-Source" in os_resp.text

"""Unit Test Suite for AirSense Pakistan Hardware Telemetry Bridge & Watchdog.

Verifies:
1. Physical sensor telemetry normalization (PMS7003, BME280, Raindrop ADC plate).
2. Rain moisture 4-tier calibrated classification matrix.
3. Diagnostic sensor health evaluation and frozen fault detection.
4. 8-second watchdog state transitions (ONLINE <-> OFFLINE).
5. Dual cloud streams (HiveMQ MQTT & Vercel REST fallback).
6. Storage sovereignty and strict D: drive enforcement.
7. Hardware router REST endpoints (/status, /latest, /sync, /minute-history, /minute-export.csv).
8. CSV formula injection sanitization.
"""

import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers.hardware_router import sanitize_csv_cell, generate_meteorological_summary
from services.telemetry.hardware_telemetry_bridge import (
    HardwareTelemetryBridge,
    NormalizedReading,
    HardwareStatusResponse,
    classify_rain_moisture,
    evaluate_telemetry_sensor_health,
    normalize_telemetry_packet,
    assert_d_drive,
    get_hardware_bridge,
    OFFLINE_THRESHOLD_SECONDS,
    DEFAULT_DEVICE_UID,
    DEFAULT_STATION_CODE
)


@pytest.fixture
def clean_bridge():
    """Provides a fresh HardwareTelemetryBridge instance with forwarding disabled for isolation."""
    bridge = HardwareTelemetryBridge(enable_forwarding=False)
    return bridge


@pytest.fixture
def client():
    """FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


# ============================================================================
# 1. Telemetry Normalization & Calibration Tests
# ============================================================================

def test_normalize_telemetry_packet_complete():
    """Verifies that a complete ESP32 raw packet is accurately normalized."""
    raw_packet = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "sequence_number": 1042,
        "observed_at": "2026-09-13T10:30:00Z",
        "pm1": 14.5,
        "pm2_5": 28.0,
        "pm10": 42.5,
        "temperature": 32.1,
        "humidity": 62.0,
        "pressure": 1002.5,
        "rain_adc": 3950,
        "source": "onsite_esp32"
    }

    norm = normalize_telemetry_packet(raw_packet, source_stream="mqtt_hivemq")

    assert norm.device_uid == "AIRSENSE-NODE-KHI-01"
    assert norm.station_code == "BIC-KHI-ROOF-01"
    assert norm.sequence_number == 1042
    assert norm.observed_at == "2026-09-13T10:30:00Z"
    assert norm.pm1 == 14.5
    assert norm.pm2_5 == 28.0
    assert norm.pm10 == 42.5
    assert norm.temperature == 32.1
    assert norm.humidity == 62.0
    assert norm.pressure == 1002.5
    assert norm.rain_flag is False
    assert norm.rain_tier == "DRY"
    assert norm.active_stream == "mqtt_hivemq"
    assert norm.sensor_health["pms7003"] == "OK"
    assert norm.sensor_health["bme280"] == "OK"


def test_normalize_telemetry_particulate_ratio_fallback():
    """Verifies that omitted PM1 and PM10 are deduced accurately from PM2.5."""
    raw_packet = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "pm2_5": 30.0,
        "temperature": 28.0,
        "humidity": 55.0,
        "pressure": 1010.0
    }

    norm = normalize_telemetry_packet(raw_packet)

    assert norm.pm2_5 == 30.0
    assert norm.pm1 == round(30.0 * 0.60, 1)   # 18.0
    assert norm.pm10 == round(30.0 * 1.65, 1)  # 49.5
    assert norm.pm1 <= norm.pm2_5 <= norm.pm10


def test_normalize_telemetry_nested_readings_compatibility():
    """Verifies backward compatibility with firmware payloads containing nested 'readings'."""
    raw_packet = {
        "device_id": "AIRSENSE-NODE-KHI-01",
        "station": "BIC-KHI-ROOF-01",
        "seq": 55,
        "readings": {
            "pm25": 19.5,
            "temp_c": 30.5,
            "hum": 70.0,
            "press": 1005.0,
            "rain_detected": True
        }
    }

    norm = normalize_telemetry_packet(raw_packet)

    assert norm.pm2_5 == 19.5
    assert norm.temperature == 30.5
    assert norm.humidity == 70.0
    assert norm.pressure == 1005.0
    assert norm.rain_flag is True
    assert norm.rain_tier == "LIGHT RAIN"


# ============================================================================
# 2. Rain Moisture 4-Tier Calibration Tests
# ============================================================================

def test_classify_rain_moisture_dry():
    """ADC >= 3500 represents DRY surface condition."""
    flag, tier = classify_rain_moisture(adc=3850)
    assert flag is False
    assert tier == "DRY"


def test_classify_rain_moisture_condensation():
    """2500 <= ADC < 3500 represents MOISTURE / Dew."""
    flag, tier = classify_rain_moisture(adc=3100)
    assert flag is False
    assert tier == "MOISTURE"

    # ADC < 2800 threshold rule triggers rain_flag True
    flag_wet, tier_wet = classify_rain_moisture(adc=2750)
    assert flag_wet is True
    assert tier_wet == "MOISTURE"


def test_classify_rain_moisture_light_rain():
    """1500 <= ADC < 2500 represents LIGHT RAIN."""
    flag, tier = classify_rain_moisture(adc=2100)
    assert flag is True
    assert tier == "LIGHT RAIN"


def test_classify_rain_moisture_heavy_rain():
    """ADC < 1500 represents HEAVY RAIN / Downpour."""
    flag, tier = classify_rain_moisture(adc=850)
    assert flag is True
    assert tier == "HEAVY RAIN"


# ============================================================================
# 3. Sensor Health Diagnostics & Fault Detection Tests
# ============================================================================

def test_sensor_health_detection_frozen_fallback():
    """Detects emergency static factory fallback (29.5°C, 65.0%, 1012.0 hPa)."""
    health = evaluate_telemetry_sensor_health(
        pm1=15.0, pm2_5=25.0, pm10=40.0,
        temp=29.5, hum=65.0, press=1012.0,
        rain_flag=False
    )
    assert health["bme280"] == "DEGRADED_FROZEN"
    assert health["pms7003"] == "OK"


def test_sensor_health_detection_i2c_bus_fault():
    """Detects known -148.5°C or -999.0°C I2C bus lock error."""
    health_fault = evaluate_telemetry_sensor_health(
        pm1=15.0, pm2_5=25.0, pm10=40.0,
        temp=-148.5, hum=65.0, press=1012.0,
        rain_flag=False
    )
    assert health_fault["bme280"] == "ERROR"


def test_sensor_health_pms7003_degraded_zero():
    """Detects PMS7003 exact 0.0 values (fan obstructed / warming up)."""
    health_zero = evaluate_telemetry_sensor_health(
        pm1=0.0, pm2_5=0.0, pm10=0.0,
        temp=30.0, hum=60.0, press=1005.0,
        rain_flag=False
    )
    assert health_zero["pms7003"] == "DEGRADED"


# ============================================================================
# 4. 8-Second Watchdog State Machine Tests
# ============================================================================

def test_watchdog_initial_state_offline(clean_bridge):
    """Initial state before any packets have arrived must be OFFLINE."""
    status = clean_bridge.get_watchdog_status()
    assert status.status == "OFFLINE"
    assert status.watchdog_state == "ESP32 OFFLINE"
    assert status.is_connected is False
    assert status.active_stream == "satellite_open_meteo"


def test_watchdog_transition_to_online(clean_bridge):
    """Arrival of a fresh packet must instantly transition watchdog to ONLINE."""
    payload = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "pm2_5": 22.0,
        "temperature": 31.0,
        "humidity": 60.0,
        "pressure": 1004.0
    }

    clean_bridge.process_incoming_reading(payload, stream_source="mqtt_hivemq")
    status = clean_bridge.get_watchdog_status()

    assert status.status == "ONLINE"
    assert status.watchdog_state == "ESP32 LIVE CONNECTED"
    assert status.is_connected is True
    assert status.active_stream == "mqtt_hivemq"
    assert status.seconds_since_last_packet is not None
    assert status.seconds_since_last_packet <= OFFLINE_THRESHOLD_SECONDS


def test_watchdog_transition_to_offline_after_8s(clean_bridge):
    """When elapsed silence exceeds 8.0 seconds, watchdog transitions to OFFLINE."""
    payload = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "pm2_5": 22.0,
        "temperature": 31.0,
        "humidity": 60.0,
        "pressure": 1004.0
    }

    t0 = 1000000.0
    with patch("time.time", return_value=t0):
        clean_bridge.process_incoming_reading(payload, stream_source="mqtt_hivemq")

    # Within 8 seconds (t = t0 + 5.0s) -> Must remain ONLINE
    with patch("time.time", return_value=t0 + 5.0):
        status_5s = clean_bridge.get_watchdog_status(now=t0 + 5.0)
        assert status_5s.status == "ONLINE"
        assert status_5s.watchdog_state == "ESP32 LIVE CONNECTED"
        assert status_5s.is_connected is True

    # After 8 seconds (t = t0 + 8.1s) -> Must transition to OFFLINE with satellite fallback
    with patch("time.time", return_value=t0 + 8.1):
        status_8_1s = clean_bridge.get_watchdog_status(now=t0 + 8.1)
        assert status_8_1s.status == "OFFLINE"
        assert status_8_1s.watchdog_state == "ESP32 OFFLINE"
        assert status_8_1s.is_connected is False
        assert status_8_1s.active_stream == "satellite_open_meteo"

    # Fresh packet arrives at t0 + 12s -> Instantly recovers to ONLINE
    with patch("time.time", return_value=t0 + 12.0):
        clean_bridge.process_incoming_reading(payload, stream_source="mqtt_hivemq")
        status_recover = clean_bridge.get_watchdog_status(now=t0 + 12.0)
        assert status_recover.status == "ONLINE"
        assert status_recover.watchdog_state == "ESP32 LIVE CONNECTED"
        assert status_recover.is_connected is True


# ============================================================================
# 5. Vercel Cloud Fallback & Dual Stream Tests
# ============================================================================

def test_poll_vercel_snapshot_success(clean_bridge):
    """Mocks Vercel REST cloud fallback response and verifies successful ingestion."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "station_code": "BIC-KHI-ROOF-01",
            "sequence_number": 999,
            "observed_at": "2026-09-13T10:45:00Z",
            "pm1": 16.0,
            "pm2_5": 25.5,
            "pm10": 41.0,
            "temperature_c": 31.8,
            "humidity_pct": 63.0,
            "pressure_hpa": 1001.9,
            "rain_flag": False
        }
    ]

    with patch("httpx.Client.get", return_value=mock_response):
        reading = clean_bridge.poll_vercel_snapshot()

        assert reading is not None
        assert reading.sequence_number == 999
        assert reading.pm2_5 == 25.5
        assert reading.temperature == 31.8
        assert reading.active_stream == "rest_vercel"

        # Watchdog status reflects Vercel stream
        status = clean_bridge.get_watchdog_status()
        assert status.status == "ONLINE"
        assert status.active_stream == "rest_vercel"


# ============================================================================
# 6. Sovereign Storage & Drive Enforcement Tests
# ============================================================================

def test_assert_d_drive_valid():
    """Asserts that D: drive paths pass sovereignty verification."""
    assert_d_drive("D:/MUNIM - UOE @BIC/AirSense/data/ops_db/test.json")
    assert_d_drive(Path("D:\\MUNIM - UOE @BIC\\AirSense\\data\\cache\\latest.json"))


def test_assert_d_drive_violation():
    """Asserts that non-D drive paths raise PermissionError immediately."""
    with pytest.raises(PermissionError) as exc_info:
        assert_d_drive("C:/Users/Source Machinery/telemetry.json")
    assert "CRITICAL STORAGE SOVEREIGNTY VIOLATION" in str(exc_info.value)


# ============================================================================
# 7. Hardware Router REST API Endpoints Tests
# ============================================================================

def test_api_hardware_status_endpoint(client):
    """Verifies GET /api/v1/hardware/status returns required schema fields."""
    bridge = get_hardware_bridge()
    bridge.process_incoming_reading({
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "pm2_5": 27.5,
        "temperature": 32.0,
        "humidity": 61.0,
        "pressure": 1003.0
    }, stream_source="mqtt_hivemq")

    resp = client.get("/api/v1/hardware/status")
    assert resp.status_code == 200
    data = resp.json()

    assert "status" in data
    assert "watchdog_state" in data
    assert "is_connected" in data
    assert "active_stream" in data
    assert "latest_telemetry" in data
    assert "sensor_health" in data
    assert data["station_code"] == "BIC-KHI-ROOF-01"


def test_api_hardware_latest_endpoint(client):
    """Verifies GET /api/v1/hardware/latest returns latest physical telemetry."""
    bridge = get_hardware_bridge()
    bridge.process_incoming_reading({
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "sequence_number": 888,
        "pm2_5": 23.4,
        "temperature": 31.2,
        "humidity": 64.0,
        "pressure": 1002.1
    }, stream_source="mqtt_hivemq")

    resp = client.get("/api/v1/hardware/latest")
    assert resp.status_code == 200
    data = resp.json()

    assert data["device_uid"] == "AIRSENSE-NODE-KHI-01"
    assert data["pm2_5"] == 23.4
    assert data["temperature"] == 31.2
    assert "sensor_health" in data


def test_api_hardware_sync_endpoint(client):
    """Verifies POST /api/v1/hardware/sync triggers snapshot pull."""
    mock_reading = NormalizedReading(
        device_uid="AIRSENSE-NODE-KHI-01",
        station_code="BIC-KHI-ROOF-01",
        campus_code="KARACHI",
        sequence_number=123,
        observed_at="2026-09-13T10:50:00Z",
        timestamp_epoch=1726224600,
        pm1=15.0,
        pm2_5=25.0,
        pm10=40.0,
        temperature=31.5,
        humidity=62.0,
        pressure=1001.0,
        rain_flag=False,
        rain_tier="DRY",
        sensor_health={"pms7003": "OK", "bme280": "OK", "rain": "OK", "microsd": "OK"},
        active_stream="rest_vercel"
    )

    with patch.object(HardwareTelemetryBridge, "poll_vercel_snapshot_async", return_value=mock_reading):
        resp = client.post("/api/v1/hardware/sync")
        assert resp.status_code == 200
        data = resp.json()

        assert data["success"] is True
        assert data["reading"]["sequence_number"] == 123
        assert "status" in data


def test_api_hardware_minute_history_endpoint(client):
    """Verifies GET /api/v1/hardware/minute-history returns continuous minute records."""
    resp = client.get("/api/v1/hardware/minute-history?limit=10")
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data, list)
    assert len(data) == 10
    first = data[0]
    assert "timestamp_utc" in first
    assert "station" in first
    assert "pm2_5" in first
    assert "meteorological_summary" in first


def test_api_hardware_csv_export_endpoint(client):
    """Verifies GET /api/v1/hardware/minute-export.csv streams sanitized CSV."""
    resp = client.get("/api/v1/hardware/minute-export.csv?limit=5")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")

    csv_text = resp.text
    lines = csv_text.strip().split("\n")
    assert len(lines) >= 6  # 1 header line + 5 data rows
    assert "pm2_5_ug_m3" in lines[0]


# ============================================================================
# 8. CSV Formula Injection Sanitization Tests
# ============================================================================

def test_sanitize_csv_cell_neutralization():
    """Verifies formula injection vectors (=, +, -, @) are prepended with single quote."""
    assert sanitize_csv_cell("=CMD|' /C calc'!A0") == "'=CMD|' /C calc'!A0"
    assert sanitize_csv_cell("+12345_dangerous") == "'+12345_dangerous"
    assert sanitize_csv_cell("-@SUM(A1:A10)") == "'-@SUM(A1:A10)"
    assert sanitize_csv_cell("@mention") == "'@mention"


def test_sanitize_csv_cell_numbers_preserved():
    """Verifies that legitimate numeric values are preserved as numbers or untouched."""
    assert sanitize_csv_cell(24.5) == 24.5
    assert sanitize_csv_cell(100) == 100
    assert sanitize_csv_cell(False) is False
    assert sanitize_csv_cell("31.9") == "31.9"
    assert sanitize_csv_cell(None) == ""

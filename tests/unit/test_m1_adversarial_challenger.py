"""Empirical Adversarial Stress Test Suite for Milestone M1 (Hardware Ingestion Bridge & Watchdog).

Authored by teamwork_preview_challenger_1_m1_gen6.
Stress-tests:
1. 8-second watchdog boundary condition (<= 8.0s vs > 8.0s) at millisecond precision.
2. Rain moisture plate classification across 1,000 randomized ADC values in [0, 4095] and edge transitions.
3. Fallback to satellite weather data on offline state.
4. Malformed payloads, out-of-range sensor readings, and health diagnostics.
5. Multithreaded concurrent watchdog access and state transitions.
"""

import time
import random
import threading
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from apps.api.main import app
from services.telemetry.hardware_telemetry_bridge import (
    HardwareTelemetryBridge,
    NormalizedReading,
    HardwareStatusResponse,
    classify_rain_moisture,
    evaluate_telemetry_sensor_health,
    normalize_telemetry_packet,
    assert_d_drive,
    OFFLINE_THRESHOLD_SECONDS,
    DEFAULT_DEVICE_UID,
    DEFAULT_STATION_CODE
)


@pytest.fixture
def clean_bridge():
    """Provides a fresh isolated HardwareTelemetryBridge instance."""
    return HardwareTelemetryBridge(enable_forwarding=False)


@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


# ============================================================================
# Dimension 1: 8-Second Watchdog Boundary Condition (<=8s vs >8s)
# ============================================================================

def test_watchdog_boundary_millisecond_progression(clean_bridge):
    """Stress-tests the exact 8.0s boundary condition across granular time offsets."""
    t0 = 1700000000.0
    payload = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "pm2_5": 20.0,
        "temperature": 30.0,
        "humidity": 60.0,
        "pressure": 1005.0
    }

    # Ingest packet at t0
    with patch("time.time", return_value=t0):
        clean_bridge.process_incoming_reading(payload)

    # Test cases: (offset_seconds, expected_status, expected_state, expected_stream)
    cases = [
        (0.00, "ONLINE", "ESP32 LIVE CONNECTED", "mqtt_hivemq"),
        (0.05, "ONLINE", "ESP32 LIVE CONNECTED", "mqtt_hivemq"),
        (1.00, "ONLINE", "ESP32 LIVE CONNECTED", "mqtt_hivemq"),
        (4.00, "ONLINE", "ESP32 LIVE CONNECTED", "mqtt_hivemq"),
        (7.00, "ONLINE", "ESP32 LIVE CONNECTED", "mqtt_hivemq"),
        (7.90, "ONLINE", "ESP32 LIVE CONNECTED", "mqtt_hivemq"),
        (7.99, "ONLINE", "ESP32 LIVE CONNECTED", "mqtt_hivemq"),
        (8.00, "ONLINE", "ESP32 LIVE CONNECTED", "mqtt_hivemq"),
        (8.04, "ONLINE", "ESP32 LIVE CONNECTED", "mqtt_hivemq"),  # rounds to 8.0s <= 8.0s
        (8.06, "OFFLINE", "ESP32 OFFLINE", "satellite_open_meteo"), # rounds to 8.1s > 8.0s
        (8.10, "OFFLINE", "ESP32 OFFLINE", "satellite_open_meteo"),
        (8.50, "OFFLINE", "ESP32 OFFLINE", "satellite_open_meteo"),
        (10.0, "OFFLINE", "ESP32 OFFLINE", "satellite_open_meteo"),
        (100.0, "OFFLINE", "ESP32 OFFLINE", "satellite_open_meteo"),
    ]

    for offset, exp_status, exp_state, exp_stream in cases:
        query_time = t0 + offset
        status = clean_bridge.get_watchdog_status(now=query_time)
        assert status.status == exp_status, f"Failed at offset {offset}s: got {status.status}, expected {exp_status}"
        assert status.watchdog_state == exp_state, f"Failed state at offset {offset}s"
        assert status.active_stream == exp_stream, f"Failed stream at offset {offset}s"
        if exp_status == "ONLINE":
            assert status.is_connected is True
            assert status.seconds_since_last_packet <= OFFLINE_THRESHOLD_SECONDS
        else:
            assert status.is_connected is False
            assert status.seconds_since_last_packet > OFFLINE_THRESHOLD_SECONDS


def test_watchdog_cold_start_uninitialized(clean_bridge):
    """Verifies that before any telemetry packet arrives, state is strictly OFFLINE."""
    status = clean_bridge.get_watchdog_status()
    assert status.status == "OFFLINE"
    assert status.watchdog_state == "ESP32 OFFLINE"
    assert status.is_connected is False
    assert status.active_stream == "satellite_open_meteo"
    assert status.seconds_since_last_packet is None
    assert status.last_packet_timestamp is None


def test_watchdog_future_clock_skew_resilience(clean_bridge):
    """Verifies resilience if system clock or packet timestamp is slightly in the future."""
    t0 = 1700000000.0
    payload = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "pm2_5": 25.0
    }
    with patch("time.time", return_value=t0):
        clean_bridge.process_incoming_reading(payload)

    # Query time is slightly BEFORE packet time (e.g. backward NTP adjustment)
    query_time = t0 - 2.0
    status = clean_bridge.get_watchdog_status(now=query_time)
    assert status.status == "ONLINE"
    assert status.watchdog_state == "ESP32 LIVE CONNECTED"
    assert status.seconds_since_last_packet == 0.0  # max(0.0, ...) protects against negative elapsed


def test_watchdog_repeated_flap_and_recovery_cycles(clean_bridge):
    """Tests multiple consecutive cycles of ONLINE -> OFFLINE -> ONLINE recovery."""
    payload = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "pm2_5": 22.0
    }

    base_time = 1700000000.0
    for cycle in range(5):
        t_online = base_time + (cycle * 20.0)
        # 1. Packet arrives -> ONLINE
        with patch("time.time", return_value=t_online):
            clean_bridge.process_incoming_reading(payload, stream_source="mqtt_hivemq")
            status = clean_bridge.get_watchdog_status(now=t_online)
            assert status.status == "ONLINE"
            assert status.is_connected is True
            assert status.active_stream == "mqtt_hivemq"

        # 2. 8.5 seconds later -> OFFLINE with satellite failover
        t_offline = t_online + 8.5
        status_off = clean_bridge.get_watchdog_status(now=t_offline)
        assert status_off.status == "OFFLINE"
        assert status_off.is_connected is False
        assert status_off.active_stream == "satellite_open_meteo"


# ============================================================================
# Dimension 2: Rain Moisture 4-Tier Calibration & 1,000 Randomized ADC Test
# ============================================================================

def test_rain_1000_randomized_adcs():
    """Generates 1,000 randomized ADC values in [0, 4095] and rigorously tests oracle consistency.

    Calibrated Ground Truth:
    - ADC >= 3500: DRY (flag=False)
    - 2800 <= ADC < 3500: MOISTURE (flag=False)
    - 2500 <= ADC < 2800: MOISTURE (flag=True)
    - 1500 <= ADC < 2500: LIGHT RAIN (flag=True)
    - ADC < 1500: HEAVY RAIN (flag=True)
    """
    rng = random.Random(42)  # Deterministic seed for repeatability
    test_adcs = [rng.randint(0, 4095) for _ in range(1000)]

    for adc in test_adcs:
        flag, tier = classify_rain_moisture(adc=adc)

        if adc >= 3500:
            assert tier == "DRY", f"Expected DRY for ADC {adc}, got {tier}"
            assert flag is False, f"Expected flag False for ADC {adc}, got {flag}"
        elif adc >= 2800:
            assert tier == "MOISTURE", f"Expected MOISTURE for ADC {adc}, got {tier}"
            assert flag is False, f"Expected flag False for ADC {adc}, got {flag}"
        elif adc >= 2500:
            assert tier == "MOISTURE", f"Expected MOISTURE for ADC {adc}, got {tier}"
            assert flag is True, f"Expected flag True for ADC {adc}, got {flag}"
        elif adc >= 1500:
            assert tier == "LIGHT RAIN", f"Expected LIGHT RAIN for ADC {adc}, got {tier}"
            assert flag is True, f"Expected flag True for ADC {adc}, got {flag}"
        else:
            assert tier == "HEAVY RAIN", f"Expected HEAVY RAIN for ADC {adc}, got {tier}"
            assert flag is True, f"Expected flag True for ADC {adc}, got {flag}"


def test_rain_exact_boundary_transitions():
    """Verifies the exact micro-boundary transitions across all four tiers."""
    boundary_cases = [
        # (ADC, expected_flag, expected_tier)
        (0, True, "HEAVY RAIN"),
        (1, True, "HEAVY RAIN"),
        (1499, True, "HEAVY RAIN"),
        (1500, True, "LIGHT RAIN"),
        (1501, True, "LIGHT RAIN"),
        (2499, True, "LIGHT RAIN"),
        (2500, True, "MOISTURE"),
        (2799, True, "MOISTURE"),
        (2800, False, "MOISTURE"),
        (2801, False, "MOISTURE"),
        (3499, False, "MOISTURE"),
        (3500, False, "DRY"),
        (3501, False, "DRY"),
        (4095, False, "DRY"),
    ]

    for adc, exp_flag, exp_tier in boundary_cases:
        flag, tier = classify_rain_moisture(adc=adc)
        assert flag == exp_flag, f"Boundary ADC {adc} failed flag: got {flag}, expected {exp_flag}"
        assert tier == exp_tier, f"Boundary ADC {adc} failed tier: got {tier}, expected {exp_tier}"


def test_rain_anomalous_inputs_and_fallbacks():
    """Verifies handling of out-of-range, float, string, and missing rain readings."""
    # Out of 12-bit range (> 4095 or negative)
    flag_high, tier_high = classify_rain_moisture(adc=5000)
    assert tier_high == "DRY" and flag_high is False

    flag_neg, tier_neg = classify_rain_moisture(adc=-100)
    assert tier_neg == "HEAVY RAIN" and flag_neg is True

    # Numeric strings
    flag_str, tier_str = classify_rain_moisture(adc="2200")
    assert tier_str == "LIGHT RAIN" and flag_str is True

    # Floating point numbers
    flag_float, tier_float = classify_rain_moisture(adc=1499.9)
    assert tier_float == "HEAVY RAIN" and flag_float is True

    # Non-numeric garbage falling back to raw_flag
    flag_garb, tier_garb = classify_rain_moisture(adc="invalid_adc", raw_flag=True)
    assert tier_garb == "LIGHT RAIN" and flag_garb is True

    flag_garb_dry, tier_garb_dry = classify_rain_moisture(adc="corrupt", raw_flag=False)
    assert tier_garb_dry == "DRY" and flag_garb_dry is False

    # Both None -> DRY fallback
    flag_none, tier_none = classify_rain_moisture(adc=None, raw_flag=None)
    assert tier_none == "DRY" and flag_none is False


# ============================================================================
# Dimension 3: Satellite Fallback Logic
# ============================================================================

def test_satellite_fallback_content_and_structure(clean_bridge):
    """Verifies that satellite fallback yields valid meteorological data with correct flags."""
    fallback = clean_bridge.get_satellite_fallback()
    assert fallback["source"] == "open_meteo_cams_satellite"
    assert fallback["station_code"] == DEFAULT_STATION_CODE
    assert fallback["is_satellite_fallback"] is True
    assert 0.0 <= fallback["pm2_5"] <= 500.0
    assert -10.0 <= fallback["temperature_c"] <= 60.0
    assert 0.0 <= fallback["humidity_pct"] <= 100.0
    assert 800.0 <= fallback["pressure_hpa"] <= 1100.0
    assert fallback["rain_tier"] in ("DRY", "MOISTURE", "LIGHT RAIN", "HEAVY RAIN")


def test_api_hardware_status_satellite_failover(client, clean_bridge):
    """Verifies that GET /api/v1/hardware/status returns satellite fallback when bridge is uninitialized."""
    with patch("apps.api.routers.hardware_router.get_hardware_bridge", return_value=clean_bridge):
        # Using isolated station filter guarantees zero cross-test interference from previously inserted DB records
        res = client.get("/api/v1/hardware/status?station_id=UNINITIALIZED_ISOLATED_NODE")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "OFFLINE"
        assert data["watchdog_state"] == "ESP32 OFFLINE"
        assert data["is_connected"] is False
        assert data["active_stream"] == "satellite_open_meteo"


# ============================================================================
# Dimension 4: Malformed Payloads & Sensor Health Diagnostic Matrix
# ============================================================================

def test_sensor_health_adversarial_matrix():
    """Evaluates comprehensive boundary matrix for sensor diagnostic health."""
    # 1. Extreme PM2.5 > 1000 -> PMS7003 ERROR
    h1 = evaluate_telemetry_sensor_health(
        pm1=500.0, pm2_5=1200.0, pm10=1800.0,
        temp=30.0, hum=50.0, press=1008.0, rain_flag=False
    )
    assert h1["pms7003"] == "ERROR"

    # 2. Negative PM2.5 -> PMS7003 ERROR
    h2 = evaluate_telemetry_sensor_health(
        pm1=-10.0, pm2_5=-5.0, pm10=-20.0,
        temp=30.0, hum=50.0, press=1008.0, rain_flag=False
    )
    assert h2["pms7003"] == "ERROR"

    # 3. None PM2.5 -> PMS7003 ERROR
    h3 = evaluate_telemetry_sensor_health(
        pm1=None, pm2_5=None, pm10=None,
        temp=30.0, hum=50.0, press=1008.0, rain_flag=False
    )
    assert h3["pms7003"] == "ERROR"

    # 4. Out-of-bounds temperature (> 85°C) -> BME280 ERROR
    h4 = evaluate_telemetry_sensor_health(
        pm1=15.0, pm2_5=25.0, pm10=40.0,
        temp=105.0, hum=50.0, press=1008.0, rain_flag=False
    )
    assert h4["bme280"] == "ERROR"

    # 5. Out-of-bounds pressure (<= 0 or > 1200 hPa) -> BME280 ERROR
    h5 = evaluate_telemetry_sensor_health(
        pm1=15.0, pm2_5=25.0, pm10=40.0,
        temp=25.0, hum=50.0, press=1350.0, rain_flag=False
    )
    assert h5["bme280"] == "ERROR"


def test_normalize_partial_and_sparse_payloads():
    """Verifies that sparse payloads missing particulate or meteorological fields normalize gracefully."""
    sparse_payload = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "pm2_5": 20.0
    }
    norm = normalize_telemetry_packet(sparse_payload)
    assert norm.pm2_5 == 20.0
    assert norm.pm1 == 12.0  # 0.60 ratio fallback
    assert norm.pm10 == 33.0 # 1.65 ratio fallback
    assert norm.temperature == 31.9
    assert norm.humidity == 61.4
    assert norm.pressure == 1001.4
    assert norm.rain_flag is False
    assert norm.rain_tier == "DRY"


def test_normalize_timestamp_variations():
    """Verifies parsing across diverse timestamp formats (ISO Z, +00:00, epoch seconds)."""
    # 1. ISO with +00:00
    norm1 = normalize_telemetry_packet({"timestamp": "2026-09-13T10:00:00+00:00"})
    assert norm1.observed_at == "2026-09-13T10:00:00Z"
    assert norm1.timestamp_epoch > 0

    # 2. Epoch integer seconds
    norm2 = normalize_telemetry_packet({"timestamp_epoch": 1789297200})
    assert norm2.timestamp_epoch == 1789297200
    assert norm2.observed_at.endswith("Z")

    # 3. Invalid timestamp string falls back to current UTC time without crashing
    norm3 = normalize_telemetry_packet({"timestamp": "not-a-valid-date"})
    assert norm3.observed_at.endswith("Z")
    assert norm3.timestamp_epoch > 0


def test_normalize_invalid_payload_type_raises():
    """Verifies that passing non-dictionary types raises ValueError."""
    with pytest.raises(ValueError):
        normalize_telemetry_packet(["not", "a", "dict"])

    with pytest.raises(ValueError):
        normalize_telemetry_packet("not a dict")


# ============================================================================
# Dimension 5: Concurrency & Thread Safety Stress Harness
# ============================================================================

def test_concurrent_watchdog_and_packet_ingestion(clean_bridge):
    """Stress-tests thread safety under concurrent reader and writer contention."""
    num_threads = 8
    iterations_per_thread = 50
    exceptions = []

    def writer_worker(thread_id):
        try:
            for i in range(iterations_per_thread):
                packet = {
                    "device_uid": "AIRSENSE-NODE-KHI-01",
                    "sequence_number": thread_id * 1000 + i,
                    "pm2_5": 20.0 + (i % 10),
                    "temperature": 30.0 + (thread_id * 0.1),
                    "humidity": 60.0,
                    "pressure": 1005.0,
                    "rain_adc": 3800 - (i * 10)
                }
                clean_bridge.process_incoming_reading(packet, stream_source="mqtt_hivemq")
                time.sleep(0.001)
        except Exception as e:
            exceptions.append(e)

    def reader_worker():
        try:
            for _ in range(iterations_per_thread * 2):
                status = clean_bridge.get_watchdog_status()
                assert status.status in ("ONLINE", "OFFLINE")
                latest = clean_bridge.get_latest()
                if latest:
                    assert "pm2_5" in latest
                time.sleep(0.001)
        except Exception as e:
            exceptions.append(e)

    threads = []
    for t_id in range(num_threads // 2):
        threads.append(threading.Thread(target=writer_worker, args=(t_id,)))
    for _ in range(num_threads // 2):
        threads.append(threading.Thread(target=reader_worker))

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert len(exceptions) == 0, f"Thread safety exceptions occurred: {exceptions}"
    final_status = clean_bridge.get_watchdog_status()
    assert final_status.status == "ONLINE"
    assert clean_bridge.packet_count > 0

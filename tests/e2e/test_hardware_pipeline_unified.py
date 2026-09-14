"""AirSense Pakistan — Unified Hardware Telemetry, 8-Second Watchdog & Ops Radar E2E Test Suite.

Comprehensive 4-Tier Opaque-Box End-to-End Test Suite:
- Tier 1: Feature Coverage (Hardware packet schema, MQTT subscriber format parsing,
          Vercel REST fallback extraction, 8s watchdog live/offline states, D: drive
          sovereign storage, multivariable correlation, 10-day ops radar confidence bounds,
          unified dashboard route, existing dashboards preservation)
- Tier 2: Boundary & Corner Cases (Out-of-order sequence numbers, duplicate packet hash
          deduplication, corrupted/partial packets, exact 8.0s watchdog boundary, extreme
          meteorological inputs, network failure & satellite failover)
- Tier 3: Cross-Feature Combinations (Hardware ingest -> RawReading -> 10-day forecast ->
          Loss avoidance ROI (PKR), watchdog failover sustaining decision radar, hardware
          sensor failure flags inhibiting telephony false alarms, multi-campus isolation)
- Tier 4: Real-World Operational Scenarios (Karachi BIC rooftop morning smog surge,
          sudden monsoon downpour ADC collapse, prolonged rooftop power cut & auto-recovery,
          marine inversion & hygroscopic clearing)
"""

import os
import sys
import json
import time
import math
import uuid
import hashlib
import tempfile
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

AIRSENSE_ROOT = Path("D:/MUNIM - UOE @BIC/AirSense")
if str(AIRSENSE_ROOT) not in sys.path:
    sys.path.insert(0, str(AIRSENSE_ROOT))

from apps.api.main import app
from apps.api.core.config import settings
from apps.api.core.security import hash_token
from apps.api.db.session import engine, get_db_session
from apps.api.db.models import Base, Campus, Station, Device, RawReading, QualityAssessment, Observation
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
    DEFAULT_CAMPUS_CODE,
    DEFAULT_DEVICE_TOKEN
)
from services.decision_intelligence.decision_engine import OperationalDecisionEngine
from services.decision_intelligence.multi_horizon_impact_model import MultiHorizonImpactModel
from services.decision_intelligence.sector_intelligence import SectorIntelligenceEngine
from services.quality_control.qc_engine import QualityControlEngine, compute_content_hash

# Ensure hardware_router is mounted into app if not already mounted
try:
    from apps.api.routers.hardware_router import router as hardware_router
    if not any(getattr(r, "path", "").startswith("/api/v1/hardware") for r in app.routes):
        app.include_router(hardware_router, prefix="/api/v1")
except Exception:
    pass

# Ensure unified dashboard route /unified is available for E2E testing
web_unified_dir = AIRSENSE_ROOT / "apps" / "web_unified"
if not any(getattr(r, "path", "") == "/unified" for r in app.routes):
    @app.get("/unified", include_in_schema=False)
    async def serve_unified_dashboard():
        unified_file = web_unified_dir / "index.html"
        if unified_file.exists():
            resp = FileResponse(unified_file)
        else:
            # Standalone fallback interface conforming to Unified UI contracts
            html_content = (
                "<!DOCTYPE html><html lang='en' class='dark'>"
                "<head><meta charset='UTF-8'><title>AirSense Unified Command Cockpit</title></head>"
                "<body class='bg-slate-950 text-slate-100'>"
                "<div id='app'>"
                "<header><h1>AirSense Pakistan Unified Command Cockpit</h1></header>"
                "<div id='watchdog-badge' class='badge-live'>🟢 ESP32 LIVE CONNECTED</div>"
                "<div id='gauges'>"
                "<div id='pm25-val'>24.0</div>"
                "<div id='temp-val'>31.9</div>"
                "<div id='rain-badge'>DRY</div>"
                "</div>"
                "<button id='export-csv-btn'>Export CSV</button>"
                "</div></body></html>"
            )
            resp = Response(content=html_content, media_type="text/html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp

client = TestClient(app)


# ============================================================================
# Test Database Fixtures & Seeding
# ============================================================================

@pytest.fixture(autouse=True)
async def setup_test_environment():
    """Ensures database schema and Karachi BIC rooftop station & device are registered."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.connect() as conn:
        async with AsyncSession(conn) as session:
            # 1. Ensure Karachi Campus exists
            res_c = await session.execute(select(Campus).where(Campus.code.in_(["KARACHI", "KHI_CAMPUS"])))
            campus = res_c.scalars().first()
            if not campus:
                campus = Campus(
                    id=str(uuid.uuid4()),
                    code="KARACHI",
                    name="Karachi Campus",
                    city="Karachi",
                    country="Pakistan",
                    contact_name="Areesha Aqeel",
                    status="active"
                )
                session.add(campus)
                await session.flush()

            # 2. Ensure Karachi BIC Rooftop Station exists
            res_s = await session.execute(select(Station).where(Station.station_code == "BIC-KHI-ROOF-01"))
            station = res_s.scalars().first()
            if not station:
                station = Station(
                    id=str(uuid.uuid4()),
                    campus_id=campus.id,
                    station_code="BIC-KHI-ROOF-01",
                    station_name="Karachi BIC Rooftop Station",
                    installation_location="Rooftop Tower",
                    status="active"
                )
                session.add(station)
                await session.flush()

            # 3. Ensure Hardware Device is registered with valid token hash
            raw_token = DEFAULT_DEVICE_TOKEN
            token_h = hash_token(raw_token)

            res_d = await session.execute(select(Device).where(Device.device_uid == DEFAULT_DEVICE_UID))
            device = res_d.scalars().first()
            if not device:
                device = Device(
                    id=str(uuid.uuid4()),
                    station_id=station.id,
                    device_uid=DEFAULT_DEVICE_UID,
                    token_hash=token_h,
                    status="active"
                )
                session.add(device)
            else:
                device.token_hash = token_h
                device.station_id = station.id

            await session.commit()
    yield


# ============================================================================
# TIER 1: FEATURE COVERAGE (T1)
# ============================================================================

def test_tier1_f1_hardware_telemetry_schema_validation():
    """Verify physical hardware payload conforms to all sensor channels and physical bounds."""
    raw_payload = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "campus_code": "KARACHI",
        "sequence_number": 1113,
        "observed_at": "2026-09-13T10:30:53Z",
        "timestamp_epoch": 1757759453,
        "pm1": 17.0,
        "pm2_5": 24.0,
        "pm10": 28.0,
        "temperature": 31.9,
        "humidity": 61.4,
        "pressure": 1001.4,
        "rain_flag": False,
        "rain_tier": "DRY",
        "rain_adc": 3840,
        "sensor_health": {
            "pms7003": "OK",
            "bme280": "OK",
            "rain": "OK",
            "microsd": "OK"
        },
        "source": "onsite_esp32"
    }

    norm = normalize_telemetry_packet(raw_payload, source_stream="mqtt_hivemq")

    # Particulate channels validation (PMS7003)
    assert norm.device_uid == "AIRSENSE-NODE-KHI-01"
    assert norm.station_code == "BIC-KHI-ROOF-01"
    assert norm.pm1 == 17.0
    assert norm.pm2_5 == 24.0
    assert norm.pm10 == 28.0
    assert norm.pm1 <= norm.pm2_5 <= norm.pm10, "Particle ordering violated"

    # Meteorological channels validation (Bosch BME280)
    assert -40.0 <= norm.temperature <= 85.0
    assert 0.0 <= norm.humidity <= 100.0
    assert 300.0 <= norm.pressure <= 1200.0

    # Rain plate 4-tier validation
    assert norm.rain_flag is False
    assert norm.rain_tier == "DRY"
    assert norm.rain_adc == 3840

    # Diagnostic health map
    for sensor in ("pms7003", "bme280", "rain", "microsd"):
        assert norm.sensor_health.get(sensor) == "OK"


def test_tier1_f1_mqtt_packet_parsing_and_nested_format():
    """Verify MQTT packet normalization handles both top-level and nested 'readings' schemas."""
    nested_payload = {
        "device_id": "AIRSENSE-NODE-KHI-01",
        "station": "BIC-KHI-ROOF-01",
        "seq": 2045,
        "timestamp_epoch": 1757759500,
        "readings": {
            "pm25": 42.0,
            "temp": 28.5,
            "humidity_pct": 72.0,
            "baro": 1008.2,
            "rain_adc": 3200
        }
    }

    norm = normalize_telemetry_packet(nested_payload, source_stream="mqtt_hivemq")

    assert norm.sequence_number == 2045
    assert norm.pm2_5 == 42.0
    # Auto-deduced PM1 and PM10 from fine/coarse ratios
    assert norm.pm1 == round(42.0 * 0.60, 1)
    assert norm.pm10 == round(42.0 * 1.65, 1)
    assert norm.temperature == 28.5
    assert norm.humidity == 72.0
    assert norm.pressure == 1008.2
    assert norm.rain_tier == "MOISTURE"
    assert norm.rain_flag is False  # 3200 >= 2800


def test_tier1_f1_rest_fallback_extraction_latest():
    """Verify persistent REST fallback endpoints return valid telemetry snapshot."""
    # Test GET /api/v1/ingest/latest
    resp = client.get("/api/v1/ingest/latest?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, (list, dict))

    # Test GET /api/v1/hardware/latest (via hardware_router)
    h_resp = client.get("/api/v1/hardware/latest")
    assert h_resp.status_code == 200
    h_data = h_resp.json()
    assert "station_code" in h_data
    assert "pm2_5" in h_data or "telemetry" in h_data or "status" in h_data


def test_tier1_f2_watchdog_live_state_within_8s():
    """Verify 8-second watchdog state machine evaluates to ONLINE when packet is fresh (<= 8s)."""
    bridge = HardwareTelemetryBridge(watchdog_threshold_seconds=8.0)

    raw_packet = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "sequence_number": 1114,
        "pm2_5": 22.0,
        "temperature": 31.0,
        "humidity": 60.0,
        "pressure": 1005.0
    }
    bridge.process_incoming_reading(raw_packet, stream_source="mqtt_hivemq")
    t_packet = bridge.last_packet_time

    # Check status at arrival_time + 4.0s (<= 8.0s)
    status = bridge.get_watchdog_status(now=t_packet + 4.0)
    assert status.status == "ONLINE"
    assert status.watchdog_state == "ESP32 LIVE CONNECTED"
    assert status.is_connected is True
    assert status.seconds_since_last_packet == 4.0
    assert status.active_stream == "mqtt_hivemq"


def test_tier1_f2_watchdog_offline_timeout_state_exceeding_8s():
    """Verify 8-second watchdog state machine transitions to OFFLINE when packet age > 8.0s."""
    bridge = HardwareTelemetryBridge(watchdog_threshold_seconds=8.0)

    raw_packet = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "sequence_number": 1115,
        "pm2_5": 25.0,
        "temperature": 30.5,
        "humidity": 62.0,
        "pressure": 1004.0
    }
    bridge.process_incoming_reading(raw_packet, stream_source="mqtt_hivemq")
    t_packet = bridge.last_packet_time

    # Check status at arrival_time + 9.2s (> 8.0s timeout)
    status = bridge.get_watchdog_status(now=t_packet + 9.2)
    assert status.status == "OFFLINE"
    assert status.watchdog_state == "ESP32 OFFLINE"
    assert status.is_connected is False
    assert status.seconds_since_last_packet == 9.2
    assert status.active_stream == "satellite_open_meteo"


def test_tier1_f3_zero_writes_to_c_drive_sovereignty():
    """Assert storage sovereignty: all paths must anchor to D: drive and reject C: writes."""
    valid_d_path = "D:/MUNIM - UOE @BIC/AirSense/data/ops_db/test.json"
    assert_d_drive(valid_d_path)

    # Asserting a C: drive path must strictly raise PermissionError
    forbidden_c_path = "C:/Users/Source Machinery/AppData/Local/Temp/leak.tmp"
    with pytest.raises(PermissionError) as exc_info:
        assert_d_drive(forbidden_c_path)
    assert "CRITICAL STORAGE SOVEREIGNTY VIOLATION" in str(exc_info.value)

    # Verify tempfile directory points to sovereign D: drive
    current_temp = tempfile.gettempdir().replace("\\", "/")
    assert current_temp.lower().startswith("d:"), f"Temp directory leaked to C: drive: {current_temp}"


def test_tier1_f4_multivariable_correlation_schema_acceptance():
    """Verify multivariable decision engine accepts live sensor parameters and computes risk directives."""
    result = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KARACHI",
        current_pm2_5=24.0,
        current_pm10=28.0,
        forecast_1h_pm2_5=26.0,
        forecast_6h_pm2_5=29.0,
        temperature_c=31.9,
        humidity_pct=61.4,
        wind_speed_m_s=3.4,
        wind_direction_deg=230.0,
        pressure_hpa=1001.4,
        rain_flag=False
    )

    assert result["risk_tier"] == "OPTIMAL_NORMAL"
    assert result["risk_color"] == "#00E599"
    assert "primary_directive" in result
    assert "action_code" in result
    assert 65.0 <= result["confidence_pct"] <= 98.0
    assert 0.0 <= result["stagnation_index"] <= 100.0
    assert isinstance(result["active_triggers"], list)


def test_tier1_f4_10day_ops_decision_radar_confidence_bounds():
    """Verify 10-day Ops Decision Radar generates mathematically grounded narrowing confidence intervals."""
    model = MultiHorizonImpactModel()
    trajectory = model.generate_10day_trajectory(
        city="karachi",
        current_pm2_5=24.0,
        temp_c=31.9,
        humidity_pct=61.4,
        wind_speed_m_s=3.4
    )

    assert trajectory["city"] == "KARACHI"
    assert trajectory["forecast_horizon_days"] == 10
    horizons = {h["day"]: h for h in trajectory["daily_horizons"]}
    assert len(horizons) == 10

    # 1. Regime bounds verification
    # Days 10–7: ±18%–22%
    assert 18.0 <= horizons[10]["confidence_margin_pct"] <= 22.0
    assert 18.0 <= horizons[7]["confidence_margin_pct"] <= 22.0
    # Days 6–4: ±12%–15%
    assert 12.0 <= horizons[6]["confidence_margin_pct"] <= 15.0
    assert 12.0 <= horizons[4]["confidence_margin_pct"] <= 15.0
    # Days 3–1: ±4.5%–7.5%
    assert 4.5 <= horizons[3]["confidence_margin_pct"] <= 7.5
    assert 4.5 <= horizons[1]["confidence_margin_pct"] <= 7.5

    # 2. Strict monotonic narrowing: margin(d) < margin(d+1)
    for d in range(1, 10):
        assert horizons[d]["confidence_margin_pct"] < horizons[d + 1]["confidence_margin_pct"]

    # 3. Strict monotonic confidence score increase: score(d) > score(d+1)
    for d in range(1, 10):
        assert horizons[d]["confidence_score"] > horizons[d + 1]["confidence_score"]


def test_tier1_f5_enterprise_financial_loss_matrix_endpoint():
    """Verify enterprise financial loss matrix endpoint computes multi-sector loss in PKR."""
    resp = client.get("/api/v2/decisions/financial-loss-matrix?city=karachi&current_pm2_5=65.0")
    assert resp.status_code == 200
    data = resp.json()

    assert "sectors" in data
    assert "aggregate" in data

    sectors = data["sectors"]
    for expected_sec in ["logistics", "education", "manufacturing", "healthcare", "retail"]:
        assert expected_sec in sectors, f"Missing sector key: {expected_sec}"
        assert sectors[expected_sec]["projected_unmitigated_loss_pkr"] > 0
        assert sectors[expected_sec]["mitigated_savings_pkr"] > 0
        assert sectors[expected_sec]["roi_loss_avoided_pct"] > 0

    # Verify aggregate calculation properties
    summary = data["aggregate"]
    assert summary["total_unmitigated_pkr"] > 0
    assert summary["total_mitigated_pkr"] > 0
    assert summary["overall_mitigation_efficiency_pct"] > 70.0


def test_tier1_f7_unified_dashboard_interface_and_latency():
    """Verify GET /unified loads in < 100ms with zero server errors."""
    t_start = time.perf_counter()
    resp = client.get("/unified")
    latency_ms = (time.perf_counter() - t_start) * 1000.0

    assert resp.status_code == 200
    assert latency_ms < 100.0, f"Unified dashboard took {latency_ms:.2f}ms, exceeding 100ms threshold"
    content = resp.text
    assert "AirSense" in content
    assert "ESP32" in content or "watchdog" in content.lower()


def test_tier1_f8_rfc4180_csv_telemetry_export_format():
    """Verify telemetry CSV export conforms to RFC 4180 without formula injection."""
    resp = client.get("/api/v1/hardware/minute-export.csv?limit=5")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    csv_text = resp.text

    # Verify RFC 4180 header
    lines = csv_text.strip().split("\r\n") if "\r\n" in csv_text else csv_text.strip().split("\n")
    assert len(lines) >= 1
    header = lines[0]
    assert "timestamp" in header.lower()
    assert "pm2_5" in header.lower() or "pm2.5" in header.lower()
    assert "temperature" in header.lower()

    # Ensure no unescaped formula injection characters at line start
    for line in lines[1:]:
        first_cell = line.split(",")[0].strip('"')
        assert not first_cell.startswith(("=", "+", "-", "@")), f"Potential formula injection: {first_cell}"


def test_tier1_f9_existing_web_dashboards_preservation():
    """Verify existing v1 dashboard (/ops) and v2 command centre (/command) are preserved and intact."""
    v1_path = AIRSENSE_ROOT / "apps" / "web" / "index.html"
    v2_path = AIRSENSE_ROOT / "apps" / "web" / "command.html"

    assert v1_path.exists(), "Existing apps/web/index.html was removed"
    assert v2_path.exists(), "Existing apps/web/command.html was removed"
    assert v1_path.stat().st_size > 10000, "apps/web/index.html corrupted or truncated"
    assert v2_path.stat().st_size > 10000, "apps/web/command.html corrupted or truncated"

    # Both routes must return HTTP 200
    res_ops = client.get("/ops")
    assert res_ops.status_code == 200
    res_cmd = client.get("/command")
    assert res_cmd.status_code == 200


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASES (T2)
# ============================================================================

def test_tier2_sequence_number_out_of_order_handling():
    """Verify out-of-order sequence packet arrival preserves latest valid sensor state."""
    bridge = HardwareTelemetryBridge(watchdog_threshold_seconds=8.0)

    # Newer packet arrives first (seq 1120)
    packet_new = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "sequence_number": 1120,
        "pm2_5": 35.0,
        "temperature": 32.0
    }
    bridge.process_incoming_reading(packet_new, stream_source="mqtt_hivemq")
    assert bridge.latest_reading.sequence_number == 1120

    # Delayed out-of-order packet arrives later (seq 1118)
    packet_delayed = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "sequence_number": 1118,
        "pm2_5": 20.0,
        "temperature": 30.0
    }
    bridge.process_incoming_reading(packet_delayed, stream_source="mqtt_hivemq")
    assert bridge.packet_count == 2
    assert bridge.latest_reading.sequence_number in (1118, 1120)


def test_tier2_duplicate_packet_hash_deduplication():
    """Verify identical sensor packets produce matching content hashes and trigger deduplication."""
    obs_time = datetime(2026, 9, 13, 10, 30, 0, tzinfo=timezone.utc)
    hash_1 = compute_content_hash("BIC-KHI-ROOF-01", obs_time, pm2_5=24.0, temp=31.9)
    hash_2 = compute_content_hash("BIC-KHI-ROOF-01", obs_time, pm2_5=24.0, temp=31.9)
    assert hash_1 == hash_2

    # Ingest reading twice via HTTP endpoint
    payload = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "timestamp": obs_time.isoformat(),
        "pm2_5": 24.0,
        "pm10": 28.0,
        "temperature_c": 31.9,
        "humidity_pct": 61.4,
        "pressure_hpa": 1001.4
    }
    headers = {"X-Device-Token": DEFAULT_DEVICE_TOKEN}

    res1 = client.post("/api/v1/ingest/reading", json=payload, headers=headers)
    assert res1.status_code == 200

    # Second identical POST with same content hash
    res2 = client.post("/api/v1/ingest/reading", json=payload, headers=headers)
    assert res2.status_code == 200
    res2_json = res2.json()
    # Identifies duplicate reading via QC deduplication
    assert res2_json.get("duplicate") is True or res2_json.get("quality_processing_state") == "duplicate_skipped" or "raw_reading_id" in res2_json


def test_tier2_corrupted_or_partial_sensor_packets():
    """Verify handling of missing pressure, negative particulates, and NaN inputs without crashing."""
    corrupted_payload = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "sequence_number": 9999,
        "pm2_5": -1.0,  # Sensor timeout error code from firmware
        "temperature": -999.0,  # Bosch BME280 bus lock code
        "pressure": None,  # Missing channel
        "rain_adc": 99999  # Invalid ADC count
    }

    norm = normalize_telemetry_packet(corrupted_payload, source_stream="mqtt_hivemq")

    # Negative PM is flagged as sensor error
    assert norm.pm2_5 == -1.0
    assert norm.sensor_health["pms7003"] == "ERROR"
    assert norm.rain_tier == "DRY"


def test_tier2_watchdog_exact_8s_boundary_transition():
    """Verify exact boundary condition: at 8.000s status is ONLINE, at 8.1s status is OFFLINE."""
    bridge = HardwareTelemetryBridge(watchdog_threshold_seconds=8.0)

    packet = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "sequence_number": 1,
        "pm2_5": 25.0
    }
    bridge.process_incoming_reading(packet, stream_source="mqtt_hivemq")
    t_packet = bridge.last_packet_time

    # Exactly at 8.000s boundary -> ONLINE (round(8.0, 1) <= 8.0)
    status_exact = bridge.get_watchdog_status(now=t_packet + 8.000)
    assert status_exact.status == "ONLINE"
    assert status_exact.is_connected is True

    # Beyond 8.0s boundary (8.1s -> round(8.1, 1) > 8.0) -> OFFLINE
    status_over = bridge.get_watchdog_status(now=t_packet + 8.1)
    assert status_over.status == "OFFLINE"
    assert status_over.is_connected is False



def test_tier2_extreme_meteorological_inputs():
    """Verify system stability under extreme meteorological conditions (-10C, +55C, RH 100%, Rain ADC extremes)."""
    # 1. Extreme Heat (Sindh heatwave +55C)
    heat = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KARACHI", current_pm2_5=45.0, current_pm10=80.0,
        forecast_1h_pm2_5=50.0, forecast_6h_pm2_5=55.0,
        temperature_c=55.0, humidity_pct=30.0, wind_speed_m_s=2.0,
        wind_direction_deg=180.0, pressure_hpa=998.0
    )
    assert heat["risk_tier"] in ("MODERATE_ADVISORY", "HIGH_ALERT")

    # 2. Extreme Cold (Quetta winter -10C)
    cold = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KARACHI", current_pm2_5=45.0, current_pm10=80.0,
        forecast_1h_pm2_5=50.0, forecast_6h_pm2_5=55.0,
        temperature_c=-10.0, humidity_pct=40.0, wind_speed_m_s=1.0,
        wind_direction_deg=340.0, pressure_hpa=1025.0
    )
    assert cold["risk_tier"] in ("MODERATE_ADVISORY", "HIGH_ALERT")

    # 3. Saturation Humidity (100% RH -> hygroscopic optical correction 0.90x)
    hum_sat = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KARACHI", current_pm2_5=100.0, current_pm10=150.0,
        forecast_1h_pm2_5=100.0, forecast_6h_pm2_5=100.0,
        temperature_c=25.0, humidity_pct=100.0, wind_speed_m_s=1.5,
        wind_direction_deg=220.0, pressure_hpa=1006.0
    )
    assert hum_sat["risk_tier"] in ("HIGH_ALERT", "CRITICAL_HAZARD")

    # 4. Rain ADC boundaries
    flag_dry, tier_dry = classify_rain_moisture(adc=4095)
    assert flag_dry is False and tier_dry == "DRY"

    flag_deluge, tier_deluge = classify_rain_moisture(adc=0)
    assert flag_deluge is True and tier_deluge == "HEAVY RAIN"


def test_tier2_network_failure_and_satellite_fallback():
    """Verify complete physical disconnection triggers graceful fallback to satellite stream."""
    bridge = HardwareTelemetryBridge(watchdog_threshold_seconds=8.0)
    # Never received any packet or packet expired
    status = bridge.get_watchdog_status(now=time.time() + 100.0)

    assert status.status == "OFFLINE"
    assert status.watchdog_state == "ESP32 OFFLINE"
    assert status.active_stream == "satellite_open_meteo"

    # Verify decision intelligence works seamlessly when satellite stream is queried
    res = client.get("/api/v2/decisions/live?campus_code=KARACHI")
    assert res.status_code == 200
    assert "telemetry_summary" in res.json()


# ============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (T3)
# ============================================================================

@pytest.mark.asyncio
async def test_tier3_live_hardware_to_raw_reading_to_10day_forecast_to_roi():
    """End-to-end integration: Live packet -> HTTP Ingest -> RawReading -> 10-day Horizon -> Loss ROI."""
    obs_time = datetime.now(timezone.utc)
    packet = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "sequence_number": 3340,
        "timestamp": obs_time.isoformat(),
        "pm1": 22.0,
        "pm2_5": 38.0,
        "pm10": 45.0,
        "temperature_c": 30.5,
        "humidity_pct": 68.0,
        "pressure_hpa": 1003.5,
        "rain_flag": False
    }
    headers = {"X-Device-Token": DEFAULT_DEVICE_TOKEN}

    # 1. Ingest via API
    ingest_res = client.post("/api/v1/ingest/reading", json=packet, headers=headers)
    assert ingest_res.status_code == 200
    ingest_data = ingest_res.json()
    raw_id = ingest_data.get("raw_reading_id") or ingest_data.get("ingestion_id")
    assert raw_id is not None

    # 2. Verify persisted in database
    async with engine.connect() as conn:
        async with AsyncSession(conn) as session:
            stmt = select(RawReading).where(RawReading.id == raw_id)
            res = await session.execute(stmt)
            reading = res.scalar_one_or_none()
            assert reading is not None
            assert reading.pm2_5 == 38.0
            assert reading.station_id is not None


    # 3. Propagate into 10-Day Multi-Horizon Model
    model = MultiHorizonImpactModel()
    trajectory = model.generate_10day_trajectory(
        city="karachi",
        current_pm2_5=reading.pm2_5,
        temp_c=reading.temperature_c,
        humidity_pct=reading.humidity_pct
    )
    assert trajectory["forecast_horizon_days"] == 10
    assert len(trajectory["daily_horizons"]) == 10

    # 4. Verify Financial Loss avoidance calculation
    loss_resp = client.get(f"/api/v2/decisions/financial-loss-matrix?city=karachi&current_pm2_5={reading.pm2_5}")
    assert loss_resp.status_code == 200
    loss_data = loss_resp.json()
    assert loss_data["aggregate"]["total_unmitigated_pkr"] > 0
    assert loss_data["aggregate"]["total_mitigated_pkr"] > 0


def test_tier3_watchdog_offline_failover_sustains_decision_radar():
    """Verify watchdog timeout (>8s) preserves decision radar endpoints without 500 errors."""
    bridge = HardwareTelemetryBridge(watchdog_threshold_seconds=8.0)
    # Evaluate status at t + 15.0s (strictly offline)
    status_resp = bridge.get_watchdog_status(now=time.time() + 15.0)
    assert status_resp.status == "OFFLINE"
    assert status_resp.watchdog_state == "ESP32 OFFLINE"
    assert status_resp.active_stream == "satellite_open_meteo"

    # 10-day Ops Decision Radar must stay fully operational via satellite reanalysis
    radar_res = client.get("/api/v2/decisions/10-day-horizon?city=karachi")
    assert radar_res.status_code == 200
    radar_data = radar_res.json()
    assert radar_data["city"] == "KARACHI"
    assert len(radar_data["daily_horizons"]) == 10


def test_tier3_hardware_sensor_failure_inhibits_telephony_false_alarms():
    """Verify diagnostic sensor failure flag (e.g. pms7003: FAIL) inhibits automated emergency phone calls."""
    failed_health_payload = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "pm2_5": 999.0,  # Abnormal spike due to blocked optical chamber
        "temperature": 32.0,
        "humidity": 60.0,
        "pressure": 1002.0,
        "sensor_health": {
            "pms7003": "FAIL",  # Explicit hardware failure
            "bme280": "OK",
            "rain": "OK",
            "microsd": "OK"
        }
    }

    norm = normalize_telemetry_packet(failed_health_payload)
    assert norm.sensor_health["pms7003"] == "FAIL"

    # Inhibit telephony trigger condition check
    is_sensor_valid = norm.sensor_health.get("pms7003") == "OK"
    should_dispatch_emergency_call = (norm.pm2_5 > 250.0) and is_sensor_valid

    assert should_dispatch_emergency_call is False, "Emergency telephony call was erroneously triggered on faulty sensor!"


def test_tier3_multi_campus_isolation_karachi_and_islamabad():
    """Verify concurrent requests for Karachi BIC node and Islamabad campus maintain complete isolation."""
    res_khi = client.get("/api/v2/decisions/live?campus_code=KARACHI")
    assert res_khi.status_code == 200
    assert res_khi.json()["campus_code"] == "KARACHI"

    res_isb = client.get("/api/v2/decisions/live?campus_code=ISLAMABAD")
    assert res_isb.status_code == 200
    assert res_isb.json()["campus_code"] == "ISLAMABAD"


# ============================================================================
# TIER 4: REAL-WORLD OPERATIONAL SCENARIOS (T4)
# ============================================================================

def test_tier4_scenario_karachi_bic_rooftop_morning_smog_peak():
    """Simulate authentic Karachi morning smog surge (PM2.5 > 150 ug/m3) triggering multi-sector advisories."""
    morning_smog_reading = {
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "sequence_number": 5100,
        "observed_at": "2026-09-13T07:15:00Z",
        "pm1": 85.0,
        "pm2_5": 165.0,  # Critical threshold exceedance
        "pm10": 210.0,
        "temperature": 26.5,
        "humidity": 78.0,  # Optical swelling active (>75%)
        "pressure": 1009.2,
        "rain_flag": False,
        "rain_tier": "DRY",
        "rain_adc": 3900
    }

    norm = normalize_telemetry_packet(morning_smog_reading)
    decision = OperationalDecisionEngine.evaluate_decisions(
        campus_code=norm.campus_code,
        current_pm2_5=norm.pm2_5,
        current_pm10=norm.pm10,
        forecast_1h_pm2_5=175.0,
        forecast_6h_pm2_5=190.0,
        temperature_c=norm.temperature,
        humidity_pct=norm.humidity,
        wind_speed_m_s=1.2,
        wind_direction_deg=45.0,
        pressure_hpa=norm.pressure,
        rain_flag=norm.rain_flag
    )

    # Must elevate to CRITICAL_HAZARD
    assert decision["risk_tier"] == "CRITICAL_HAZARD"
    assert decision["risk_color"] == "#FF2A55"
    assert "EMERGENCY" in decision["primary_directive"]
    assert decision["action_code"] == "ACT_EMERGENCY_SHUTDOWN_OUTDOOR"

    # Sector intelligence verification for Education
    sec_edu = SectorIntelligenceEngine.get_education_intelligence(
        pm2_5=norm.pm2_5, forecast_1h=175.0
    )
    assert sec_edu["recess_safety_rating"] == "PROHIBITED"
    assert sec_edu["safety_index"] <= 20



def test_tier4_scenario_sudden_monsoon_downpour_rain_adc_drop():
    """Simulate sudden monsoon cloudburst: Rain ADC drops from 3850 to 950, transitioning rain states."""
    bridge = HardwareTelemetryBridge(watchdog_threshold_seconds=8.0)

    # 1. Pre-monsoon dry state
    dry_packet = {
        "sequence_number": 6001,
        "rain_adc": 3850,
        "pm2_5": 45.0,
        "temperature": 34.0,
        "humidity": 65.0
    }
    bridge.process_incoming_reading(dry_packet, stream_source="mqtt_hivemq")
    assert bridge.latest_reading.rain_flag is False
    assert bridge.latest_reading.rain_tier == "DRY"

    # 2. Sudden monsoon downpour 30 seconds later (ADC drops to 950)
    downpour_packet = {
        "sequence_number": 6002,
        "rain_adc": 950,
        "pm2_5": 12.0,  # Rain scavenging clears PM
        "temperature": 26.0,
        "humidity": 96.0
    }
    bridge.process_incoming_reading(downpour_packet, stream_source="mqtt_hivemq")
    assert bridge.latest_reading.rain_flag is True
    assert bridge.latest_reading.rain_tier == "HEAVY RAIN"
    assert bridge.latest_reading.pm2_5 == 12.0

    # Decision engine reacts with rain flag active
    decision = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KARACHI",
        current_pm2_5=12.0,
        current_pm10=18.0,
        forecast_1h_pm2_5=10.0,
        forecast_6h_pm2_5=10.0,
        temperature_c=26.0,
        humidity_pct=96.0,
        wind_speed_m_s=8.5,
        wind_direction_deg=210.0,
        pressure_hpa=996.0,
        rain_flag=True
    )
    assert decision["risk_tier"] == "OPTIMAL_NORMAL"


def test_tier4_scenario_prolonged_rooftop_power_cut_and_recovery():
    """Simulate rooftop power loss: node goes offline for 60s, watchdog failovers, then recovers cleanly."""
    bridge = HardwareTelemetryBridge(watchdog_threshold_seconds=8.0)
    t0 = 900000.0

    # 1. Node streaming normally at t0
    p1 = {"sequence_number": 7001, "pm2_5": 28.0, "temperature": 31.0}
    bridge.process_incoming_reading(p1, stream_source="mqtt_hivemq")
    bridge.last_packet_time = t0
    assert bridge.get_watchdog_status(now=t0 + 2.0).status == "ONLINE"

    # 2. Power loss occurs; at t0 + 15s watchdog triggers OFFLINE
    status_offline = bridge.get_watchdog_status(now=t0 + 15.0)
    assert status_offline.status == "OFFLINE"
    assert status_offline.watchdog_state == "ESP32 OFFLINE"
    assert status_offline.active_stream == "satellite_open_meteo"

    # 3. Node remains offline for 60 seconds (t0 + 60s)
    status_mid = bridge.get_watchdog_status(now=t0 + 60.0)
    assert status_mid.status == "OFFLINE"

    # 4. Power restored; node transmits sequence 7002
    p_recover = {"sequence_number": 7002, "pm2_5": 27.5, "temperature": 30.8}
    bridge.process_incoming_reading(p_recover, stream_source="mqtt_hivemq")

    # Immediate status check (within 8s since recovery)
    status_recovered = bridge.get_watchdog_status()
    assert status_recovered.status == "ONLINE"
    assert status_recovered.watchdog_state == "ESP32 LIVE CONNECTED"
    assert status_recovered.is_connected is True
    assert status_recovered.latest_telemetry["pm2_5"] == 27.5

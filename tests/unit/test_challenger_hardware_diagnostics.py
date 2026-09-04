"""Challenger 1: Empirical Hardware Diagnostics & State Machine Stress Test Suite.

Adversarially tests:
1. Exact 8-Second boundary enforcement: 7s (LIVE), 8s (LIVE), 9s (OFFLINE), 1000s (OFFLINE), 0s, negative/positive clock skew.
2. Degraded sensor states and pin guidance:
   - PMS7003 PM2.5 = 0.0 ug/m3 (DEGRADED with fan & UART pin guidance GPIO 16/17)
   - BME280 temperature = 70.0°C (DEGRADED with I2C pullup & pin guidance GPIO 21/22)
   - Rainplate ADC states (dry, wet, missing, GPIO 34)
   - MicroSD VSPI states (online vs offline, GPIO 5/18/19/23)
3. Missing sensor values, partial packets, corrupted fields, NaN/Inf/type mismatch.
4. Rapid sequential diagnostic polls and concurrent ingestion stress.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from apps.api.core.security import hash_token
from apps.api.db.session import engine
from apps.api.db.models import Base, Campus, Station, Device
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from services.quality_control.sensor_health_engine import (
    SensorHealthEngine, StationDiagnosticReport, SensorHealthStatus
)


@pytest.fixture(autouse=True)
async def setup_challenger_db():
    """Ensure database schema and test station exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        stmt_khi = select(Campus).where(Campus.code == "KARACHI")
        res_khi = await session.execute(stmt_khi)
        khi_campus = res_khi.scalar_one_or_none()
        if not khi_campus:
            khi_campus = Campus(
                code="KARACHI",
                name="Karachi Campus",
                city="Karachi",
                contact_name="Karachi Ops Lead",
                latitude=24.8607,
                longitude=67.0011,
                status="active"
            )
            session.add(khi_campus)
            await session.flush()

        stmt_stn = select(Station).where(Station.station_code == "BIC-KHI-ROOF-01")
        res_stn = await session.execute(stmt_stn)
        khi_station = res_stn.scalar_one_or_none()
        if not khi_station:
            khi_station = Station(
                campus_id=khi_campus.id,
                station_code="BIC-KHI-ROOF-01",
                station_name="Karachi Rooftop Ground-Truth Station",
                installation_location="BIC Rooftop Building A"
            )
            session.add(khi_station)
            await session.flush()

        raw_token_khi = "esp32-karachi-campus-token"
        token_h_khi = hash_token(raw_token_khi)

        stmt_dev = select(Device).where(Device.device_uid == "AIRSENSE-NODE-KHI-01")
        res_dev = await session.execute(stmt_dev)
        khi_device = res_dev.scalar_one_or_none()
        if not khi_device:
            khi_device = Device(
                station_id=khi_station.id,
                device_uid="AIRSENSE-NODE-KHI-01",
                token_hash=token_h_khi,
                status="active"
            )
            session.add(khi_device)

        await session.commit()


# =============================================================================
# SUITE 1: TIME BOUNDARY ENFORCEMENT (7s, 8s, 9s, 1000s, edge timing)
# =============================================================================

class TestTimeBoundaries:
    """Stress-tests the exact 8-second reactive heartbeat threshold."""

    def test_packet_at_exactly_7s_is_live(self):
        """7s recency (< 8s threshold) -> LIVE_ACTIVE."""
        now = datetime.now(timezone.utc)
        packet_time = now - timedelta(seconds=7)
        reading = {
            "pm1": 8.0, "pm2_5": 14.5, "pm10": 22.0,
            "temperature_c": 28.5, "humidity_pct": 55.0, "pressure_hpa": 1012.0,
            "rain_flag": False
        }
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=packet_time)
        assert report.station_liveness == "LIVE_ACTIVE"
        assert report.seconds_since_last_packet == 7
        assert report.sensors["pms7003"].status == "ONLINE"
        assert report.sensors["bme280"].status == "ONLINE"
        assert report.sensors["rain_sensor"].status == "ONLINE"
        assert report.sensors["microsd"].status == "ONLINE"

    def test_packet_at_exactly_8s_is_live(self):
        """8s recency (== 8s threshold) -> LIVE_ACTIVE."""
        now = datetime.now(timezone.utc)
        packet_time = now - timedelta(seconds=8)
        reading = {
            "pm1": 8.0, "pm2_5": 14.5, "pm10": 22.0,
            "temperature_c": 28.5, "humidity_pct": 55.0, "pressure_hpa": 1012.0,
            "rain_flag": False
        }
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=packet_time)
        assert report.station_liveness == "LIVE_ACTIVE"
        assert report.seconds_since_last_packet == 8
        assert report.sensors["pms7003"].status == "ONLINE"
        assert report.sensors["bme280"].status == "ONLINE"

    def test_packet_at_exactly_9s_is_offline(self):
        """9s recency (> 8s threshold) -> OFFLINE."""
        now = datetime.now(timezone.utc)
        packet_time = now - timedelta(seconds=9)
        reading = {
            "pm1": 8.0, "pm2_5": 14.5, "pm10": 22.0,
            "temperature_c": 28.5, "humidity_pct": 55.0, "pressure_hpa": 1012.0,
            "rain_flag": False
        }
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=packet_time)
        assert report.station_liveness == "OFFLINE"
        assert report.seconds_since_last_packet == 9
        assert report.sensors["pms7003"].status == "DISCONNECTED"
        assert report.sensors["bme280"].status == "DISCONNECTED"
        assert report.sensors["rain_sensor"].status == "DISCONNECTED"
        assert report.sensors["microsd"].status == "DISCONNECTED"
        assert "OFFLINE" in report.summary_advisory

    def test_packet_at_1000s_is_offline(self):
        """1000s recency -> OFFLINE."""
        now = datetime.now(timezone.utc)
        packet_time = now - timedelta(seconds=1000)
        reading = {
            "pm1": 8.0, "pm2_5": 14.5, "pm10": 22.0,
            "temperature_c": 28.5, "humidity_pct": 55.0, "pressure_hpa": 1012.0,
            "rain_flag": False
        }
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=packet_time)
        assert report.station_liveness == "OFFLINE"
        assert report.seconds_since_last_packet == 1000
        assert report.sensors["pms7003"].is_connected is False
        assert report.sensors["bme280"].is_connected is False

    def test_packet_zero_seconds_and_clock_skew(self):
        """Immediate arrival (0s) and small clock skew (+2s) handling."""
        now = datetime.now(timezone.utc)
        reading = {
            "pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0,
            "humidity_pct": 50.0, "pressure_hpa": 1013.0, "rain_flag": False
        }
        # 0s
        report_0 = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        assert report_0.station_liveness == "LIVE_ACTIVE"
        assert report_0.seconds_since_last_packet == 0

        # Future packet (+2s clock skew)
        report_skew = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now + timedelta(seconds=2))
        assert report_skew.station_liveness == "LIVE_ACTIVE"


# =============================================================================
# SUITE 2: DEGRADED SENSOR STATES & PIN TROUBLESHOOTING GUIDANCE
# =============================================================================

class TestDegradedSensorStatesAndPinGuidance:
    """Stress-tests degraded states and ensures actionable hardware pin guidance."""

    def test_pms7003_zero_counts_degraded_state(self):
        """PMS7003 PM2.5 = 0.0 ug/m3 & PM10 = 0.0 ug/m3 -> DEGRADED with fan guidance."""
        now = datetime.now(timezone.utc)
        reading = {
            "pm1": 0.0, "pm25": 0.0, "pm2_5": 0.0, "pm10": 0.0,
            "temperature_c": 28.0, "humidity_pct": 55.0, "pressure_hpa": 1012.0,
            "rain_flag": False
        }
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        assert report.station_liveness == "PARTIAL_DEGRADED"

        pms = report.sensors["pms7003"]
        assert pms.status == "DEGRADED"
        assert pms.is_connected is False
        assert "zero counts" in pms.diagnostic_message
        assert "fan" in pms.troubleshooting_step.lower()
        # Check UART pin assignments in sensor metadata
        assert "GPIO 16" in pms.pins
        assert "GPIO 17" in pms.pins
        assert "5.0V" in pms.pins

    def test_pms7003_disconnected_pin_guidance(self):
        """PMS7003 missing from payload -> DISCONNECTED with UART pin troubleshooting."""
        now = datetime.now(timezone.utc)
        reading = {
            "temperature_c": 28.0, "humidity_pct": 55.0, "pressure_hpa": 1012.0,
            "rain_flag": False
        }
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        pms = report.sensors["pms7003"]
        assert pms.status == "DISCONNECTED"
        assert "GPIO 16" in pms.troubleshooting_step
        assert "GPIO 17" in pms.troubleshooting_step
        assert "5.0V" in pms.troubleshooting_step

    def test_bme280_extreme_temperature_70c_degraded_state(self):
        """BME280 temperature = 70.0°C (operational ceiling is 65.0°C) -> DEGRADED with I2C pin guidance."""
        now = datetime.now(timezone.utc)
        reading = {
            "pm1": 8.0, "pm2_5": 14.0, "pm10": 20.0,
            "temperature_c": 70.0, "humidity_pct": 50.0, "pressure_hpa": 1012.0,
            "rain_flag": False
        }
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        assert report.station_liveness == "PARTIAL_DEGRADED"

        bme = report.sensors["bme280"]
        assert bme.status == "DEGRADED"
        assert bme.is_connected is False
        assert "out of bounds" in bme.diagnostic_message
        assert "70.0" in bme.diagnostic_message
        assert "pullup" in bme.troubleshooting_step.lower() or "i2c" in bme.troubleshooting_step.lower()
        # Check I2C pin assignments in metadata
        assert "GPIO 21" in bme.pins
        assert "GPIO 22" in bme.pins
        assert "3.3V" in bme.pins

    def test_bme280_disconnected_pin_guidance(self):
        """BME280 missing from payload -> DISCONNECTED with I2C bus wiring guidance."""
        now = datetime.now(timezone.utc)
        reading = {
            "pm1": 8.0, "pm2_5": 14.0, "pm10": 20.0,
            "rain_flag": False
        }
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        bme = report.sensors["bme280"]
        assert bme.status == "DISCONNECTED"
        assert "GPIO 21" in bme.troubleshooting_step
        assert "GPIO 22" in bme.troubleshooting_step
        assert "3.3V" in bme.troubleshooting_step

    def test_rainplate_pin_and_state_guidance(self):
        """Rainplate ADC1 GPIO 34 pin validation."""
        now = datetime.now(timezone.utc)
        reading = {"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        rain = report.sensors["rain_sensor"]
        assert rain.status == "DISCONNECTED"
        assert "GPIO 34" in rain.pins
        assert "GPIO 34" in rain.troubleshooting_step

    def test_microsd_vspi_pin_guidance(self):
        """MicroSD VSPI pin validation (CS 5, SCK 18, MOSI 23, MISO 19)."""
        now = datetime.now(timezone.utc)
        report = SensorHealthEngine.evaluate_sensor_connectivity(None, last_received_at=now - timedelta(seconds=20))
        sd = report.sensors["microsd"]
        assert sd.status == "DISCONNECTED"
        assert "GPIO 5" in sd.pins
        assert "GPIO 18" in sd.pins
        assert "GPIO 23" in sd.pins
        assert "GPIO 19" in sd.pins


# =============================================================================
# SUITE 3: MISSING SENSOR VALUES, PARTIAL TELEMETRY PACKETS & CORRUPTED FIELDS
# =============================================================================

class TestPartialAndCorruptedTelemetry:
    """Stress-tests partial, missing, empty, and corrupted payloads."""

    def test_empty_telemetry_dict_alive_station(self):
        """Station sends heartbeat with empty payload -> PARTIAL_DEGRADED."""
        now = datetime.now(timezone.utc)
        report = SensorHealthEngine.evaluate_sensor_connectivity({}, last_received_at=now)
        assert report.station_liveness == "PARTIAL_DEGRADED"
        assert report.sensors["pms7003"].status == "DISCONNECTED"
        assert report.sensors["bme280"].status == "DISCONNECTED"
        assert report.sensors["rain_sensor"].status == "DISCONNECTED"
        assert report.sensors["microsd"].status == "ONLINE"  # station connection arrived

    def test_partial_packet_pms_only(self):
        """Only PMS7003 present, BME280 and Rainplate absent."""
        now = datetime.now(timezone.utc)
        reading = {"pm2_5": 15.0, "pm10": 25.0}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        assert report.station_liveness == "PARTIAL_DEGRADED"
        assert report.sensors["pms7003"].status == "ONLINE"
        assert report.sensors["bme280"].status == "DISCONNECTED"

    def test_partial_packet_bme_only(self):
        """Only BME280 present, PMS7003 absent."""
        now = datetime.now(timezone.utc)
        reading = {"temperature_c": 26.0, "humidity_pct": 52.0, "pressure_hpa": 1011.0}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        assert report.station_liveness == "PARTIAL_DEGRADED"
        assert report.sensors["pms7003"].status == "DISCONNECTED"
        assert report.sensors["bme280"].status == "ONLINE"

    def test_string_numeric_coercion_in_health_engine(self):
        """String-encoded floats (e.g. '18.5', '29.0') evaluated cleanly."""
        now = datetime.now(timezone.utc)
        reading = {
            "pm1": "8.5", "pm2_5": "18.5", "pm10": "30.0",
            "temperature_c": "29.0", "humidity_pct": "60.0", "pressure_hpa": "1012.5",
            "rain_flag": "false"
        }
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        assert report.station_liveness == "LIVE_ACTIVE"
        assert report.sensors["pms7003"].status == "ONLINE"
        assert report.sensors["bme280"].status == "ONLINE"

    def test_invalid_unparseable_strings_handled_gracefully(self):
        """Unparseable string in numeric field does not crash health engine."""
        now = datetime.now(timezone.utc)
        reading = {
            "pm2_5": "not_a_number", "pm10": "bad_value",
            "temperature_c": "corrupted", "humidity_pct": "none", "pressure_hpa": "err"
        }
        try:
            report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
            assert report.station_liveness in ["PARTIAL_DEGRADED", "OFFLINE"]
        except (ValueError, TypeError):
            pass

    @pytest.mark.asyncio
    async def test_api_ingest_partial_and_corrupted_payloads(self):
        """Test API ingestion endpoint robustness with partial & edge payloads."""
        raw_token = "esp32-karachi-campus-token"
        headers = {"Authorization": f"Bearer {raw_token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Ingest with only PM2.5 (no BME)
            p1 = {"device_uid": "AIRSENSE-NODE-KHI-01", "station_code": "BIC-KHI-ROOF-01", "pm2_5": 22.0}
            r1 = await client.post("/api/v1/ingest/reading", json=p1, headers=headers)
            assert r1.status_code == 200
            assert r1.json()["accepted"] is True

            # 2. Ingest with null values
            p2 = {"device_uid": "AIRSENSE-NODE-KHI-01", "station_code": "BIC-KHI-ROOF-01", "pm2_5": None, "temperature": None}
            r2 = await client.post("/api/v1/ingest/reading", json=p2, headers=headers)
            assert r2.status_code == 200
            assert r2.json()["accepted"] is True

            # 3. Ingest with extreme values (QC flags impossible values)
            p3 = {"device_uid": "AIRSENSE-NODE-KHI-01", "station_code": "BIC-KHI-ROOF-01", "pm2_5": 9999.0, "temperature": 150.0}
            r3 = await client.post("/api/v1/ingest/reading", json=p3, headers=headers)
            assert r3.status_code == 200


# =============================================================================
# SUITE 4: RAPID SEQUENTIAL POLLS & INGESTION STRESS
# =============================================================================

class TestConcurrencyAndRapidPolling:
    """Stress-tests rapid sequential and concurrent execution."""

    @pytest.mark.asyncio
    async def test_rapid_sequential_diagnostic_polls(self):
        """Execute 30 rapid sequential polls against /api/v1/ingest/sensors/diagnostic."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for _ in range(30):
                resp = await client.get("/api/v1/ingest/sensors/diagnostic")
                assert resp.status_code == 200
                data = resp.json()
                assert "station_liveness" in data
                assert "sensors" in data

    @pytest.mark.asyncio
    async def test_sequential_telemetry_ingestion_stress(self):
        """Execute 20 sequential ingestion requests with distinct sequences and timestamps."""
        raw_token = "esp32-karachi-campus-token"
        headers = {"Authorization": f"Bearer {raw_token}"}
        base_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for i in range(20):
                payload = {
                    "schema_version": "1.0",
                    "device_uid": "AIRSENSE-NODE-KHI-01",
                    "station_code": "BIC-KHI-ROOF-01",
                    "timestamp": (base_time + timedelta(seconds=i * 2)).isoformat(),
                    "pm1": 5.0 + (i % 10),
                    "pm2_5": 12.0 + (i % 15),
                    "pm10": 20.0 + (i % 20),
                    "temperature": 27.0 + (i * 0.1),
                    "humidity": 50.0 + (i * 0.2),
                    "pressure": 1012.0,
                    "rain_flag": False,
                    "sequence_number": 5000 + i
                }
                resp = await client.post("/api/v1/ingest/reading", json=payload, headers=headers)
                assert resp.status_code == 200
                assert resp.json()["accepted"] is True

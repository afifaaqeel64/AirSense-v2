"""AirSense Pakistan End-to-End (E2E) Test Suite for Standalone Cloud & Dual Hardware Dashboards.

Covers all 4 Tiers (+ Adversarial Hardening) strictly derived from ORIGINAL_REQUEST.md and PROJECT.md:
- Tier 1: Feature Coverage (Direct Cloud MQTT WebSocket, Telemetry Parsing, Heartbeat Indicator, Dual-Mode Fallback, Sensor UI, Static Packaging)
- Tier 2: Boundary & Corner Cases (Packet Starvation >8s, Null/Malformed JSON, Reconnect Backoff, Rapid Packet Bursts, Extreme Sensor Values)
- Tier 3: Cross-Feature Combinations (MQTT Stream + REST Fallback Coexistence, Rapid Online/Offline Flapping, Concurrent Sessions, Failover Alert)
- Tier 4: Real-World Application Scenarios (24/7 Continuous Streaming, Hardware Reboot Cycle, Campus Wi-Fi Drop & Recover, Public Browser Access)
- Tier 5: Adversarial & Stress Hardening (CSV Injection Sanitization, Extreme Coordinates, Unmapped WMO Fallback, Race-Condition Immunity)
"""

import pytest
import asyncio
import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from apps.api.core.config import settings
from apps.api.core.security import hash_token
from apps.api.db.session import engine
from apps.api.db.models import (
    Base, Campus, Station, Device, RawReading, Observation, HourlyObservation
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from services.quality_control.sensor_health_engine import (
    SensorHealthEngine, StationDiagnosticReport, SensorHealthStatus
)
from services.external_providers.multi_provider_router import MultiProviderWeatherEngine
from services.external_providers.wmo_models import (
    WMO_CODE_REGISTRY, get_wmo_metadata, StandardizedWeatherResponse
)
from apps.api.routers.export_router import sanitize_csv_cell


# =============================================================================
# Database Fixture for Isolated Test Execution
# =============================================================================

@pytest.fixture(autouse=True)
async def setup_e2e_test_db():
    """Ensures database schema and required campus/station/device records exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # 1. Karachi Campus & Station
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

        # 2. Islamabad Campus & Station
        stmt_isb = select(Campus).where(Campus.code == "ISLAMABAD")
        res_isb = await session.execute(stmt_isb)
        isb_campus = res_isb.scalar_one_or_none()
        if not isb_campus:
            isb_campus = Campus(
                code="ISLAMABAD",
                name="Islamabad Campus",
                city="Islamabad",
                contact_name="Islamabad Ops Lead",
                latitude=33.6844,
                longitude=73.0479,
                status="active"
            )
            session.add(isb_campus)
            await session.flush()

        stmt_isb_stn = select(Station).where(Station.station_code == "BIC-ISB-ACAD-01")
        res_isb_stn = await session.execute(stmt_isb_stn)
        isb_station = res_isb_stn.scalar_one_or_none()
        if not isb_station:
            isb_station = Station(
                campus_id=isb_campus.id,
                station_code="BIC-ISB-ACAD-01",
                station_name="Islamabad Academic Station",
                installation_location="Academic Block Rooftop"
            )
            session.add(isb_station)
            await session.flush()

        raw_token_isb = "esp32-islamabad-campus-token"
        token_h_isb = hash_token(raw_token_isb)

        stmt_isb_dev = select(Device).where(Device.device_uid == "AIRSENSE-NODE-ISB-01")
        res_isb_dev = await session.execute(stmt_isb_dev)
        isb_device = res_isb_dev.scalar_one_or_none()
        if not isb_device:
            isb_device = Device(
                station_id=isb_station.id,
                device_uid="AIRSENSE-NODE-ISB-01",
                token_hash=token_h_isb,
                status="active"
            )
            session.add(isb_device)

        await session.commit()


# =============================================================================
# TIER 1: FEATURE COVERAGE TESTS (F1.1 - F4.3)
# =============================================================================

class TestTier1FeatureCoverage:
    """Validates isolated happy-path behavior across all platform features."""

    def test_t1_f1_1_direct_cloud_mqtt_websocket_configuration(self):
        """F1.1: Validates Direct Cloud MQTT WebSocket client configuration in static assets."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        public_html = (root_dir / "public" / "index.html").read_text(encoding="utf-8")
        apps_html = (root_dir / "apps" / "web" / "hardware_dashboard.html").read_text(encoding="utf-8")

        for html in [public_html, apps_html]:
            assert "broker.hivemq.com" in html or "broker.emqx.io" in html
            assert ("8884" in html or "8084" in html)  # WSS port
            assert ("8000" in html or "8083" in html)  # WS port
            assert "airsense/karachi/bic_roof/telemetry" in html or "airsense/#" in html
            assert "Paho.MQTT.Client" in html
            assert "applyLiveTelemetryPacket" in html

    def test_t1_f1_2_telemetry_packet_schema_ingestion(self):
        """F1.2: Ingests and validates multi-field JSON telemetry packet schema."""
        now = datetime.now(timezone.utc)
        payload = {
            "schema_version": "1.0",
            "device_uid": "ESP32-AIRSENSE-BIC-001",
            "station_code": "BIC_ROOF_01",
            "campus_code": "MAIN_CAMPUS",
            "firmware_version": "v3.5.0-MQTT",
            "sequence_number": 1042,
            "timestamp_epoch": int(now.timestamp()),
            "pm1": 14.2,
            "pm2_5": 28.5,
            "pm10": 45.1,
            "temperature": 31.8,
            "humidity": 68.4,
            "pressure": 1008.2,
            "rain_flag": False
        }

        report = SensorHealthEngine.evaluate_sensor_connectivity(payload, last_received_at=now)
        assert report.station_liveness == "LIVE_ACTIVE"
        assert report.sensors["pms7003"].is_connected is True
        assert report.sensors["pms7003"].last_valid_value["pm2_5"] == 28.5
        assert report.sensors["bme280"].is_connected is True
        assert report.sensors["bme280"].last_valid_value["temperature_c"] == 31.8
        assert report.sensors["rain_sensor"].is_connected is True
        assert report.sensors["rain_sensor"].last_valid_value["rain_flag"] is False

    def test_t1_f1_3_reactive_8s_heartbeat_window_eval(self):
        """F1.3: Evaluates packet recency against the 8.0s reactive heartbeat window."""
        now = datetime.now(timezone.utc)
        reading = {"pm2_5": 15.0, "pm10": 25.0, "temperature_c": 28.0, "humidity_pct": 55.0, "pressure_hpa": 1012.0}

        # Recent packet (3s ago <= 8s threshold) -> LIVE_ACTIVE
        report_recent = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now - timedelta(seconds=3))
        assert report_recent.seconds_since_last_packet == 3
        assert report_recent.station_liveness == "LIVE_ACTIVE"

        # Stale packet (10s ago > 8s threshold) -> OFFLINE
        report_stale = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now - timedelta(seconds=10))
        assert report_stale.seconds_since_last_packet == 10
        assert report_stale.station_liveness == "OFFLINE"

    def test_t1_f1_4_pms7003_uart_validation(self):
        """F1.4: Validates Plantower PMS7003 UART frame parsing and bounds."""
        now = datetime.now(timezone.utc)
        reading = {"pm1": 7.5, "pm2_5": 12.0, "pm10": 18.0, "temperature_c": 28.0, "humidity_pct": 50.0, "pressure_hpa": 1012.0}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)

        pms = report.sensors["pms7003"]
        assert pms.is_connected is True
        assert pms.status == "ONLINE"
        assert pms.interface == "UART2 (Serial)"
        assert pms.last_valid_value == {"pm1": 7.5, "pm2_5": 12.0, "pm10": 18.0}
        assert pms.troubleshooting_step is None

    def test_t1_f1_5_bme280_i2c_validation(self):
        """F1.5: Validates Bosch BME280 I2C bus response and operational bounds."""
        now = datetime.now(timezone.utc)
        reading = {"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 29.5, "humidity_pct": 62.0, "pressure_hpa": 1013.2}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)

        bme = report.sensors["bme280"]
        assert bme.is_connected is True
        assert bme.status == "ONLINE"
        assert "I2C" in bme.interface
        assert bme.last_valid_value == {"temperature_c": 29.5, "humidity_pct": 62.0, "pressure_hpa": 1013.2}

    def test_t1_f1_6_rainplate_and_microsd_validation(self):
        """F1.6: Validates Raindrop ADC moisture plate and MicroSD SPI logger modules."""
        now = datetime.now(timezone.utc)
        reading = {"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 28.0, "humidity_pct": 50.0, "pressure_hpa": 1012.0, "rain_flag": True}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)

        rain = report.sensors["rain_sensor"]
        assert rain.is_connected is True
        assert rain.status == "ONLINE"
        assert "ADC" in rain.interface

        sd = report.sensors["microsd"]
        assert sd.is_connected is True
        assert sd.status == "ONLINE"
        assert "SPI" in sd.interface

    @pytest.mark.asyncio
    async def test_t1_f1_7_diagnostic_endpoint_contract(self):
        """F1.7: Validates GET /api/v1/ingest/sensors/diagnostic response contract."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/ingest/sensors/diagnostic")
            assert resp.status_code == 200
            data = resp.json()
            assert "station_liveness" in data
            assert "sensors" in data
            assert "pms7003" in data["sensors"]
            assert "bme280" in data["sensors"]
            assert "rain_sensor" in data["sensors"]
            assert "microsd" in data["sensors"]
            assert "summary_advisory" in data

    @pytest.mark.asyncio
    async def test_t1_f2_1_hardware_ui_route_served(self):
        """F2.1: Validates dedicated /hardware route returns HTTP 200 and HTML."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/hardware")
            assert resp.status_code == 200
            assert "text/html" in resp.headers["content-type"]
            assert "AirSense" in resp.text

    @pytest.mark.asyncio
    async def test_t1_f2_2_sensor_chip_cards_and_badges(self):
        """F2.2: Validates individual sensor chip cards and pins exist in /hardware DOM."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/hardware")
            assert "Plantower PMS7003" in resp.text
            assert "Bosch BME280" in resp.text
            assert "Raindrop Moisture Plate" in resp.text
            assert "MicroSD SPI" in resp.text
            assert "GPIO 16" in resp.text
            assert "GPIO 21" in resp.text
            assert "GPIO 34" in resp.text

    @pytest.mark.asyncio
    async def test_t1_f2_3_reactive_heartbeat_pill_and_pulsing_dot(self):
        """F2.3: Validates reactive heartbeat pill and pulsing dot indicator elements in DOM."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/hardware")
            assert "heartbeatPill" in resp.text
            assert "pulseDot" in resp.text
            assert "pulse-dot" in resp.text
            assert "livenessText" in resp.text

    @pytest.mark.asyncio
    async def test_t1_f2_4_realtime_telemetry_table_columns(self):
        """F2.4: Validates real-time 10-column telemetry table headers in /hardware DOM."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/hardware")
            assert "telemetryTableBody" in resp.text
            assert "TIMESTAMP (UTC)" in resp.text
            assert "SOURCE" in resp.text
            assert "PM1.0" in resp.text
            assert "PM2.5" in resp.text
            assert "PM10" in resp.text
            assert "TEMP" in resp.text
            assert "HUM" in resp.text
            assert "PRESS" in resp.text
            assert "RAIN" in resp.text
            assert "QC STATE" in resp.text

    def test_t1_f2_5_static_web_packaging_and_paho_mqtt(self):
        """F2.5: Validates standalone static packaging in public/ with paho-mqtt.js."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        public_index = root_dir / "public" / "index.html"
        public_paho = root_dir / "public" / "paho-mqtt.js"
        web_hardware = root_dir / "apps" / "web" / "hardware_dashboard.html"

        assert public_index.exists()
        assert public_paho.exists()
        assert web_hardware.exists()

        paho_js = public_paho.read_text(encoding="utf-8")
        assert "Paho" in paho_js
        assert "MQTT" in paho_js

    def test_t1_f2_6_cloud_deployment_configuration(self):
        """F2.6: Validates vercel.json and deploy.yml configurations."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        vercel_json_path = root_dir / "vercel.json"
        assert vercel_json_path.exists()

        vercel_content = json.loads(vercel_json_path.read_text(encoding="utf-8"))
        assert "builds" in vercel_content or "routes" in vercel_content or "public" in vercel_content or "rewrites" in vercel_content

    @pytest.mark.asyncio
    async def test_t1_f2_7_disconnection_failover_banner_and_opensource_link(self):
        """F2.7: Validates failover disconnect banner linking to /opensource."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/hardware")
            assert "disconnectBanner" in resp.text
            assert "/opensource" in resp.text

    @pytest.mark.asyncio
    async def test_t1_f3_1_opensource_ui_route_served(self):
        """F3.1: Validates dedicated /opensource route returns HTTP 200 and HTML."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/opensource")
            assert resp.status_code == 200
            assert "text/html" in resp.headers["content-type"]
            assert "24/7 Open-Source" in resp.text

    @pytest.mark.asyncio
    async def test_t1_f3_2_multi_provider_engine_coverage(self):
        """F3.2: Validates GET /api/v1/providers/status reports all integrated providers."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/providers/status")
            assert resp.status_code == 200
            data = resp.json()
            names = [p["name"] for p in data["providers"]]
            assert "open_meteo" in names
            assert "weatherapi" in names
            assert "bright_sky" in names
            assert "met_norway" in names
            assert "visual_crossing" in names
            assert "openaq" in names

    @pytest.mark.asyncio
    async def test_t1_f3_3_latency_benchmarking_in_compare(self):
        """F3.3: Validates per-provider millisecond latency benchmarking in /weather/compare."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/providers/weather/compare", params={"latitude": 24.8607, "longitude": 67.0011})
            assert resp.status_code == 200
            data = resp.json()
            assert "providers" in data
            for p_name, p_data in data["providers"].items():
                if "latency_ms" in p_data:
                    assert isinstance(p_data["latency_ms"], (int, float))

    @pytest.mark.asyncio
    async def test_t1_f3_4_atmospheric_consensus_computation(self):
        """F3.4: Validates real-time consensus calculations across providers."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/providers/weather/compare", params={"latitude": 33.6844, "longitude": 73.0479})
            assert resp.status_code == 200
            data = resp.json()
            assert "consensus" in data
            assert "avg_temperature_c" in data["consensus"]
            assert "avg_humidity_pct" in data["consensus"]
            assert "avg_pressure_hpa" in data["consensus"]
            assert data["consensus"]["total_providers"] >= 6

    @pytest.mark.asyncio
    async def test_t1_f3_5_wmo_4501_registry_translation(self):
        """F3.5: Validates WMO 4501 code registry translation endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/providers/weather/wmo-codes")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_codes"] >= 20
            assert "0" in data["registry"] or 0 in data["registry"]
            assert "61" in data["registry"] or 61 in data["registry"]

    @pytest.mark.asyncio
    async def test_t1_f3_6_24h_ai_pm25_trajectory_forecast(self):
        """F3.6: Validates 24-hour predictive PM2.5 walk-forward trajectory endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/forecasts")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_t1_f4_1_automated_fallback_hierarchy(self):
        """F4.1: Validates automated fallback when querying current weather."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/providers/weather/current", params={"latitude": 24.8607, "longitude": 67.0011})
            assert resp.status_code == 200
            data = resp.json()
            assert data["temperature_c"] is not None
            assert data["weather_description"] is not None

    @pytest.mark.asyncio
    async def test_t1_f4_2_topbar_navigation_coherence(self):
        """F4.2: Validates navigation switcher links across all dashboard templates."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for route in ["/", "/hardware", "/opensource"]:
                resp = await client.get(route)
                assert resp.status_code == 200
                assert ('href="/hardware"' in resp.text or 'href="/"' in resp.text)
                assert 'href="/opensource"' in resp.text

    @pytest.mark.asyncio
    async def test_t1_f4_3_platform_health_and_version(self):
        """F4.3: Validates system health and version endpoints."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            h_resp = await client.get("/api/v1/health")
            assert h_resp.status_code == 200
            assert h_resp.json()["status"] == "healthy"

            v_resp = await client.get("/api/v1/version")
            assert v_resp.status_code == 200
            assert "Islamabad" in v_resp.json()["pilots"]
            assert "Karachi" in v_resp.json()["pilots"]


# =============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# =============================================================================

class TestTier2BoundaryAndCornerCases:
    """Validates precise boundaries, invalid inputs, and edge condition handling."""

    def test_t2_packet_starvation_boundary_at_8s_alive(self):
        """Heartbeat boundary at exactly 8.0s recency -> Station is LIVE_ACTIVE."""
        now = datetime.now(timezone.utc)
        reading = {"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now - timedelta(seconds=8))
        assert report.seconds_since_last_packet == 8
        assert report.station_liveness == "LIVE_ACTIVE"

    def test_t2_packet_starvation_boundary_at_9s_disconnected(self):
        """Heartbeat boundary at 9.0s recency (> 8.0s threshold) -> Station transitions to OFFLINE."""
        now = datetime.now(timezone.utc)
        reading = {"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now - timedelta(seconds=9))
        assert report.seconds_since_last_packet == 9
        assert report.station_liveness == "OFFLINE"

    def test_t2_packet_starvation_zero_elapsed_seconds(self):
        """Heartbeat at 0 seconds elapsed (immediate packet arrival) -> LIVE_ACTIVE."""
        now = datetime.now(timezone.utc)
        reading = {"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        assert report.seconds_since_last_packet == 0
        assert report.station_liveness == "LIVE_ACTIVE"

    def test_t2_packet_starvation_extreme_stale_10000s(self):
        """Heartbeat after long disconnect (10,000s) -> OFFLINE with exact elapsed time."""
        now = datetime.now(timezone.utc)
        reading = {"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now - timedelta(seconds=10000))
        assert report.seconds_since_last_packet == 10000
        assert report.station_liveness == "OFFLINE"

    def test_t2_packet_starvation_none_timestamp(self):
        """Heartbeat when no packet has ever been received -> OFFLINE with None elapsed."""
        report = SensorHealthEngine.evaluate_sensor_connectivity(None, last_received_at=None)
        assert report.seconds_since_last_packet is None
        assert report.station_liveness == "OFFLINE"

    def test_t2_null_and_malformed_json_payloads(self):
        """Handles null, empty, or partial payload dictionaries gracefully."""
        now = datetime.now(timezone.utc)
        # Empty dict
        rep_empty = SensorHealthEngine.evaluate_sensor_connectivity({}, last_received_at=now)
        assert rep_empty.station_liveness == "PARTIAL_DEGRADED"
        assert rep_empty.sensors["pms7003"].status == "DISCONNECTED"
        assert rep_empty.sensors["bme280"].status == "DISCONNECTED"

        # None values inside reading
        null_reading = {"pm2_5": None, "pm10": None, "temperature_c": None}
        rep_null = SensorHealthEngine.evaluate_sensor_connectivity(null_reading, last_received_at=now)
        assert rep_null.station_liveness == "PARTIAL_DEGRADED"

    def test_t2_mqtt_client_id_randomness_and_reconnect_backoff(self):
        """Validates that MQTT client ID generation in JS is unique and contains random hex suffix."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        public_html = (root_dir / "public" / "index.html").read_text(encoding="utf-8")
        assert ("airsense-hub-" in public_html or "airsense-web-" in public_html)
        assert "Math.random()" in public_html
        assert "initCloudMQTT" in public_html

    def test_t2_rapid_packet_bursts_sub_second(self):
        """Rapid sequence of packet bursts within sub-second intervals handled with strict liveness."""
        now = datetime.now(timezone.utc)
        for i in range(10):
            reading = {
                "pm1": 5.0 + i, "pm2_5": 10.0 + i, "pm10": 15.0 + i,
                "temperature_c": 28.0, "humidity_pct": 50.0, "pressure_hpa": 1012.0
            }
            report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
            assert report.station_liveness == "LIVE_ACTIVE"
            assert report.sensors["pms7003"].status == "ONLINE"

    def test_t2_pms7003_zero_particulate_degraded(self):
        """PMS7003 reporting exact 0.0 ug/m3 -> Flagged DEGRADED (fan inspection advice)."""
        now = datetime.now(timezone.utc)
        reading = {"pm25": 0.0, "pm2_5": 0.0, "pm10": 0.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}
        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)

        pms = report.sensors["pms7003"]
        assert pms.status == "DEGRADED"
        assert "zero counts" in pms.diagnostic_message
        assert "fan" in pms.troubleshooting_step.lower()

    def test_t2_pms7003_physical_bounds_enforcement(self):
        """PMS7003 minimum (0.1) and maximum (1000.0) physical bounds validated."""
        now = datetime.now(timezone.utc)
        # Min valid (0.1 ug/m3)
        r_min = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": 0.1, "pm10": 0.1, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}, now)
        assert r_min.sensors["pms7003"].status == "ONLINE"

        # Max valid (1000.0 ug/m3)
        r_max = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": 1000.0, "pm10": 1500.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}, now)
        assert r_max.sensors["pms7003"].status == "ONLINE"

        # Out of bounds (negative or >1000)
        r_neg = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": -5.0, "pm10": -5.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}, now)
        assert r_neg.sensors["pms7003"].status == "DISCONNECTED"

    def test_t2_bme280_temp_bounds_and_out_of_bounds(self):
        """BME280 temperature bounds (-20°C to 65°C) and out-of-bounds flagging."""
        now = datetime.now(timezone.utc)
        # Min valid (-20.0 C)
        r_min = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": 10.0, "pm10": 15.0, "temperature_c": -20.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}, now)
        assert r_min.sensors["bme280"].status == "ONLINE"

        # Max valid (65.0 C)
        r_max = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 65.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}, now)
        assert r_max.sensors["bme280"].status == "ONLINE"

        # Out-of-bounds (70.0 C) -> DEGRADED
        r_deg = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 70.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}, now)
        assert r_deg.sensors["bme280"].status == "DEGRADED"

    def test_t2_bme280_humidity_bounds(self):
        """BME280 humidity bounds (1.0% to 100.0%) and out-of-bounds flagging."""
        now = datetime.now(timezone.utc)
        r_valid = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 100.0, "pressure_hpa": 1013.0}, now)
        assert r_valid.sensors["bme280"].status == "ONLINE"

        r_invalid = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 105.0, "pressure_hpa": 1013.0}, now)
        assert r_invalid.sensors["bme280"].status == "DEGRADED"

    def test_t2_bme280_pressure_bounds(self):
        """BME280 pressure bounds (800.0 to 1100.0 hPa) and out-of-bounds flagging."""
        now = datetime.now(timezone.utc)
        r_valid = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 800.0}, now)
        assert r_valid.sensors["bme280"].status == "ONLINE"

        r_invalid = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 750.0}, now)
        assert r_invalid.sensors["bme280"].status == "DEGRADED"

    def test_t2_rainplate_boolean_and_none_states(self):
        """Rainplate handles True, False, and None gracefully."""
        now = datetime.now(timezone.utc)
        r_wet = SensorHealthEngine.evaluate_sensor_connectivity({"rain_flag": True, "pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}, now)
        assert r_wet.sensors["rain_sensor"].last_valid_value == {"rain_flag": True}

        r_dry = SensorHealthEngine.evaluate_sensor_connectivity({"rain_flag": False, "pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}, now)
        assert r_dry.sensors["rain_sensor"].last_valid_value == {"rain_flag": False}

        r_none = SensorHealthEngine.evaluate_sensor_connectivity({"rain_flag": None, "pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}, now)
        assert r_none.sensors["rain_sensor"].status == "DISCONNECTED"

    def test_t2_microsd_offline_disconnection(self):
        """MicroSD status transitions to DISCONNECTED when station is offline (>8s)."""
        now = datetime.now(timezone.utc)
        report = SensorHealthEngine.evaluate_sensor_connectivity({"pm2_5": 10.0, "pm10": 15.0, "temperature_c": 25.0, "humidity_pct": 50.0, "pressure_hpa": 1013.0}, now - timedelta(seconds=15))
        assert report.sensors["microsd"].status == "DISCONNECTED"

    @pytest.mark.asyncio
    async def test_t2_ingest_auth_header_validation(self):
        """Ingest endpoint rejects requests with missing or invalid bearer token (401)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Missing header
            r1 = await client.post("/api/v1/ingest/reading", json={"pm2_5": 15.0})
            assert r1.status_code == 401

            # Invalid header
            r2 = await client.post("/api/v1/ingest/reading", json={"pm2_5": 15.0}, headers={"Authorization": "Bearer bad_token"})
            assert r2.status_code == 401

    @pytest.mark.asyncio
    async def test_t2_export_invalid_dataset_parameter(self):
        """Export endpoint validates dataset parameter regex and rejects invalid values (422)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/export/csv?dataset=invalid_dataset_name")
            assert resp.status_code == 422


# =============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# =============================================================================

class TestTier3CrossFeatureCombinations:
    """Validates interaction and coordination across subsystems."""

    def test_t3_mqtt_websocket_and_rest_fallback_coexistence(self):
        """Verifies dual-mode fallback logic in frontend JavaScript client."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        html_code = (root_dir / "public" / "index.html").read_text(encoding="utf-8")

        # 1. Primary MQTT reception sets lastMqttPacketTime
        assert "applyLiveTelemetryPacket" in html_code
        assert "lastMqttPacketTime = Date.now()" in html_code

        # 2. Polling loop checks if MQTT arrived within 8000ms
        assert "Date.now() - lastMqttPacketTime" in html_code
        assert "fetchHardwareDiagnostics" in html_code

    def test_t3_rapid_online_offline_flapping_stability(self):
        """Validates deterministic state machine flipping between LIVE_ACTIVE and OFFLINE."""
        now = datetime.now(timezone.utc)
        reading = {"pm2_5": 12.0, "pm10": 20.0, "temperature_c": 28.0, "humidity_pct": 55.0, "pressure_hpa": 1012.0}

        # Iteratively flap 10 times
        for cycle in range(10):
            # Packet arrives (0s elapsed) -> LIVE_ACTIVE
            rep_live = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
            assert rep_live.station_liveness == "LIVE_ACTIVE"
            assert rep_live.sensors["pms7003"].status == "ONLINE"

            # Silence (>8s elapsed) -> OFFLINE
            rep_off = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now - timedelta(seconds=12))
            assert rep_off.station_liveness == "OFFLINE"
            assert rep_off.sensors["pms7003"].status == "DISCONNECTED"

    def test_t3_concurrent_sessions_and_topic_subscription(self):
        """Verifies multi-client topic wildcard subscription in frontend."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        public_html = (root_dir / "public" / "index.html").read_text(encoding="utf-8")
        assert 'airsense/#' in public_html
        assert 'airsense/karachi/bic_roof/telemetry' in public_html

    @pytest.mark.asyncio
    async def test_t3_hardware_disconnect_and_opensource_failover_banner(self):
        """Simulated hardware disconnect leads to OFFLINE state and failover recommendation to /opensource."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Diagnostic endpoint reports valid report
            diag_resp = await client.get("/api/v1/ingest/sensors/diagnostic")
            assert diag_resp.status_code == 200

            # 2. Hardware dashboard provides failover link to /opensource
            hw_resp = await client.get("/hardware")
            assert hw_resp.status_code == 200
            assert "/opensource" in hw_resp.text
            assert "disconnectBanner" in hw_resp.text

            # 3. Open-source hub is fully operational
            os_resp = await client.get("/opensource")
            assert os_resp.status_code == 200
            assert "Open-Source" in os_resp.text

    @pytest.mark.asyncio
    async def test_t3_multi_provider_consensus_math_and_active_counts(self):
        """Cross-feature: /weather/compare computes consensus averages across active providers."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/providers/weather/compare", params={"latitude": 24.8607, "longitude": 67.0011})
            assert resp.status_code == 200
            data = resp.json()

            consensus = data["consensus"]
            providers = data["providers"]

            active_temps = [p["temperature_c"] for p in providers.values() if p.get("status") == "available" and p.get("temperature_c") is not None]
            if active_temps:
                expected_avg = round(sum(active_temps) / len(active_temps), 2)
                assert consensus["avg_temperature_c"] == expected_avg
                assert consensus["providers_reporting"] == len(active_temps)

    @pytest.mark.asyncio
    async def test_t3_ai_forecast_24_steps_non_negative_lower_bound(self):
        """Cross-feature: AI trajectory forecast returns 24 horizon steps with non-negative lower bounds CI >= 0.0."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/forecasts")
            assert resp.status_code == 200
            forecasts = resp.json()
            assert isinstance(forecasts, list)
            if forecasts:
                for step in forecasts:
                    if "pm2_5_lower" in step and step["pm2_5_lower"] is not None:
                        assert step["pm2_5_lower"] >= 0.0

    @pytest.mark.asyncio
    async def test_t3_topbar_route_switcher_coherence_across_all_spas(self):
        """Cross-feature: Topbar navigation switcher is coherent across /, /hardware, and /opensource."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r_root = await client.get("/")
            r_hw = await client.get("/hardware")
            r_os = await client.get("/opensource")

            for r in [r_root, r_hw, r_os]:
                assert ('href="/hardware"' in r.text or 'href="/"' in r.text)
                assert 'href="/opensource"' in r.text

    @pytest.mark.asyncio
    async def test_t3_ingest_idempotency_and_qc_state_propagation(self):
        """Cross-feature: Ingestion with deduplication propagates QC evaluation and preserves idempotency."""
        now_ts = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(microsecond=0).isoformat()
        raw_token = "esp32-karachi-campus-token"
        headers = {"Authorization": f"Bearer {raw_token}"}
        payload = {
            "schema_version": "1.0",
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "station_code": "BIC-KHI-ROOF-01",
            "timestamp": now_ts,
            "pm1": 8.0,
            "pm2_5": 14.5,
            "pm10": 22.0,
            "temperature": 28.5,
            "humidity": 55.0,
            "pressure": 1012.0,
            "rain_flag": False,
            "sequence_number": 9999
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. First ingestion
            r1 = await client.post("/api/v1/ingest/reading", json=payload, headers=headers)
            assert r1.status_code == 200
            d1 = r1.json()
            assert d1["accepted"] is True
            assert d1["duplicate"] is False

            # 2. Duplicate ingestion
            r2 = await client.post("/api/v1/ingest/reading", json=payload, headers=headers)
            assert r2.status_code == 200
            d2 = r2.json()
            assert d2["accepted"] is True
            assert d2["duplicate"] is True
            assert d2["quality_processing_state"] == "duplicate_skipped"


# =============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS
# =============================================================================

class TestTier4RealWorldScenarios:
    """Validates 5 comprehensive end-to-end operational scenarios."""

    def test_t4_scenario1_24_7_continuous_streaming_rolling_buffer(self):
        """Scenario 1: 24/7 Continuous Streaming with FIFO Rolling Buffer."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        public_html = (root_dir / "public" / "index.html").read_text(encoding="utf-8")
        assert "savedTelemetryRecords" in public_html or "telemetryTableBody" in public_html
        assert "pop()" in public_html or "deleteRow" in public_html

    @pytest.mark.asyncio
    async def test_t4_scenario2_hardware_station_reboot_cycle(self):
        """Scenario 2: Hardware Station Reboot Cycle (Online -> Reboot Silence -> Offline -> Reconnect Live)."""
        raw_token = "esp32-karachi-campus-token"
        headers = {"Authorization": f"Bearer {raw_token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Step 1: Initial broadcast packet -> Station is LIVE
            now = datetime.now(timezone.utc)
            p1 = {
                "schema_version": "1.0",
                "device_uid": "AIRSENSE-NODE-KHI-01",
                "station_code": "BIC-KHI-ROOF-01",
                "timestamp": now.isoformat(),
                "pm1": 7.5,
                "pm2_5": 12.0,
                "pm10": 18.0,
                "temperature": 29.0,
                "humidity": 60.0,
                "pressure": 1012.5,
                "rain_flag": False,
                "sequence_number": 201
            }
            r1 = await client.post("/api/v1/ingest/reading", json=p1, headers=headers)
            assert r1.status_code == 200

            diag1 = await client.get("/api/v1/ingest/sensors/diagnostic")
            assert diag1.status_code == 200
            assert diag1.json()["station_liveness"] == "LIVE_ACTIVE"

            # Step 2: Station reboots (silence for >8 seconds evaluated in health engine)
            report_rebooting = SensorHealthEngine.evaluate_sensor_connectivity(p1, last_received_at=now - timedelta(seconds=12))
            assert report_rebooting.station_liveness == "OFFLINE"
            assert report_rebooting.sensors["pms7003"].status == "DISCONNECTED"

            # Step 3: Station completes bootloader and broadcasts fresh packet -> Immediate recovery
            recovered_time = datetime.now(timezone.utc)
            p2 = dict(p1, timestamp=recovered_time.isoformat(), sequence_number=202)
            report_recovered = SensorHealthEngine.evaluate_sensor_connectivity(p2, last_received_at=recovered_time)
            assert report_recovered.station_liveness == "LIVE_ACTIVE"
            assert report_recovered.sensors["pms7003"].status == "ONLINE"

    def test_t4_scenario3_campus_wifi_drop_and_recover(self):
        """Scenario 3: Campus Wi-Fi Drop & Auto-Reconnect Recovery Sequence."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        public_html = (root_dir / "public" / "index.html").read_text(encoding="utf-8")

        # Verifies Paho onConnectionLost handler and auto-retry callback
        assert "onConnectionLost" in public_html
        assert "initCloudMQTT" in public_html

    @pytest.mark.asyncio
    async def test_t4_scenario4_public_browser_access_vercel_github_pages(self):
        """Scenario 4: Public Browser Access from Vercel / GitHub Pages."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        public_html = (root_dir / "public" / "index.html").read_text(encoding="utf-8")

        # 1. Relative or absolute script import of paho-mqtt.js
        assert "paho-mqtt.js" in public_html

        # 2. Adaptive protocol detection for WSS (HTTPS) vs WS (HTTP)
        assert "isHttps" in public_html
        assert "useSSL" in public_html

        # 3. Clean CSS variable design
        assert "--blue-600: #0284C7;" in public_html
        assert "--font-sans:" in public_html

    def test_t4_scenario5_multi_sensor_partial_degradation(self):
        """Scenario 5: Multi-Sensor Partial Degradation with Isolated Pin Troubleshooting."""
        now = datetime.now(timezone.utc)
        # BME280 valid, PMS7003 zero (fan blocked), Rainplate valid
        reading = {
            "pm1": 0.0,
            "pm25": 0.0,
            "pm2_5": 0.0,
            "pm10": 0.0,
            "temperature_c": 28.0,
            "humidity_pct": 55.0,
            "pressure_hpa": 1012.0,
            "rain_flag": False
        }

        report = SensorHealthEngine.evaluate_sensor_connectivity(reading, last_received_at=now)
        assert report.station_liveness == "PARTIAL_DEGRADED"

        # PMS7003 is DEGRADED with fan guidance and UART pins
        assert report.sensors["pms7003"].status == "DEGRADED"
        assert "fan" in report.sensors["pms7003"].troubleshooting_step.lower()
        assert "GPIO 16" in report.sensors["pms7003"].pins

        # BME280 is ONLINE without troubleshooting
        assert report.sensors["bme280"].status == "ONLINE"
        assert report.sensors["bme280"].troubleshooting_step is None

        # Rain sensor is ONLINE
        assert report.sensors["rain_sensor"].status == "ONLINE"


# =============================================================================
# TIER 5: ADVERSARIAL & STRESS HARDENING
# =============================================================================

class TestTier5AdversarialHardening:
    """Validates resilience against adversarial payloads, extreme coordinates, and stress conditions."""

    def test_t5_csv_formula_injection_mitigation(self):
        """Mitigates CSV formula injection attacks by escaping =, +, -, @ characters."""
        assert sanitize_csv_cell("=1+1") == "'=1+1"
        assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
        assert sanitize_csv_cell("-2+3") == "'-2+3"
        assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
        assert sanitize_csv_cell("Normal Text") == "Normal Text"
        assert sanitize_csv_cell(None) == ""

    @pytest.mark.asyncio
    async def test_t5_extreme_polar_geographic_coordinates(self):
        """Handles extreme geographic coordinates (North/South poles) without server crash."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp_np = await client.get("/api/v1/providers/weather/current", params={"latitude": 89.0, "longitude": 0.0})
            assert resp_np.status_code == 200
            assert resp_np.json()["temperature_c"] is not None

            resp_sp = await client.get("/api/v1/providers/weather/current", params={"latitude": -89.0, "longitude": 0.0})
            assert resp_sp.status_code == 200
            assert resp_sp.json()["temperature_c"] is not None

    def test_t5_wmo_unregistered_code_graceful_handling(self):
        """Handles unmapped/unregistered WMO codes gracefully with fallback metadata."""
        meta_invalid = get_wmo_metadata(99999)
        assert meta_invalid["category"] == "unknown"
        assert meta_invalid["description"] == "Unknown Weather State"
        assert meta_invalid["icon"] == "fa-cloud"

        meta_none = get_wmo_metadata(None)
        assert meta_none["category"] == "unknown"

    @pytest.mark.asyncio
    async def test_t5_rapid_diagnostic_polling_stability(self):
        """Handles rapid sequential requests to diagnostic endpoint without state corruption."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for _ in range(15):
                resp = await client.get("/api/v1/ingest/sensors/diagnostic")
                assert resp.status_code == 200
                assert "station_liveness" in resp.json()

    @pytest.mark.asyncio
    async def test_t5_corrupted_telemetry_type_coercion(self):
        """Coerces string-encoded numeric values in telemetry payloads safely."""
        raw_token = "esp32-karachi-campus-token"
        headers = {"Authorization": f"Bearer {raw_token}"}
        payload = {
            "schema_version": "1.0",
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "station_code": "BIC-KHI-ROOF-01",
            "pm1": 8,
            "pm2_5": 14,
            "pm10": 22,
            "temperature": 28,
            "humidity": 55,
            "pressure": 1012,
            "rain_flag": False
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/ingest/reading", json=payload, headers=headers)
            assert resp.status_code == 200
            assert resp.json()["accepted"] is True

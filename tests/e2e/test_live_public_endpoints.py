"""AirSense Pakistan - Live Public HTTPS Endpoints & Verification Test Suite.

Rigorously verifies:
1. Production endpoint behavior for all 5 endpoints (Liveness, Readiness, Telemetry Feed, Ingest Reading, Sensor Diagnostics).
2. scripts/verify_live_endpoints.py verification suite behavior under success and failure modes.
3. Hardware serial bridge simulation forwarding to cloud ingestion routes.
"""

import time
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from apps.api.main import app
from scripts.verify_live_endpoints import run_live_verification, DEFAULT_BASE_URL, DEVICE_TOKEN
from scripts.airsense_serial_live_bridge import run_simulation_mode, push_to_endpoint


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


class TestLivePublicEndpointsHarness:
    """Verifies that the 5 production endpoints conform to specification."""

    def test_endpoint_1_liveness_probe(self, client):
        """GET /api/v1/health/liveness returns HTTP 200 with status 'healthy'."""
        resp = client.get("/api/v1/health/liveness")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") in ("healthy", "ok")
        assert data.get("process") == "running"

    def test_endpoint_2_readiness_probe(self, client):
        """GET /api/v1/health/readiness returns HTTP 200 with database connected."""
        resp = client.get("/api/v1/health/readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("database", {}).get("connected") is True
        assert data.get("storage", {}).get("disk_writable") is True

    def test_endpoint_3_weather_telemetry_feed(self, client):
        """GET /api/v1/providers/weather/telemetry-feed returns HTTP 200 with 60s cadence."""
        resp = client.get("/api/v1/providers/weather/telemetry-feed", params={"limit": 5, "latitude": 24.8607, "longitude": 67.0011})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        assert data.get("cadence_seconds") == 60
        assert len(data.get("records", [])) > 0

    def test_endpoint_4_live_ingest_reading(self, client):
        """POST /api/v1/ingest/reading accepts valid payload and returns accepted: true."""
        payload = {
            "schema_version": "1.0",
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "station_code": "BIC-KHI-ROOF-01",
            "campus_code": "KARACHI",
            "sequence_number": int(time.time()) % 100000,
            "timestamp_epoch": int(time.time()),
            "pm1": 8.0,
            "pm2_5": 15.0,
            "pm10": 22.0,
            "temperature": 29.5,
            "humidity": 60.0,
            "pressure": 1012.0,
            "gas_resistance_kohm": 45.0,
            "rain_flag": False,
            "sensor_health": {"pms7003": "OK", "bme280": "OK", "rain": "OK", "microsd": "OK"},
            "firmware_version": "v3.5.0-PROD-VERIFY",
            "transmission_mode": "E2E_VERIFICATION_HARNESS"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Device-Token": DEVICE_TOKEN
        }
        resp = client.post("/api/v1/ingest/reading", json=payload, headers=headers)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data.get("accepted") is True
        assert "ingestion_id" in data

    def test_endpoint_5_sensor_diagnostics(self, client):
        """GET /api/v1/ingest/sensors/diagnostic returns HTTP 200 with station diagnostic report."""
        resp = client.get("/api/v1/ingest/sensors/diagnostic")
        assert resp.status_code == 200
        data = resp.json()
        assert "station_code" in data
        assert "station_liveness" in data
        assert data["station_liveness"] in ("LIVE_ACTIVE", "ONLINE", "PARTIAL_DEGRADED", "OFFLINE")
        assert "sensors" in data
        assert "pms7003" in data["sensors"]
        assert "bme280" in data["sensors"]


class TestVerificationSuiteLogic:
    """Verifies the logic of run_live_verification in scripts/verify_live_endpoints.py."""

    @patch("httpx.Client.get")
    @patch("httpx.Client.post")
    def test_run_live_verification_success_path(self, mock_post, mock_get):
        """run_live_verification returns True when all 5 endpoints return HTTP 200."""
        # Mock warm-up and GET endpoints
        def get_side_effect(url, **kwargs):
            mock_res = MagicMock()
            mock_res.status_code = 200
            if "/api/v1/health/liveness" in url:
                mock_res.json.return_value = {"status": "healthy", "process": "running"}
            elif "/api/v1/health/readiness" in url:
                mock_res.json.return_value = {
                    "status": "ready",
                    "database": {"connected": True},
                    "storage": {"disk_writable": True},
                    "background_scheduler": {"is_running": True}
                }
            elif "/api/v1/providers/weather/telemetry-feed" in url:
                mock_res.json.return_value = {
                    "status": "success",
                    "cadence_seconds": 60,
                    "records": [{"observed_at": "2026-09-04T12:00:00Z", "temperature": 30.0}]
                }
            elif "/api/v1/ingest/sensors/diagnostic" in url:
                mock_res.json.return_value = {
                    "station_code": "BIC-KHI-ROOF-01",
                    "station_liveness": "LIVE_ACTIVE",
                    "seconds_since_last_packet": 1,
                    "sensors": {"pms7003": {"status": "ONLINE"}}
                }
            return mock_res

        mock_get.side_effect = get_side_effect

        mock_post_res = MagicMock()
        mock_post_res.status_code = 200
        mock_post_res.json.return_value = {"accepted": True, "ingestion_id": "test-uuid-123"}
        mock_post.return_value = mock_post_res

        success = run_live_verification("https://mock-live-endpoint.trycloudflare.com")
        assert success is True

    @patch("httpx.Client.get")
    def test_run_live_verification_failure_path(self, mock_get):
        """run_live_verification returns False when an endpoint returns HTTP 500 or fails."""
        mock_res = MagicMock()
        mock_res.status_code = 500
        mock_res.json.return_value = {"detail": "Internal Server Error"}
        mock_get.return_value = mock_res

        success = run_live_verification("https://mock-failing-endpoint.trycloudflare.com")
        assert success is False


class TestSerialBridgeSimulationToCloud:
    """Verifies that simulation mode forwards packets to cloud URL."""

    @patch("scripts.airsense_serial_live_bridge.push_to_endpoint", return_value=True)
    def test_simulation_forwards_to_cloud(self, mock_push):
        """run_simulation_mode triggers push_to_endpoint with cloud URL."""
        cloud_url = "https://forums-surfaces-reef-stands.trycloudflare.com/api/v1/ingest/reading"
        payload = run_simulation_mode(cloud_url=cloud_url, local_url="http://127.0.0.1:8000/api/v1/ingest/reading", wait_for_completion=True)

        assert payload is not None
        assert payload["transmission_mode"] == "SERIAL_BRIDGE_SIMULATE"
        assert payload["pm2_5"] > 0
        assert mock_push.called

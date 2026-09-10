"""Tests validating the 5 flapping and data consistency fixes across firmware, bridge, routers, and dashboards."""

import pytest
import re
from pathlib import Path
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
from apps.api.main import app
from scripts.airsense_serial_live_bridge import (
    build_telemetry_payload,
    parse_serial_line,
    push_telemetry_dual_async,
)


@pytest.mark.asyncio
async def test_ready_endpoint_contract_consistency():
    """Verifies that /ready always returns database as a string contract."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Normal connected case
        resp = await client.get("/api/v1/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert isinstance(data["database"], str)
        assert data["database"] == "connected"

        # 2. Deep probe endpoint still returns structured dict
        resp_deep = await client.get("/api/v1/health/readiness")
        assert resp_deep.status_code == 200
        data_deep = resp_deep.json()
        assert isinstance(data_deep["database"], dict)
        assert data_deep["database"]["connected"] is True


@pytest.mark.asyncio
async def test_ready_endpoint_disconnected_fallback():
    """Verifies that if database execution fails, /ready returns database: 'disconnected' (string)."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("Connection lost")

    from apps.api.db.session import get_db_session
    app.dependency_overrides[get_db_session] = lambda: mock_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/ready")
            assert resp.status_code == 503
            data = resp.json()["detail"]
            assert data["database"] == "disconnected"
            assert data["status"] == "degraded"
    finally:
        app.dependency_overrides.pop(get_db_session, None)


def test_bridge_preserves_rain_adc_and_gas_in_json():
    """Verifies parse_serial_line extracts and preserves rain_adc from JSON telemetry."""
    json_line = '[JSON_TELEMETRY] {"sequence_number": 44, "pm2_5": 14.5, "temperature": 27.2, "rain_adc": 1820, "gas_resistance_kohm": 38.5}'
    payload, is_end = parse_serial_line(json_line, {})
    assert is_end is True
    assert payload is not None
    assert payload["sequence_number"] == 44
    assert payload["pm2_5"] == 14.5
    assert payload["rain_adc"] == 1820
    assert payload["gas_resistance_kohm"] == 38.5


def test_firmware_timeout_and_sync_configuration():
    """Verifies that firmware source code contains the required 2500ms timeouts and frame sync."""
    firmware_path = Path("scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino")
    assert firmware_path.exists()
    content = firmware_path.read_text(encoding="utf-8")

    # 1. Check socket connect timeout is 2500ms
    assert "mqttClient.connect(broker, MQTT_PORT, 2500)" in content

    # 2. Check CONNACK timeout is 2500ms
    assert "millis() - t0 < 2500" in content

    # 3. Check sliding window sync (0x42 0x4D)
    assert "0x42" in content and "0x4D" in content

    # 4. Check stale byte flush condition (flushes when > 32 bytes accumulated)
    assert "pmsSerial.available() > 32" in content


def test_frontend_dashboards_stale_badges_and_empty_filtering():
    """Verifies all 4 dashboard HTML files contain STALE badge fallback and guard against empty records."""
    dashboard_files = [
        Path("public/hardware.html"),
        Path("public/index.html"),
        Path("apps/web/hardware_dashboard.html"),
        Path("apps/web/index.html"),
    ]

    for f in dashboard_files:
        assert f.exists()
        content = f.read_text(encoding="utf-8")

        # 1. Silence watchdog threshold is 35s
        assert "elapsed <= 35" in content

        # 2. Clamped REST lag
        assert "Date.now() - 2000" in content or "Date.now() - lagMs" in content

        # 3. STALE badge used in renderDisconnectedUI
        assert "status-stale" in content

        # 4. STALE badge preserved in renderConnectedUI for transient sensor glitches
        # Check that renderConnectedUI has the check for preserving existing text
        assert "pVal.textContent && pVal.textContent.trim() !== '--'" in content
        assert "bVal.textContent && bVal.textContent.trim() !== '--'" in content

        # 5. addTelemetryRecord guards against empty or rain-only records
        assert "hasRealReading" in content

        # 6. applyLiveTelemetryPacket rejects null-only readings
        assert "hasSensorData" in content

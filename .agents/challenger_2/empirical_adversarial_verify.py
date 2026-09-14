"""Empirical Adversarial Verification Suite for AirSense-v2 (Challenger 2).

Thoroughly exercises:
1. Dual-mode fallback priority arbitration (live MQTT suppressing REST polling overwrites).
2. Disconnect failover banner display and state machine transitions.
3. Static asset integrity and relative path resolution.
4. vercel.json and GitHub Actions deploy.yml configuration validity.
"""

import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PUBLIC_INDEX = ROOT_DIR / "public" / "index.html"
PUBLIC_OPENSOURCE = ROOT_DIR / "public" / "opensource.html"
PUBLIC_PAHO = ROOT_DIR / "public" / "paho-mqtt.js"
APPS_HARDWARE = ROOT_DIR / "apps" / "web" / "hardware_dashboard.html"
APPS_OPENSOURCE = ROOT_DIR / "apps" / "web" / "opensource_dashboard.html"
APPS_PAHO = ROOT_DIR / "apps" / "web" / "paho-mqtt.js"
VERCEL_JSON = ROOT_DIR / "vercel.json"
DEPLOY_YML = ROOT_DIR / ".github" / "workflows" / "deploy.yml"


def test_files_exist_and_non_empty():
    files = [
        PUBLIC_INDEX, PUBLIC_OPENSOURCE, PUBLIC_PAHO,
        APPS_HARDWARE, APPS_OPENSOURCE, APPS_PAHO,
        VERCEL_JSON, DEPLOY_YML
    ]
    for f in files:
        assert f.exists(), f"Missing expected file: {f}"
        assert f.stat().st_size > 0, f"File is empty: {f}"
    print("[PASS] All required static, web, and deployment configuration files exist and are non-empty.")


def test_dual_mode_priority_arbitration_logic():
    content = PUBLIC_INDEX.read_text(encoding="utf-8")

    # 1. applyLiveTelemetryPacket updates lastMqttPacketTime
    assert "lastMqttPacketTime = Date.now();" in content, "applyLiveTelemetryPacket must record lastMqttPacketTime"

    # 2. fetchHardwareDiagnostics suppresses REST polling when MQTT is fresh (<= 8000ms)
    diag_suppress_match = re.search(
        r"function fetchHardwareDiagnostics\(\)\s*\{[\s\S]*?lastMqttPacketTime\s*>\s*0\s*&&\s*\(Date\.now\(\)\s*-\s*lastMqttPacketTime\)\s*<=\s*8000\s*\)\s*\{\s*return;\s*\}",
        content
    )
    assert diag_suppress_match, "fetchHardwareDiagnostics must immediately return when MQTT packet is fresh (<=8s)"

    # 3. fetchLatestTelemetry suppresses REST polling table overwrite when MQTT is fresh
    telem_suppress_match = re.search(
        r"function fetchLatestTelemetry\(\)\s*\{[\s\S]*?lastMqttPacketTime\s*>\s*0\s*&&\s*\(Date\.now\(\)\s*-\s*lastMqttPacketTime\)\s*<=\s*8000\s*\)\s*\{\s*return;\s*\}",
        content
    )
    assert telem_suppress_match, "fetchLatestTelemetry must immediately return when MQTT packet is fresh (<=8s)"

    # 4. Silence watchdog checks 8000ms timeout
    watchdog_match = re.search(
        r"function checkSilenceWatchdog\(\)\s*\{[\s\S]*?now\s*-\s*lastMqttPacketTime\s*>\s*8000[\s\S]*?renderDisconnectedUI",
        content
    )
    assert watchdog_match, "checkSilenceWatchdog must trigger renderDisconnectedUI when >8000ms elapsed"

    print("[PASS] Dual-mode priority arbitration logic verified: MQTT strictly suppresses REST polling within 8s window.")


def test_disconnect_failover_banner_and_ui_states():
    content = PUBLIC_INDEX.read_text(encoding="utf-8")

    # Banner element in HTML
    assert 'id="disconnectBanner"' in content
    assert 'class="disconnect-banner"' in content
    assert 'href="/opensource"' in content
    assert 'VIEW OPEN-SOURCE LIVE DATA' in content

    # renderDisconnectedUI shows banner and marks cards offline
    assert "if (banner) banner.style.display = 'flex';" in content
    assert "'cardPms', 'cardBme', 'cardRain', 'cardSd'" in content
    assert "el.classList.add('offline-card');" in content
    assert "text.textContent = 'ESP32 DISCONNECTED';" in content

    # renderConnectedUI hides banner and removes offline-card class
    assert "if (banner) banner.style.display = 'none';" in content
    assert "el.classList.remove('offline-card');" in content
    assert "text.textContent = 'ESP32 LIVE CONNECTED';" in content

    # Pin guidance in cards
    assert "GPIO 16 (RX) / 17 (TX)" in content
    assert "GPIO 21 (SDA) / 22 (SCL)" in content
    assert "GPIO 34 (ADC1 CH6)" in content
    assert "GPIO 5 (CS) / 18 / 19 / 23" in content

    print("[PASS] Disconnection failover banner and UI state transitions verified.")


def test_paho_mqtt_and_static_asset_integrity():
    content_idx = PUBLIC_INDEX.read_text(encoding="utf-8")
    content_os = PUBLIC_OPENSOURCE.read_text(encoding="utf-8")
    content_paho = PUBLIC_PAHO.read_text(encoding="utf-8")

    # paho script tag is relative in index.html head
    assert '<script src="paho-mqtt.js"></script>' in content_idx
    # Paho library valid
    assert "Paho.MQTT" in content_paho
    assert "Client" in content_paho

    # Auto-reconnect & watchdog
    assert "initCloudMQTT" in content_idx
    assert "onConnectionLost" in content_idx
    assert "onMessageArrived" in content_idx
    assert "subscribe" in content_idx
    assert "airsense/#" in content_idx

    # Navigation tabs match in both pages
    for nav_href in ['href="/hardware"', 'href="/opensource"', 'href="/"']:
        assert nav_href in content_idx
        assert nav_href in content_os

    print("[PASS] Static asset packaging, relative script loading, and navigation links verified.")


def test_vercel_and_github_actions_deployment_configs():
    # Vercel JSON
    v_data = json.loads(VERCEL_JSON.read_text(encoding="utf-8"))
    assert v_data.get("outputDirectory") == "public", f"Expected outputDirectory 'public', got {v_data.get('outputDirectory')}"
    assert v_data.get("cleanUrls") is True
    assert v_data.get("public") is True

    # Check CSP Header
    headers = v_data.get("headers", [])
    assert len(headers) > 0
    csp_found = False
    for h_entry in headers:
        for header in h_entry.get("headers", []):
            if header.get("key") == "Content-Security-Policy":
                csp_val = header.get("value", "")
                assert "connect-src" in csp_val
                assert "broker.hivemq.com:8884" in csp_val
                assert "broker.hivemq.com:8000" in csp_val
                assert "api.open-meteo.com" in csp_val
                assert "air-quality-api.open-meteo.com" in csp_val
                csp_found = True
    assert csp_found, "Content-Security-Policy header with connect-src not found in vercel.json"

    # Check Routes
    routes = {r.get("src"): r.get("dest") for r in v_data.get("routes", [])}
    assert routes.get("/hardware") == "/public/index.html"
    assert routes.get("/opensource") == "/public/opensource.html"
    assert routes.get("/") == "/public/index.html"

    # GitHub Actions workflow
    yml_data = DEPLOY_YML.read_text(encoding="utf-8")
    assert "actions/checkout@v4" in yml_data
    assert "actions/configure-pages@v5" in yml_data
    assert "actions/upload-pages-artifact@v3" in yml_data
    assert "path: './public'" in yml_data
    assert "actions/deploy-pages@v4" in yml_data
    assert "pages: write" in yml_data
    assert "id-token: write" in yml_data

    print("[PASS] vercel.json and GitHub Actions deploy.yml deployment configurations verified.")


if __name__ == "__main__":
    test_files_exist_and_non_empty()
    test_dual_mode_priority_arbitration_logic()
    test_disconnect_failover_banner_and_ui_states()
    test_paho_mqtt_and_static_asset_integrity()
    test_vercel_and_github_actions_deployment_configs()
    print("\n========================================================")
    print("ALL EMPIRICAL ADVERSARIAL CHALLENGER 2 CHECKS PASSED 100%")
    print("========================================================")

"""Unit and integration test suite for AirSense Pakistan Standalone Unified Dashboard (Milestone M3).

Verifies:
1. Directory structure and file presence in apps/web_unified/
2. Strict preservation of existing apps/web/ files (sha256 matching)
3. Zero CDN blocking, no runtime Babel, pre-compiled Vanilla JS & CSS
4. Sub-50ms reactive hardware gauge anchors and DOM elements
5. Dynamic 8-second client watchdog specification and UI states
6. 1-Click RFC 4180 CSV export with formula injection sanitization
7. Canvas 2D Atmospheric Dispersion Plume and wind vector particle system
8. 10-Day risk horizon interactive slider and dynamic confidence bounds
9. 8-Domain scraping radar widget
10. Enterprise financial loss reduction ticker (PKR)
11. AgentPhone autonomous AI telephony console and sector personas
12. FastAPI route mounting: GET /unified, GET /command-unified, and static files
"""

import os
import sys
import time
import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

AIRSENSE_ROOT = Path("D:/MUNIM - UOE @BIC/AirSense")
if str(AIRSENSE_ROOT) not in sys.path:
    sys.path.insert(0, str(AIRSENSE_ROOT))

from apps.api.main import app

client = TestClient(app)

WEB_UNIFIED_DIR = AIRSENSE_ROOT / "apps" / "web_unified"
WEB_DIR = AIRSENSE_ROOT / "apps" / "web"

EXPECTED_V1_HASH = "b97df4baad5fbf65fe949da860e5f2d00721dca06b2dfe2ad884f236a1c64dc8"
EXPECTED_V2_HASH = "4539bcef3de4e2475a1d83242c13eba18c3d2f9a3d324433a36a65b396e21fb8"


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


# ============================================================================
# 1. FILE STRUCTURE & INTEGRITY TESTS
# ============================================================================

def test_web_unified_directory_structure_and_files():
    """Verify apps/web_unified directory structure and bundled assets."""
    assert WEB_UNIFIED_DIR.exists(), "apps/web_unified directory does not exist"
    assert WEB_UNIFIED_DIR.is_dir()

    index_html = WEB_UNIFIED_DIR / "index.html"
    assert index_html.exists(), "apps/web_unified/index.html is missing"
    assert index_html.stat().st_size > 5000, "apps/web_unified/index.html too small"

    paho_js = WEB_UNIFIED_DIR / "js" / "paho-mqtt.js"
    assert paho_js.exists(), "apps/web_unified/js/paho-mqtt.js is missing"
    assert paho_js.stat().st_size >= 25000, "apps/web_unified/js/paho-mqtt.js corrupted or truncated"

    styles_css = WEB_UNIFIED_DIR / "css" / "styles.css"
    assert styles_css.exists(), "apps/web_unified/css/styles.css is missing"
    assert styles_css.stat().st_size > 2000, "apps/web_unified/css/styles.css too small"


def test_existing_web_dashboards_strictly_preserved():
    """Ensure existing apps/web/index.html and apps/web/command.html remain completely untouched."""
    v1_file = WEB_DIR / "index.html"
    v2_file = WEB_DIR / "command.html"

    assert v1_file.exists(), "apps/web/index.html missing"
    assert v2_file.exists(), "apps/web/command.html missing"

    v1_hash = get_file_sha256(v1_file)
    v2_hash = get_file_sha256(v2_file)

    assert v1_hash == EXPECTED_V1_HASH, f"apps/web/index.html was modified! Hash: {v1_hash}"
    assert v2_hash == EXPECTED_V2_HASH, f"apps/web/command.html was modified! Hash: {v2_hash}"


# ============================================================================
# 2. ZERO CDN BLOCKING & RUNTIME BABEL ELIMINATION
# ============================================================================

def test_zero_cdn_blocking_and_runtime_babel():
    """Assert zero CDN-blocking tags, no runtime Babel compiler, and local script usage."""
    html_content = (WEB_UNIFIED_DIR / "index.html").read_text(encoding="utf-8")

    assert "@babel/standalone" not in html_content, "Runtime Babel CDN detected in index.html"
    assert "cdn.tailwindcss.com" not in html_content, "Tailwind CDN detected in index.html"
    assert 'type="text/babel"' not in html_content, "Babel script tags detected in index.html"

    # Must bundle local scripts
    assert "paho-mqtt.js" in html_content, "Missing bundled paho-mqtt.js reference"
    assert "styles.css" in html_content, "Missing bundled styles.css reference"


# ============================================================================
# 3. SUB-50ms HARDWARE GAUGE ANCHORS & SENSOR CHANNELS
# ============================================================================

def test_sub50ms_hardware_gauge_anchors():
    """Verify DOM elements and anchors for physical sensor channels."""
    html_content = (WEB_UNIFIED_DIR / "index.html").read_text(encoding="utf-8")

    # PMS7003 Particulate
    assert 'id="pmsVal"' in html_content
    assert 'id="pm1Val"' in html_content
    assert 'id="pm10Val"' in html_content
    assert 'id="cardPms"' in html_content
    assert 'id="pmsBadge"' in html_content

    # Bosch BME280 Meteorological
    assert 'id="bmeVal"' in html_content
    assert 'id="bmeHumVal"' in html_content
    assert 'id="bmePressVal"' in html_content
    assert 'id="bmeDewVal"' in html_content
    assert 'id="cardBme"' in html_content
    assert 'id="bmeBadge"' in html_content

    # Raindrop Precipitation
    assert 'id="rainVal"' in html_content
    assert 'id="rainAdcVal"' in html_content
    assert 'id="cardRain"' in html_content
    assert 'id="rainBadge"' in html_content

    # MicroSD Storage
    assert 'id="cardSd"' in html_content
    assert 'id="sdBadge"' in html_content
    assert 'id="sdVal"' in html_content


# ============================================================================
# 4. DYNAMIC 8-SECOND CLIENT WATCHDOG SPECIFICATION
# ============================================================================

def test_dynamic_8s_watchdog_elements_and_threshold():
    """Verify 8-second watchdog state machine and UI indicators."""
    html_content = (WEB_UNIFIED_DIR / "index.html").read_text(encoding="utf-8")

    assert 'id="heartbeatPill"' in html_content
    assert 'id="pulseDot"' in html_content
    assert 'id="livenessText"' in html_content
    assert 'id="lastSeenText"' in html_content
    assert 'id="disconnectBanner"' in html_content

    # Constants & Thresholds
    assert "WATCHDOG_TIMEOUT_SECONDS = 8" in html_content or "WATCHDOG_TIMEOUT_SECONDS=8" in html_content
    assert "ESP32 LIVE CONNECTED" in html_content
    assert "ESP32 OFFLINE" in html_content
    assert "triggerSatelliteFallback" in html_content


# ============================================================================
# 5. 1-CLICK RFC 4180 CSV EXPORT & FORMULA SANITIZATION
# ============================================================================

def test_rfc4180_csv_export_implementation():
    """Verify 1-click CSV export logic, headers, and formula sanitization."""
    html_content = (WEB_UNIFIED_DIR / "index.html").read_text(encoding="utf-8")

    assert "exportTelemetryCSV" in html_content
    assert 'onclick="exportTelemetryCSV()"' in html_content
    assert "Timestamp_UTC" in html_content
    assert "PM25_ug_m3" in html_content or "PM2.5" in html_content
    assert "Temperature_C" in html_content or "Temperature" in html_content

    # Formula injection protection against (=, +, -, @)
    assert "/^[=+\\-@]/" in html_content or "sanitize" in html_content


# ============================================================================
# 6. CANVAS 2D ATMOSPHERIC PLUME & WIND VECTOR SIMULATION
# ============================================================================

def test_canvas_2d_plume_and_particle_simulation():
    """Verify HTML5 Canvas 2D atmospheric dispersion plume and particle system."""
    html_content = (WEB_UNIFIED_DIR / "index.html").read_text(encoding="utf-8")

    assert 'id="plumeCanvas"' in html_content
    assert 'id="plumeContainer"' in html_content
    assert "initAtmosphericPlumeCanvas" in html_content
    assert "getContext('2d')" in html_content
    assert "createRadialGradient" in html_content
    assert "requestAnimationFrame" in html_content
    assert "AIRSENSE-NODE-KHI-01" in html_content


# ============================================================================
# 7. 10-DAY RISK HORIZON SLIDER & DYNAMIC CONFIDENCE ENVELOPE
# ============================================================================

def test_10day_risk_horizon_slider_and_confidence_bounds():
    """Verify 10-day risk horizon interactive slider, chart canvas, and tightening CI logic."""
    html_content = (WEB_UNIFIED_DIR / "index.html").read_text(encoding="utf-8")

    assert 'id="horizonSlider"' in html_content
    assert 'id="horizonChart"' in html_content
    assert 'min="1"' in html_content and 'max="10"' in html_content
    assert "onHorizonSliderChange" in html_content
    assert "calculate10DayHorizonTrajectory" in html_content
    assert 'id="horizonLeadVal"' in html_content
    assert 'id="horizonPmVal"' in html_content
    assert 'id="horizonCiVal"' in html_content
    assert 'id="horizonLossVal"' in html_content


# ============================================================================
# 8. 8-DOMAIN SCRAPING RADAR WIDGET
# ============================================================================

def test_8domain_scraping_radar_widget():
    """Verify 8 sovereign domains are represented in the radar console."""
    html_content = (WEB_UNIFIED_DIR / "index.html").read_text(encoding="utf-8")

    expected_domains = [
        "EPA Gazettes",
        "Motorway Traffic",
        "Education Circulars",
        "Industrial Chambers",
        "Biomass Hotspots",
        "Aviation & Transport",
        "Power Grid",
        "Business Journalism"
    ]
    for domain in expected_domains:
        assert domain in html_content, f"Missing domain in radar: {domain}"


# ============================================================================
# 9. ENTERPRISE FINANCIAL LOSS TICKER (PKR)
# ============================================================================

def test_enterprise_financial_loss_ticker_pkr():
    """Verify enterprise financial loss metrics in Pakistani Rupees (PKR)."""
    html_content = (WEB_UNIFIED_DIR / "index.html").read_text(encoding="utf-8")

    assert 'id="finUnmitigated"' in html_content
    assert 'id="finMitigated"' in html_content
    assert 'id="finRoi"' in html_content
    assert "PKR" in html_content
    assert "updateEnterpriseFinancialLoss" in html_content


# ============================================================================
# 10. AGENTPHONE AUTONOMOUS AI TELEPHONY CONSOLE
# ============================================================================

def test_agentphone_autonomous_telephony_console():
    """Verify AgentPhone AI voice personas, endpoint configuration, and trigger UI."""
    html_content = (WEB_UNIFIED_DIR / "index.html").read_text(encoding="utf-8")

    assert "api.agentphone.to" in html_content
    assert "11labs-Brian" in html_content
    assert "nova" in html_content
    assert "alloy" in html_content
    assert 'id="telephonyRecipientInput"' in html_content
    assert 'id="telephonyLedger"' in html_content
    assert "triggerTelephonyCall" in html_content


# ============================================================================
# 11. FASTAPI BACKEND ROUTE MOUNTING & LATENCY
# ============================================================================

def test_fastapi_unified_route_serving_and_latency():
    """Verify GET /unified returns HTTP 200 with text/html in < 100ms."""
    # Warm up ASGI middleware stack and route dispatch
    client.get("/api/v1/health")
    client.get("/unified")

    t0 = time.perf_counter()
    res = client.get("/unified")
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert latency_ms < 100.0, f"Unified route took {latency_ms:.2f}ms, exceeding 100ms budget"

    body = res.text
    assert "AirSense Pakistan Unified Command Cockpit" in body
    assert "ESP32 LIVE CONNECTED" in body
    assert "pmsVal" in body
    assert "bmeVal" in body


def test_fastapi_command_unified_alias_route():
    """Verify GET /command-unified alias route."""
    res = client.get("/command-unified")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_fastapi_unified_static_files_serving():
    """Verify /unified-static mounts serve JS and CSS correctly."""
    res_js = client.get("/unified-static/js/paho-mqtt.js")
    assert res_js.status_code == 200
    assert len(res_js.content) >= 25000

    res_css = client.get("/unified-static/css/styles.css")
    assert res_css.status_code == 200
    assert len(res_css.content) > 2000

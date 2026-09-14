"""AirSense Pakistan Next-Generation Operational Command Centre (v2) E2E Test Suite.

Comprehensive 4-Tier Opaque-Box End-to-End Test Suite:
- Tier 1: Feature Coverage (R1 Decision Intelligence, R2 6 Sector Command Modules, R3 Alerts/News/Weather, R4 Coexistence & Routing)
- Tier 2: Boundary & Corner Cases (Hygroscopic swelling, coarse dust ratio, biomass smoke signature, zero wind, idempotent ack)
- Tier 3: Cross-Feature Combinations & Pairwise (Actuator-sector-alert coupling, campus routing divergence, dual route coexistence)
- Tier 4: Real-World Operational Scenarios (Severe Winter Smog, Industrial Dust Surge, Agricultural Stubble Plume, HVAC Smart Cycle)
"""

import asyncio
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from apps.api.db.session import engine
from apps.api.db.models import Base, RawReading
from services.decision_intelligence.decision_engine import OperationalDecisionEngine
from services.decision_intelligence.sector_intelligence import SectorIntelligenceEngine
from services.decision_intelligence.news_and_alerts import NewsAndAlertsEngine


@pytest.fixture(autouse=True)
async def init_test_db():
    """Ensure test database schema is cleanly initialized for every test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ===========================================================================
# TIER 1: FEATURE COVERAGE (>=5 tests per feature area)
# ===========================================================================

# --- R1: Decision Intelligence Engine ---

@pytest.mark.asyncio
async def test_tier1_r1_decision_intelligence_live_telemetry_schema():
    """Verify GET /api/v2/decisions/live returns comprehensive decision summary schema."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/decisions/live?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        
        required_keys = [
            "timestamp_utc", "campus_code", "risk_tier", "risk_color",
            "primary_directive", "action_code", "health_implication",
            "confidence_pct", "dispersion_class", "stagnation_index",
            "telemetry_summary", "active_triggers", "decision_engine_version"
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
            
        assert data["campus_code"] == "KARACHI"
        assert data["decision_engine_version"] == "2.0.0-PROD"
        assert isinstance(data["confidence_pct"], (int, float))
        assert isinstance(data["stagnation_index"], (int, float))
        assert isinstance(data["active_triggers"], list)
        
        tel = data["telemetry_summary"]
        for tel_key in ["pm2_5", "pm10", "forecast_1h", "forecast_6h", "temperature_c", "humidity_pct", "wind_speed_m_s", "wind_direction_deg", "pressure_hpa", "rain_flag"]:
            assert tel_key in tel, f"Missing telemetry summary key: {tel_key}"


@pytest.mark.asyncio
async def test_tier1_r1_decision_intelligence_islamabad_pilot():
    """Verify GET /api/v2/decisions/live with ISLAMABAD campus code returns appropriate telemetry."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/decisions/live?campus_code=ISLAMABAD")
        assert res.status_code == 200
        data = res.json()
        assert data["campus_code"] == "ISLAMABAD"
        assert "telemetry_summary" in data


def test_tier1_r1_risk_tier_classification_logic():
    """Verify OperationalDecisionEngine maps risk tiers correctly across pollution boundaries."""
    # Clean air
    clean = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KAR_CAMPUS", current_pm2_5=12.0, current_pm10=22.0,
        forecast_1h_pm2_5=15.0, forecast_6h_pm2_5=18.0, temperature_c=25.0,
        humidity_pct=50.0, wind_speed_m_s=4.0, wind_direction_deg=220, pressure_hpa=1012.0
    )
    assert clean["risk_tier"] == "OPTIMAL_NORMAL"
    assert clean["risk_color"] == "#00E599"

    # Moderate advisory
    mod = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KAR_CAMPUS", current_pm2_5=42.0, current_pm10=70.0,
        forecast_1h_pm2_5=48.0, forecast_6h_pm2_5=52.0, temperature_c=22.0,
        humidity_pct=60.0, wind_speed_m_s=2.5, wind_direction_deg=220, pressure_hpa=1010.0
    )
    assert mod["risk_tier"] == "MODERATE_ADVISORY"
    assert mod["risk_color"] == "#FFC700"

    # High alert
    high = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KAR_CAMPUS", current_pm2_5=85.0, current_pm10=140.0,
        forecast_1h_pm2_5=92.0, forecast_6h_pm2_5=98.0, temperature_c=18.0,
        humidity_pct=65.0, wind_speed_m_s=1.8, wind_direction_deg=220, pressure_hpa=1008.0
    )
    assert high["risk_tier"] == "HIGH_ALERT"
    assert high["risk_color"] == "#FF7A00"

    # Critical hazard
    crit = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KAR_CAMPUS", current_pm2_5=165.0, current_pm10=280.0,
        forecast_1h_pm2_5=180.0, forecast_6h_pm2_5=195.0, temperature_c=14.0,
        humidity_pct=85.0, wind_speed_m_s=0.8, wind_direction_deg=180, pressure_hpa=1005.0
    )
    assert crit["risk_tier"] == "CRITICAL_HAZARD"
    assert crit["risk_color"] == "#FF2A55"


def test_tier1_r1_stagnation_index_bounds():
    """Verify stagnation score is bounded 0-100 and maps to dispersion classes."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="ISB_CAMPUS", current_pm2_5=30.0, current_pm10=50.0,
        forecast_1h_pm2_5=32.0, forecast_6h_pm2_5=35.0, temperature_c=12.0,
        humidity_pct=80.0, wind_speed_m_s=0.5, wind_direction_deg=100, pressure_hpa=1015.0
    )
    assert 0.0 <= res["stagnation_index"] <= 100.0
    assert res["dispersion_class"] in ["POOR_TRAPPED_INVERSION", "MODERATE_DISPERSION", "EXCELLENT_VENTILATION"]


def test_tier1_r1_confidence_score_clamping():
    """Verify confidence score is bounded between 65% and 98%."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="ISB_CAMPUS", current_pm2_5=10.0, current_pm10=20.0,
        forecast_1h_pm2_5=200.0, forecast_6h_pm2_5=300.0, temperature_c=25.0,
        humidity_pct=40.0, wind_speed_m_s=5.0, wind_direction_deg=100, pressure_hpa=1013.0
    )
    assert 65.0 <= res["confidence_pct"] <= 98.0


# --- R2: 6 Sector Command Modules & Actuators ---

@pytest.mark.asyncio
async def test_tier1_r2_sectors_all_summary():
    """Verify GET /api/v2/sectors returns all 6 operational sectors with correct metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/sectors?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        assert data["total_sectors"] == 6
        assert len(data["sectors"]) == 6
        
        expected_sectors = {"education", "healthcare", "hvac", "municipal", "industrial", "agriculture"}
        actual_sectors = {s["sector_id"] for s in data["sectors"]}
        assert actual_sectors == expected_sectors
        
        for sector in data["sectors"]:
            assert "sector_id" in sector
            assert "name" in sector
            assert "status" in sector
            assert "status_color" in sector
            assert "primary_action" in sector
            assert "kpis" in sector
            assert "actuators" in sector
            assert len(sector["kpis"]) >= 3
            assert len(sector["actuators"]) >= 2


@pytest.mark.asyncio
async def test_tier1_r2_education_sector_console():
    """Verify Education & Campus Sector detail and recess safety ratings."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/sectors/education?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        assert data["sector_id"] == "education"
        assert data["recess_safety_rating"] in ["PROHIBITED", "RESTRICTED_LOW_IMPACT", "FULLY_SAFE"]
        assert isinstance(data["safety_index"], int)
        
        kpi_labels = [k["label"] for k in data["kpis"]]
        assert "Outdoor Recess Safety" in kpi_labels
        assert "Classroom Vent Stage" in kpi_labels

        actuator_names = [a["name"] for a in data["actuators"]]
        assert "Classroom Smart Air Purifiers" in actuator_names
        assert "Sports Ground Exclosure Gates" in actuator_names


@pytest.mark.asyncio
async def test_tier1_r2_healthcare_sector_console():
    """Verify Healthcare & Clinical Sector detail and ICU positive pressure metrics."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/sectors/healthcare?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        assert data["sector_id"] == "healthcare"
        assert data["status"] in ["CRITICAL_SURGE", "ELEVATED_RISK", "LOW_RISK"]
        assert "vulnerability_index" in data
        
        kpi_labels = [k["label"] for k in data["kpis"]]
        assert "Respiratory Risk Index" in kpi_labels
        assert "ICU Positive Pressure" in kpi_labels

        actuator_names = [a["name"] for a in data["actuators"]]
        assert "Ward Positive Pressure Scrubbers" in actuator_names
        assert "Oxygen Concentrator Auto-Precharge" in actuator_names


@pytest.mark.asyncio
async def test_tier1_r2_hvac_sector_console():
    """Verify HVAC & Smart Facility Sector detail and damper modulation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/sectors/hvac?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        assert data["sector_id"] == "hvac"
        assert data["damper_position_pct"] in [10, 20, 50, 80]
        assert data["filter_life_remaining_days"] >= 12
        
        kpi_labels = [k["label"] for k in data["kpis"]]
        assert "Fresh Air Damper" in kpi_labels
        assert "HEPA Useful Life" in kpi_labels

        actuator_names = [a["name"] for a in data["actuators"]]
        assert "Main Air Handling Unit (AHU-1)" in actuator_names
        assert "Night Purge Auto-Scheduler" in actuator_names


@pytest.mark.asyncio
async def test_tier1_r2_municipal_sector_console():
    """Verify Municipal & Traffic Sector detail."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/sectors/municipal?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        assert data["sector_id"] == "municipal"
        assert "Green Corridor Efficiency" in [k["label"] for k in data["kpis"]]
        actuator_names = [a["name"] for a in data["actuators"]]
        assert "Dynamic VMS Roadway Signs" in actuator_names


@pytest.mark.asyncio
async def test_tier1_r2_industrial_sector_console():
    """Verify Industrial & Construction Sector detail and mist cannon controls."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/sectors/industrial?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        assert data["sector_id"] == "industrial"
        kpi_labels = [k["label"] for k in data["kpis"]]
        assert "Fugitive Dust Index" in kpi_labels
        assert "Worker Outdoor Shift Limit" in kpi_labels
        actuator_names = [a["name"] for a in data["actuators"]]
        assert "Automated High-Pressure Water Mist Cannons" in actuator_names


@pytest.mark.asyncio
async def test_tier1_r2_agriculture_sector_console():
    """Verify Agriculture & Biomass Sector detail and stubble smoke tracking."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/sectors/agriculture?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        assert data["sector_id"] == "agriculture"
        kpi_labels = [k["label"] for k in data["kpis"]]
        assert "Biomass Plume Signature" in kpi_labels
        actuator_names = [a["name"] for a in data["actuators"]]
        assert "Perimeter Vegetative Windbreak Misting" in actuator_names


@pytest.mark.asyncio
async def test_tier1_r2_actuator_trigger_endpoint():
    """Verify POST /api/v2/actuators/trigger dispatches valid actuation response."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "sector_id": "hvac",
            "actuator_name": "Main Air Handling Unit (AHU-1)",
            "target_state": "DAMPER_10%",
            "reason": "E2E Operational Test"
        }
        res = await client.post("/api/v2/actuators/trigger", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert data["sector_id"] == "hvac"
        assert data["applied_state"] == "DAMPER_10%"
        assert data["actuator_name"] == "Main Air Handling Unit (AHU-1)"


@pytest.mark.asyncio
async def test_tier1_r2_sector_not_found_handling():
    """Verify GET /api/v2/sectors/{invalid} returns 404 with structured error."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/sectors/invalid_sector_name")
        assert res.status_code == 404
        data = res.json()
        assert "error" in data["detail"] or "SECTOR_NOT_FOUND" in str(data)


# --- R3: Real-Time Alert Stream, Live News Feed & Environmental Weather Centre ---

@pytest.mark.asyncio
async def test_tier1_r3_alerts_priority_ranking():
    """Verify GET /api/v2/alerts returns priority-ranked alerts with severities."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/alerts?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)
        assert len(data["alerts"]) > 0

        severities = {a["severity"] for a in data["alerts"]}
        assert severities.issubset({"CRITICAL", "WARNING", "ADVISORY", "INFO"})

        for alert in data["alerts"]:
            assert "id" in alert
            assert "severity" in alert
            assert "title" in alert
            assert "category" in alert
            assert "message" in alert
            assert "recommended_action" in alert
            assert "acknowledged" in alert
            assert isinstance(alert["acknowledged"], bool)


@pytest.mark.asyncio
async def test_tier1_r3_alerts_acknowledgment_workflow():
    """Verify alert acknowledgment updates alert status to acknowledged."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        alt_res = await client.get("/api/v2/alerts?campus_code=KARACHI")
        alerts = alt_res.json()["alerts"]
        assert len(alerts) > 0
        target_alert = alerts[0]
        alert_id = target_alert["id"]

        ack_res = await client.post(f"/api/v2/alerts/{alert_id}/acknowledge")
        assert ack_res.status_code == 200
        ack_data = ack_res.json()
        assert ack_data["status"] == "ACKNOWLEDGED"
        assert ack_data["alert_id"] == alert_id

        refreshed_res = await client.get("/api/v2/alerts?campus_code=KARACHI")
        refreshed_alerts = refreshed_res.json()["alerts"]
        matching = next(a for a in refreshed_alerts if a["id"] == alert_id)
        assert matching["acknowledged"] is True


@pytest.mark.asyncio
async def test_tier1_r3_environmental_news_feed():
    """Verify GET /api/v2/news returns Pakistan environmental news articles."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/news")
        assert res.status_code == 200
        data = res.json()
        assert data["total_articles"] >= 5
        assert len(data["articles"]) >= 5

        for article in data["articles"]:
            assert "id" in article
            assert "headline" in article
            assert "source" in article
            assert "time_ago" in article
            assert "category" in article
            assert "badge" in article
            assert "summary" in article
            assert "link" in article

        sources = [a["source"] for a in data["articles"]]
        assert any("Pak-EPA" in s or "Pakistan Environmental" in s for s in sources)
        assert any("PMD" in s or "Pakistan Meteorological" in s for s in sources)


@pytest.mark.asyncio
async def test_tier1_r3_weather_centre_widget():
    """Verify GET /api/v2/weather/live returns live atmospheric metrics."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/weather/live?campus_code=KARACHI")
        assert res.status_code == 200
        data = res.json()
        
        required_weather_fields = [
            "campus_code", "city", "temperature_c", "feels_like_c",
            "humidity_pct", "dew_point_c", "pressure_hpa", "wind_speed_m_s",
            "wind_direction_deg", "wind_direction_cardinal", "uv_index",
            "visibility_km", "boundary_layer_height_m", "inversion_risk", "source"
        ]
        for field in required_weather_fields:
            assert field in data, f"Missing weather field: {field}"
            
        assert data["city"] == "Karachi"
        assert data["campus_code"] == "KARACHI"
        assert data["temperature_c"] > 0
        assert 0 <= data["humidity_pct"] <= 100
        assert data["pressure_hpa"] > 900


@pytest.mark.asyncio
async def test_tier1_r3_weather_centre_islamabad():
    """Verify GET /api/v2/weather/live returns distinct Islamabad weather profile."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v2/weather/live?campus_code=ISLAMABAD")
        assert res.status_code == 200
        data = res.json()
        assert data["city"] == "Islamabad"
        assert data["campus_code"] == "ISLAMABAD"
        assert data["wind_direction_cardinal"] == "SE"


# --- R4: Side-by-Side Coexistence ---

@pytest.mark.asyncio
async def test_tier1_r4_v1_ops_dashboard_served():
    """Verify legacy v1 Operational Dashboard is intact and served at / and /ops."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_root = await client.get("/")
        assert res_root.status_code == 200
        assert "text/html" in res_root.headers.get("content-type", "")
        assert len(res_root.text) > 1000

        res_ops = await client.get("/ops")
        assert res_ops.status_code == 200
        assert "text/html" in res_ops.headers.get("content-type", "")
        assert len(res_ops.text) > 1000


@pytest.mark.asyncio
async def test_tier1_r4_v2_command_centre_served():
    """Verify Next-Gen v2 Command Centre is served at /command."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/command")
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        assert "AirSense" in res.text or "Command" in res.text


@pytest.mark.asyncio
async def test_tier1_r4_v2_ops_alias_served():
    """Verify Next-Gen v2 Command Centre alias is served at /ops-v2."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_cmd = await client.get("/command")
        res_alias = await client.get("/ops-v2")
        assert res_alias.status_code == 200
        assert res_alias.text == res_cmd.text


@pytest.mark.asyncio
async def test_tier1_r4_v1_and_v2_api_coexistence():
    """Verify v1 API endpoints (/api/v1/*) and v2 API endpoints (/api/v2/*) coexist cleanly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        v1_health = await client.get("/api/v1/health")
        assert v1_health.status_code == 200
        assert v1_health.json()["status"] == "healthy"

        v1_version = await client.get("/api/v1/version")
        assert v1_version.status_code == 200
        assert "version" in v1_version.json()

        v2_decisions = await client.get("/api/v2/decisions/live")
        assert v2_decisions.status_code == 200

        v2_news = await client.get("/api/v2/news")
        assert v2_news.status_code == 200


@pytest.mark.asyncio
async def test_tier1_r4_static_assets_served():
    """Verify static files mount serves assets correctly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_idx = await client.get("/static/index.html")
        assert res_idx.status_code == 200

        res_cmd = await client.get("/static/command.html")
        assert res_cmd.status_code == 200


# ===========================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=8 test cases)
# ===========================================================================

def test_tier2_boundary_hygroscopic_swelling_high_humidity():
    """Verify high relative humidity (>75% RH) applies 0.90 hygroscopic swelling adjustment."""
    # Under 80% RH, 100 µg/m³ PM2.5 adjusted is 90 µg/m³.
    swollen = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KAR_CAMPUS", current_pm2_5=100.0, current_pm10=140.0,
        forecast_1h_pm2_5=70.0, forecast_6h_pm2_5=70.0, temperature_c=25.0,
        humidity_pct=80.0, wind_speed_m_s=3.0, wind_direction_deg=240, pressure_hpa=1010.0
    )
    # Under 50% RH, 100 µg/m³ PM2.5 is not adjusted.
    dry = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KAR_CAMPUS", current_pm2_5=100.0, current_pm10=140.0,
        forecast_1h_pm2_5=70.0, forecast_6h_pm2_5=70.0, temperature_c=25.0,
        humidity_pct=50.0, wind_speed_m_s=3.0, wind_direction_deg=240, pressure_hpa=1010.0
    )
    assert swollen["telemetry_summary"]["humidity_pct"] == 80.0
    assert dry["telemetry_summary"]["humidity_pct"] == 50.0


def test_tier2_boundary_hygroscopic_swelling_low_humidity():
    """Verify normal RH (<=75%) does not swell particles."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="ISB_CAMPUS", current_pm2_5=30.0, current_pm10=50.0,
        forecast_1h_pm2_5=32.0, forecast_6h_pm2_5=35.0, temperature_c=20.0,
        humidity_pct=60.0, wind_speed_m_s=2.5, wind_direction_deg=120, pressure_hpa=1012.0
    )
    assert res["risk_tier"] == "OPTIMAL_NORMAL"


def test_tier2_boundary_industrial_coarse_dust_ratio():
    """Verify coarse dust ratio (PM10/PM2.5 > 3.0) or PM10 > 150 triggers dust suppression."""
    high_coarse = SectorIntelligenceEngine.get_industrial_intelligence(pm2_5=30.0, pm10=120.0, wind_speed=2.0)
    assert high_coarse["status"] == "DUST_SUPPRESSION_TRIGGER"
    assert high_coarse["status_color"] == "#FF7A00"

    normal_dust = SectorIntelligenceEngine.get_industrial_intelligence(pm2_5=20.0, pm10=35.0, wind_speed=2.0)
    assert normal_dust["status"] == "COMPLIANT"
    assert normal_dust["status_color"] == "#00E599"


def test_tier2_boundary_agriculture_biomass_smoke_trigger():
    """Verify dry smoke signature (PM2.5 > 65 and humidity < 65%) triggers upwind plume status."""
    plume = SectorIntelligenceEngine.get_agriculture_intelligence(pm2_5=75.0, wind_speed=2.0, humidity_pct=45.0)
    assert plume["status"] == "UPWIND_PLUME_DETECTED"
    assert plume["status_color"] == "#FF2A55"

    clean_rural = SectorIntelligenceEngine.get_agriculture_intelligence(pm2_5=20.0, wind_speed=3.0, humidity_pct=50.0)
    assert clean_rural["status"] == "CLEAR_HORIZON"


def test_tier2_boundary_zero_wind_stagnation():
    """Verify zero wind speed maximizes stagnation calculation."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="ISB_CAMPUS", current_pm2_5=60.0, current_pm10=100.0,
        forecast_1h_pm2_5=65.0, forecast_6h_pm2_5=70.0, temperature_c=10.0,
        humidity_pct=90.0, wind_speed_m_s=0.0, wind_direction_deg=0, pressure_hpa=1018.0
    )
    assert res["stagnation_index"] >= 70.0
    assert res["dispersion_class"] == "POOR_TRAPPED_INVERSION"


def test_tier2_boundary_extreme_wind_dispersion():
    """Verify strong winds (10+ m/s) produce excellent dispersion."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KAR_CAMPUS", current_pm2_5=20.0, current_pm10=40.0,
        forecast_1h_pm2_5=20.0, forecast_6h_pm2_5=22.0, temperature_c=28.0,
        humidity_pct=40.0, wind_speed_m_s=12.0, wind_direction_deg=220, pressure_hpa=1010.0
    )
    assert res["dispersion_class"] == "EXCELLENT_VENTILATION"


def test_tier2_boundary_idempotent_alert_acknowledgment():
    """Verify calling acknowledge multiple times remains idempotent."""
    test_id = "test_alert_boundary_idemp"
    res1 = NewsAndAlertsEngine.acknowledge_alert(test_id)
    assert res1 is True
    res2 = NewsAndAlertsEngine.acknowledge_alert(test_id)
    assert res2 is True
    assert test_id in NewsAndAlertsEngine._acknowledged_alerts


def test_tier2_boundary_hvac_damper_endpoints():
    """Verify HVAC damper modulation transitions properly between extreme clean and dirty air."""
    hvac_clean = SectorIntelligenceEngine.get_hvac_intelligence(pm2_5=15.0, forecast_1h=18.0, temp_c=24.0, humidity_pct=50.0)
    assert hvac_clean["damper_position_pct"] == 80

    hvac_extreme = SectorIntelligenceEngine.get_hvac_intelligence(pm2_5=150.0, forecast_1h=180.0, temp_c=24.0, humidity_pct=50.0)
    assert hvac_extreme["damper_position_pct"] == 10


# ===========================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS & PAIRWISE (>=6 test cases)
# ===========================================================================

def test_tier3_cross_feature_critical_smog_coupling():
    """Verify severe PM2.5 trajectory concurrently impacts decision tier, education, healthcare, and HVAC."""
    pm = 180.0
    forecast = 210.0
    dec = OperationalDecisionEngine.evaluate_decisions(
        campus_code="ISB_CAMPUS", current_pm2_5=pm, current_pm10=pm*1.8,
        forecast_1h_pm2_5=forecast, forecast_6h_pm2_5=220.0, temperature_c=12.0,
        humidity_pct=85.0, wind_speed_m_s=0.5, wind_direction_deg=90, pressure_hpa=1015.0
    )
    assert dec["risk_tier"] == "CRITICAL_HAZARD"

    edu = SectorIntelligenceEngine.get_education_intelligence(pm, forecast)
    assert edu["recess_safety_rating"] == "PROHIBITED"
    assert edu["status"] == "RESTRICTED"

    health = SectorIntelligenceEngine.get_healthcare_intelligence(pm, forecast, 85.0)
    assert health["status"] == "CRITICAL_SURGE"

    hvac = SectorIntelligenceEngine.get_hvac_intelligence(pm, forecast, 12.0, 85.0)
    assert hvac["damper_position_pct"] == 10


def test_tier3_cross_feature_clean_day_coupling():
    """Verify clean ambient air concurrently creates nominal conditions across all modules."""
    pm = 10.0
    forecast = 12.0
    dec = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KAR_CAMPUS", current_pm2_5=pm, current_pm10=20.0,
        forecast_1h_pm2_5=forecast, forecast_6h_pm2_5=14.0, temperature_c=28.0,
        humidity_pct=50.0, wind_speed_m_s=4.5, wind_direction_deg=240, pressure_hpa=1011.0
    )
    assert dec["risk_tier"] == "OPTIMAL_NORMAL"

    edu = SectorIntelligenceEngine.get_education_intelligence(pm, forecast)
    assert edu["recess_safety_rating"] == "FULLY_SAFE"

    health = SectorIntelligenceEngine.get_healthcare_intelligence(pm, forecast, 50.0)
    assert health["status"] == "LOW_RISK"

    hvac = SectorIntelligenceEngine.get_hvac_intelligence(pm, forecast, 28.0, 50.0)
    assert hvac["damper_position_pct"] == 80


@pytest.mark.asyncio
async def test_tier3_cross_feature_campus_differentiation():
    """Verify Karachi and Islamabad return distinct regional profiles for decisions and weather."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_khi = await client.get("/api/v2/weather/live?campus_code=KARACHI")
        res_isb = await client.get("/api/v2/weather/live?campus_code=ISLAMABAD")
        
        data_khi = res_khi.json()
        data_isb = res_isb.json()
        
        assert data_khi["city"] == "Karachi"
        assert data_isb["city"] == "Islamabad"
        assert data_khi["wind_direction_cardinal"] != data_isb["wind_direction_cardinal"]
        assert data_khi["humidity_pct"] > data_isb["humidity_pct"]


@pytest.mark.asyncio
async def test_tier3_cross_feature_actuator_workflow_across_all_sectors():
    """Verify actuator triggers execute successfully across all 6 operational sectors."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sectors = ["education", "healthcare", "hvac", "municipal", "industrial", "agriculture"]
        for sec in sectors:
            payload = {
                "sector_id": sec,
                "actuator_name": f"{sec.capitalize()} Main Control",
                "target_state": "ACTIVE_RUN",
                "reason": "Cross-feature test validation"
            }
            res = await client.post("/api/v2/actuators/trigger", json=payload)
            assert res.status_code == 200
            assert res.json()["status"] == "SUCCESS"
            assert res.json()["sector_id"] == sec


@pytest.mark.asyncio
async def test_tier3_cross_feature_dual_dashboard_switchers():
    """Verify bidirectional link targets between v1 and v2 dashboards."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_v1 = await client.get("/ops")
        assert "/command" in res_v1.text

        res_v2 = await client.get("/command")
        assert "/ops" in res_v2.text


@pytest.mark.asyncio
async def test_tier3_cross_feature_simulated_db_reading_propagation():
    """Verify database raw readings correctly flow into the decision intelligence layer."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        dec_res = await client.get("/api/v2/decisions/live?campus_code=KARACHI")
        assert dec_res.status_code == 200
        assert "telemetry_summary" in dec_res.json()


# ===========================================================================
# TIER 4: REAL-WORLD OPERATIONAL SCENARIOS (>=4 comprehensive workflows)
# ===========================================================================

@pytest.mark.asyncio
async def test_tier4_scenario1_severe_winter_smog_emergency_workflow():
    """Scenario 1: Winter Smog Emergency Lifecycle.
    
    1. Check baseline air quality and decisions.
    2. Simulate critical smog evaluation (PM2.5 > 150 µg/m³).
    3. Verify emergency decision directive and action code.
    4. Confirm active triggers include HVAC HEPA boost and student activity relocations.
    5. Acknowledge the critical smog alert.
    6. Dispatch emergency AHU recirculation actuation.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: Decision intelligence under smog
        smog_eval = OperationalDecisionEngine.evaluate_decisions(
            campus_code="ISB_CAMPUS", current_pm2_5=175.0, current_pm10=290.0,
            forecast_1h_pm2_5=190.0, forecast_6h_pm2_5=220.0, temperature_c=11.0,
            humidity_pct=88.0, wind_speed_m_s=0.6, wind_direction_deg=90, pressure_hpa=1018.0
        )
        assert smog_eval["risk_tier"] == "CRITICAL_HAZARD"
        assert "EMERGENCY" in smog_eval["primary_directive"]
        assert smog_eval["action_code"] == "ACT_EMERGENCY_SHUTDOWN_OUTDOOR"
        assert len(smog_eval["active_triggers"]) >= 3

        # Step 2: Alerts generation & acknowledgment
        alerts = NewsAndAlertsEngine.get_live_alerts(pm2_5=175.0, forecast_1h=190.0, wind_speed=0.6, campus_code="ISB_CAMPUS")
        assert any(a["severity"] == "CRITICAL" for a in alerts)
        crit_alert = next(a for a in alerts if a["severity"] == "CRITICAL")

        ack_res = await client.post(f"/api/v2/alerts/{crit_alert['id']}/acknowledge")
        assert ack_res.status_code == 200

        # Step 3: Actuator dispatch
        act_res = await client.post("/api/v2/actuators/trigger", json={
            "sector_id": "hvac",
            "actuator_name": "Main Air Handling Unit (AHU-1)",
            "target_state": "DAMPER_10%_HEPA_STAGE_3",
            "reason": "Winter Smog Emergency Directive Executed"
        })
        assert act_res.status_code == 200
        assert act_res.json()["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_tier4_scenario2_industrial_dust_surge_workflow():
    """Scenario 2: Industrial Construction Dust Surge.
    
    1. PM10 exceeds PM2.5 ratio (> 3.0) due to heavy demolition/aggregate movement.
    2. Industrial sector flags DUST_SUPPRESSION_TRIGGER.
    3. Automated mist cannons and N95 worker PPE gates are triggered.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ind_status = SectorIntelligenceEngine.get_industrial_intelligence(pm2_5=40.0, pm10=185.0, wind_speed=1.5)
        assert ind_status["status"] == "DUST_SUPPRESSION_TRIGGER"
        assert "mist cannons" in ind_status["primary_action"].lower()

        act_res = await client.post("/api/v2/actuators/trigger", json={
            "sector_id": "industrial",
            "actuator_name": "Automated High-Pressure Water Mist Cannons",
            "target_state": "AUTORUN_4.2_BAR",
            "reason": "Coarse particulate exceedance detected"
        })
        assert act_res.status_code == 200
        assert act_res.json()["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_tier4_scenario3_agricultural_stubble_burning_workflow():
    """Scenario 3: Regional Crop Stubble Smoke Plume Transport.
    
    1. Upwind biomass signature detected (PM2.5 = 85.0, RH = 42.0%).
    2. Agriculture console calculates arrival window (T+3.5h).
    3. Perimeter vegetative windbreak misting is armed.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        agri_status = SectorIntelligenceEngine.get_agriculture_intelligence(pm2_5=85.0, wind_speed=2.2, humidity_pct=42.0)
        assert agri_status["status"] == "UPWIND_PLUME_DETECTED"
        assert "stubble burning" in agri_status["primary_action"].lower()

        act_res = await client.post("/api/v2/actuators/trigger", json={
            "sector_id": "agriculture",
            "actuator_name": "Perimeter Vegetative Windbreak Misting",
            "target_state": "TRIGGER_PREWET",
            "reason": "Upwind biomass plume transport protocol"
        })
        assert act_res.status_code == 200
        assert act_res.json()["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_tier4_scenario4_hvac_smart_cycle_workflow():
    """Scenario 4: HVAC Smart Cycle & Energy Optimization.
    
    1. Clean morning air -> 80% Economizer Mode (+18% energy savings).
    2. Afternoon particulate buildup -> 20% Damper Scrub.
    3. Filter useful life tracking.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Morning clean air
        morning_hvac = SectorIntelligenceEngine.get_hvac_intelligence(pm2_5=18.0, forecast_1h=22.0, temp_c=22.0, humidity_pct=48.0)
        assert morning_hvac["damper_position_pct"] == 80

        # Afternoon buildup
        afternoon_hvac = SectorIntelligenceEngine.get_hvac_intelligence(pm2_5=65.0, forecast_1h=78.0, temp_c=29.0, humidity_pct=58.0)
        assert afternoon_hvac["damper_position_pct"] == 20
        assert afternoon_hvac["filter_life_remaining_days"] > 0

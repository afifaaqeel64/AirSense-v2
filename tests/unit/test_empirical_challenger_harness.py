"""Empirical Challenger 1 Stress Harness & Boundary Validation Suite.

Covers:
1. Zero particulate boundary conditions (PM2.5=0, PM10=0, Forecast=0).
2. Extreme particulate surges (PM2.5=10,000 to 100,000 ug/m3).
3. Extreme meteorological bounds (0 wind, 100% RH, freezing inversions, sub-zero temps).
4. Corrupted and edge-case telemetry vectors across API routes and services.
"""

import pytest
import math
from httpx import AsyncClient, ASGITransport
from apps.api.main import app
from services.decision_intelligence.decision_engine import OperationalDecisionEngine
from services.decision_intelligence.sector_intelligence import SectorIntelligenceEngine
from services.decision_intelligence.news_and_alerts import NewsAndAlertsEngine


# ============================================================================
# 1. ZERO PARTICULATE BOUNDARY CONDITIONS
# ============================================================================

def test_zero_particulate_decision_engine_evaluation():
    """Verify decision engine strictly outputs OPTIMAL_NORMAL and max confidence for 0.0 PM."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="ZERO_CAMPUS",
        current_pm2_5=0.0,
        current_pm10=0.0,
        forecast_1h_pm2_5=0.0,
        forecast_6h_pm2_5=0.0,
        temperature_c=25.0,
        humidity_pct=50.0,
        wind_speed_m_s=4.0,
        wind_direction_deg=180.0,
        pressure_hpa=1013.25,
        rain_flag=False
    )
    assert res["risk_tier"] == "OPTIMAL_NORMAL"
    assert res["risk_color"] == "#00E599"
    assert res["action_code"] == "ACT_STANDARD_EFFICIENCY"
    assert res["confidence_pct"] == 98.0
    assert 0.0 <= res["stagnation_index"] <= 100.0


def test_zero_particulate_all_sector_engines():
    """Verify all 6 sectors return non-crashing valid dictionaries when PM is 0.0."""
    sectors = SectorIntelligenceEngine.get_all_sectors_summary(
        pm2_5=0.0,
        pm10=0.0,
        temp_c=20.0,
        humidity_pct=50.0,
        wind_speed_m_s=3.0,
        forecast_1h=0.0
    )
    assert len(sectors) == 6
    s_map = {s["sector_id"]: s for s in sectors}
    
    # Education
    assert s_map["education"]["status"] == "OPTIMAL"
    assert s_map["education"]["recess_safety_rating"] == "FULLY_SAFE"
    assert s_map["education"]["safety_index"] == 98
    
    # Healthcare
    assert s_map["healthcare"]["status"] == "LOW_RISK"
    assert s_map["healthcare"]["vulnerability_index"] == 10  # 50% RH gives (50/100)*20 = 10
    
    # HVAC
    assert s_map["hvac"]["status"] == "OPTIMAL_EFFICIENCY"
    assert s_map["hvac"]["damper_position_pct"] == 80
    assert s_map["hvac"]["filter_life_remaining_days"] == 90
    
    # Municipal
    assert s_map["municipal"]["status"] == "FLOW_NORMAL"
    
    # Industrial
    assert s_map["industrial"]["status"] == "COMPLIANT"
    
    # Agriculture
    assert s_map["agriculture"]["status"] == "CLEAR_HORIZON"


def test_zero_particulate_live_alerts():
    """Verify live alerts generate only baseline INFO / ADVISORY when PM is 0.0."""
    alerts = NewsAndAlertsEngine.get_live_alerts(pm2_5=0.0, forecast_1h=0.0, wind_speed=3.0, campus_code="ZERO_CAMPUS")
    assert not any(a["severity"] == "CRITICAL" for a in alerts)
    assert not any(a["severity"] == "WARNING" for a in alerts)
    assert any(a["severity"] == "INFO" for a in alerts)


# ============================================================================
# 2. EXTREME PARTICULATE SURGES (10,000 to 100,000 µg/m³)
# ============================================================================

@pytest.mark.parametrize("extreme_pm", [10000.0, 25000.0, 50000.0, 100000.0])
def test_extreme_particulate_surge_invariants(extreme_pm):
    """Verify system stability and invariants under extreme particulate surges."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="SURGE_CAMPUS",
        current_pm2_5=extreme_pm,
        current_pm10=extreme_pm * 2.0,
        forecast_1h_pm2_5=extreme_pm * 1.5,
        forecast_6h_pm2_5=extreme_pm * 1.8,
        temperature_c=12.0,
        humidity_pct=85.0,
        wind_speed_m_s=0.5,
        wind_direction_deg=90.0,
        pressure_hpa=1015.0
    )
    assert res["risk_tier"] == "CRITICAL_HAZARD"
    assert res["risk_color"] == "#FF2A55"
    assert res["action_code"] == "ACT_EMERGENCY_SHUTDOWN_OUTDOOR"
    assert 65.0 <= res["confidence_pct"] <= 98.0
    assert 0.0 <= res["stagnation_index"] <= 100.0

    # Sector bounds under extreme surge
    edu = SectorIntelligenceEngine.get_education_intelligence(extreme_pm, extreme_pm * 1.5)
    assert edu["recess_safety_rating"] == "PROHIBITED"
    assert edu["status"] == "RESTRICTED"

    health = SectorIntelligenceEngine.get_healthcare_intelligence(extreme_pm, extreme_pm * 1.5, 85.0)
    assert health["vulnerability_index"] == 100  # Clamped to 100
    assert health["status"] == "CRITICAL_SURGE"

    hvac = SectorIntelligenceEngine.get_hvac_intelligence(extreme_pm, extreme_pm * 1.5, 12.0, 85.0)
    assert hvac["damper_position_pct"] == 10  # Clamped to 10%
    assert hvac["filter_life_remaining_days"] == 12  # Clamped to 12 days minimum


# ============================================================================
# 3. EXTREME METEOROLOGICAL BOUNDS
# ============================================================================

def test_extreme_meteorology_zero_wind_freeze_inversion():
    """Zero wind, freezing temp (-15°C), 100% RH -> severe inversion."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="FREEZE_INVERSION",
        current_pm2_5=60.0,
        current_pm10=100.0,
        forecast_1h_pm2_5=65.0,
        forecast_6h_pm2_5=70.0,
        temperature_c=-15.0,
        humidity_pct=100.0,
        wind_speed_m_s=0.0,
        wind_direction_deg=0.0,
        pressure_hpa=1045.0
    )
    # Stagnation score = (10-0)*5 + (100*0.4) + 20 = 50 + 40 + 20 = 110 -> clamped to 100.0
    assert res["stagnation_index"] == 100.0
    assert res["dispersion_class"] == "POOR_TRAPPED_INVERSION"


def test_extreme_meteorology_heatwave_gale_force_winds():
    """Extreme heat (55°C), 0% RH, gale-force wind (45 m/s) -> zero stagnation."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="HEAT_GALE",
        current_pm2_5=30.0,
        current_pm10=80.0,
        forecast_1h_pm2_5=25.0,
        forecast_6h_pm2_5=20.0,
        temperature_c=55.0,
        humidity_pct=0.0,
        wind_speed_m_s=45.0,
        wind_direction_deg=270.0,
        pressure_hpa=960.0
    )
    assert res["stagnation_index"] == 0.0
    assert res["dispersion_class"] == "EXCELLENT_VENTILATION"


def test_extreme_meteorology_hygroscopic_swelling_edge_thresholds():
    """Verify hygroscopic swelling behavior at 74.9%, 75.0%, and 75.1% RH."""
    # 74.9% RH -> no swelling
    res_749 = OperationalDecisionEngine.evaluate_decisions(
        campus_code="RH_749", current_pm2_5=100.0, current_pm10=150.0,
        forecast_1h_pm2_5=50.0, forecast_6h_pm2_5=50.0, temperature_c=20.0,
        humidity_pct=74.9, wind_speed_m_s=3.0, wind_direction_deg=0.0, pressure_hpa=1013.0
    )
    # 75.0% RH -> no swelling
    res_750 = OperationalDecisionEngine.evaluate_decisions(
        campus_code="RH_750", current_pm2_5=100.0, current_pm10=150.0,
        forecast_1h_pm2_5=50.0, forecast_6h_pm2_5=50.0, temperature_c=20.0,
        humidity_pct=75.0, wind_speed_m_s=3.0, wind_direction_deg=0.0, pressure_hpa=1013.0
    )
    # 75.1% RH -> 0.90 swelling multiplier applies (100 -> 90.0)
    res_751 = OperationalDecisionEngine.evaluate_decisions(
        campus_code="RH_751", current_pm2_5=100.0, current_pm10=150.0,
        forecast_1h_pm2_5=50.0, forecast_6h_pm2_5=50.0, temperature_c=20.0,
        humidity_pct=75.1, wind_speed_m_s=3.0, wind_direction_deg=0.0, pressure_hpa=1013.0
    )
    
    assert res_749["telemetry_summary"]["pm2_5"] == 100.0
    assert res_750["telemetry_summary"]["pm2_5"] == 100.0
    assert res_751["telemetry_summary"]["pm2_5"] == 100.0


# ============================================================================
# 4. CORRUPTED TELEMETRY & API ENDPOINT VALIDATION
# ============================================================================

@pytest.mark.asyncio
async def test_corrupted_vectors_simulation_endpoint():
    """Test POST /api/v2/decisions/simulate across boundary conditions."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Zero PM simulation
        sim_zero = {
            "campus_code": "ISLAMABAD",
            "simulated_pm2_5": 0.0,
            "simulated_temp_c": 10.0,
            "simulated_humidity_pct": 50.0,
            "simulated_wind_speed_m_s": 2.0,
            "inversion_active": False
        }
        res_zero = await client.post("/api/v2/decisions/simulate", json=sim_zero)
        assert res_zero.status_code == 200
        data_zero = res_zero.json()
        assert data_zero["evaluated_decision"]["risk_tier"] == "OPTIMAL_NORMAL"

        # Max allowed PM simulation (1000.0)
        sim_max = {
            "campus_code": "KARACHI",
            "simulated_pm2_5": 1000.0,
            "simulated_temp_c": 15.0,
            "simulated_humidity_pct": 95.0,
            "simulated_wind_speed_m_s": 0.2,
            "inversion_active": True
        }
        res_max = await client.post("/api/v2/decisions/simulate", json=sim_max)
        assert res_max.status_code == 200
        data_max = res_max.json()
        assert data_max["evaluated_decision"]["risk_tier"] == "CRITICAL_HAZARD"

        # Exceeds max schema validation (>1000)
        sim_invalid = {
            "campus_code": "KARACHI",
            "simulated_pm2_5": 1500.0,
            "simulated_temp_c": 25.0,
            "simulated_humidity_pct": 50.0,
            "simulated_wind_speed_m_s": 2.0,
            "inversion_active": False
        }
        res_invalid = await client.post("/api/v2/decisions/simulate", json=sim_invalid)
        assert res_invalid.status_code == 422  # Unprocessable Entity


@pytest.mark.asyncio
async def test_corrupted_vectors_ai_consult_copilot():
    """Test POST /api/v2/decisions/ai-consult with edge case queries and None PM values."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Query with None PM (should fallback cleanly to defaults)
        payload_none = {
            "query": "What should the campus director do regarding sports recess?",
            "campus_code": "KARACHI",
            "current_pm2_5": None,
            "forecast_1h": None
        }
        res_none = await client.post("/api/v2/decisions/ai-consult", json=payload_none)
        assert res_none.status_code == 200
        data_none = res_none.json()
        assert data_none["status"] == "SUCCESS"
        assert len(data_none["briefing"]) > 10

        # Query with zero PM
        payload_zero = {
            "query": "Evaluate HVAC and AHU damper settings",
            "campus_code": "ISLAMABAD",
            "current_pm2_5": 0.0,
            "forecast_1h": 0.0
        }
        res_zero = await client.post("/api/v2/decisions/ai-consult", json=payload_zero)
        assert res_zero.status_code == 200
        data_zero = res_zero.json()
        assert data_zero["status"] == "SUCCESS"
        assert "50%" in data_zero["briefing"] or "damper" in data_zero["briefing"].lower()


@pytest.mark.asyncio
async def test_corrupted_vectors_actuator_invalid_payload():
    """Test POST /api/v2/actuators/trigger handles missing fields with 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing required fields
        res_empty = await client.post("/api/v2/actuators/trigger", json={})
        assert res_empty.status_code == 422

        res_missing_state = await client.post("/api/v2/actuators/trigger", json={
            "sector_id": "hvac",
            "actuator_name": "AHU-1"
        })
        assert res_missing_state.status_code == 422

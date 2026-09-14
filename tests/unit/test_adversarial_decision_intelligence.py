"""Adversarial White-Box & Stress Test Suite for AirSense Decision Intelligence Services.

Empirical verification of:
1. Division-by-zero protections and numerical stability.
2. Boundary values and strict transition boundaries.
3. Extreme weather telemetry (0 wind, hurricane wind, 100% RH, 0% RH, extreme cold/hot).
4. Stagnation score edge bounds [0.0, 100.0] and dispersion class invariants.
5. Confidence interval clamp invariants [65.0%, 98.0%].
6. Extreme particulate matter ranges (0 to 10,000+ ug/m3).
7. Coarse dust ratio singularities and biomass smoke signature edge cases.
8. Property-based randomized fuzzing (10,000 randomized weather/PM vectors).
"""

import pytest
import math
import random
from services.decision_intelligence.decision_engine import OperationalDecisionEngine
from services.decision_intelligence.sector_intelligence import SectorIntelligenceEngine
from services.decision_intelligence.news_and_alerts import NewsAndAlertsEngine


# ============================================================================
# 1. DIVISION-BY-ZERO & NUMERICAL STABILITY ADVERSARIAL TESTS
# ============================================================================

def test_adversarial_zero_pm25_no_division_by_zero():
    """Verify current_pm2_5 = 0.0 does not trigger ZeroDivisionError in confidence score."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="TEST_ZERO",
        current_pm2_5=0.0,
        current_pm10=0.0,
        forecast_1h_pm2_5=50.0,
        forecast_6h_pm2_5=50.0,
        temperature_c=25.0,
        humidity_pct=50.0,
        wind_speed_m_s=3.0,
        wind_direction_deg=180.0,
        pressure_hpa=1013.25
    )
    assert 65.0 <= res["confidence_pct"] <= 98.0
    assert res["risk_tier"] == "MODERATE_ADVISORY"


def test_adversarial_industrial_zero_pm25_coarse_ratio():
    """Verify Industrial coarse dust ratio handles pm2_5 = 0.0 safely without division by zero."""
    res = SectorIntelligenceEngine.get_industrial_intelligence(
        pm2_5=0.0,
        pm10=100.0,
        wind_speed=2.0
    )
    assert res["sector_id"] == "industrial"
    # Ratio is 100 / max(0, 1.0) = 100.0 > 3.0 -> triggers dust suppression
    assert res["status"] == "DUST_SUPPRESSION_TRIGGER"
    assert res["status_color"] == "#FF7A00"


def test_adversarial_industrial_both_zero_pm():
    """Verify Industrial intelligence handles pm2_5 = 0.0 and pm10 = 0.0."""
    res = SectorIntelligenceEngine.get_industrial_intelligence(
        pm2_5=0.0,
        pm10=0.0,
        wind_speed=0.0
    )
    assert res["status"] == "COMPLIANT"
    assert res["status_color"] == "#00E599"


def test_adversarial_healthcare_zero_inputs():
    """Verify Healthcare sector handles pm2_5 = 0.0 and humidity = 0.0."""
    res = SectorIntelligenceEngine.get_healthcare_intelligence(
        pm2_5=0.0,
        forecast_1h=0.0,
        humidity_pct=0.0
    )
    assert res["status"] == "LOW_RISK"
    assert res["vulnerability_index"] == 0


def test_adversarial_hvac_zero_inputs():
    """Verify HVAC sector handles pm2_5 = 0.0 and forecast = 0.0."""
    res = SectorIntelligenceEngine.get_hvac_intelligence(
        pm2_5=0.0,
        forecast_1h=0.0,
        temp_c=0.0,
        humidity_pct=0.0
    )
    assert res["damper_position_pct"] == 80
    assert res["filter_life_remaining_days"] == 90
    assert res["status"] == "OPTIMAL_EFFICIENCY"


# ============================================================================
# 2. EXTREME WEATHER CONDITIONS EMPIRICAL TESTS
# ============================================================================

def test_adversarial_dead_calm_zero_wind_extreme_stagnation():
    """Dead calm (0 m/s wind), 100% humidity, sub-18C cold -> maximum theoretical stagnation."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="CALM_FREEZE",
        current_pm2_5=60.0,
        current_pm10=100.0,
        forecast_1h_pm2_5=65.0,
        forecast_6h_pm2_5=70.0,
        temperature_c=5.0,
        humidity_pct=100.0,
        wind_speed_m_s=0.0,
        wind_direction_deg=0.0,
        pressure_hpa=1030.0
    )
    # raw score = (10 - 0)*5 + (100 * 0.4) + 20 = 50 + 40 + 20 = 110 -> clamped to 100.0
    assert res["stagnation_index"] == 100.0
    assert res["dispersion_class"] == "POOR_TRAPPED_INVERSION"


def test_adversarial_hurricane_wind_maximum_dispersion():
    """Category 5 hurricane winds (75 m/s, 270 km/h), 0% RH, 40C heat -> zero stagnation."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="HURRICANE",
        current_pm2_5=10.0,
        current_pm10=20.0,
        forecast_1h_pm2_5=10.0,
        forecast_6h_pm2_5=10.0,
        temperature_c=40.0,
        humidity_pct=0.0,
        wind_speed_m_s=75.0,
        wind_direction_deg=270.0,
        pressure_hpa=920.0
    )
    # raw score = (10 - min(75, 10))*5 + (0 * 0.4) + 0 = 0.0 -> clamped to 0.0
    assert res["stagnation_index"] == 0.0
    assert res["dispersion_class"] == "EXCELLENT_VENTILATION"


def test_adversarial_100_pct_relative_humidity_swelling():
    """100% RH should trigger 10% hygroscopic swelling reduction on raw optical PM2.5."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="FOG_100",
        current_pm2_5=100.0,
        current_pm10=150.0,
        forecast_1h_pm2_5=80.0,
        forecast_6h_pm2_5=80.0,
        temperature_c=12.0,
        humidity_pct=100.0,
        wind_speed_m_s=2.0,
        wind_direction_deg=180.0,
        pressure_hpa=1010.0
    )
    # current_pm2_5 adjusted = 90.0, forecast_1h = 80.0, forecast_6h * 0.95 = 76.0 -> max is 90.0
    # max_horizon_pm2_5 = 90.0 -> HIGH_ALERT (since >= 75.0 and < 150.0)
    assert res["risk_tier"] == "HIGH_ALERT"


def test_adversarial_exact_humidity_boundary_75_pct():
    """Test humidity threshold behavior around exactly 75.0%."""
    # At 75.0% (not > 75.0%), no swelling adjustment is made
    res_at_75 = OperationalDecisionEngine.evaluate_decisions(
        campus_code="RH_75",
        current_pm2_5=80.0,
        current_pm10=120.0,
        forecast_1h_pm2_5=50.0,
        forecast_6h_pm2_5=50.0,
        temperature_c=20.0,
        humidity_pct=75.0,
        wind_speed_m_s=3.0,
        wind_direction_deg=0.0,
        pressure_hpa=1013.0
    )
    # At 75.1% (> 75.0%), swelling adjustment (0.90) is made: 80 * 0.9 = 72.0
    res_above_75 = OperationalDecisionEngine.evaluate_decisions(
        campus_code="RH_75_1",
        current_pm2_5=80.0,
        current_pm10=120.0,
        forecast_1h_pm2_5=50.0,
        forecast_6h_pm2_5=50.0,
        temperature_c=20.0,
        humidity_pct=75.1,
        wind_speed_m_s=3.0,
        wind_direction_deg=0.0,
        pressure_hpa=1013.0
    )
    # At 75.0, max_pm is 80.0 -> HIGH_ALERT (>= 75.0)
    assert res_at_75["risk_tier"] == "HIGH_ALERT"
    # At 75.1, max_pm is 72.0 -> MODERATE_ADVISORY (< 75.0 and >= 35.0)
    assert res_above_75["risk_tier"] == "MODERATE_ADVISORY"


def test_adversarial_exact_temperature_boundary_18c():
    """Test stagnation temperature bonus (+20 if temp < 18.0)."""
    # At 18.0C -> no bonus
    res_at_18 = OperationalDecisionEngine.evaluate_decisions(
        campus_code="TEMP_18",
        current_pm2_5=20.0,
        current_pm10=30.0,
        forecast_1h_pm2_5=20.0,
        forecast_6h_pm2_5=20.0,
        temperature_c=18.0,
        humidity_pct=50.0,
        wind_speed_m_s=5.0,
        wind_direction_deg=0.0,
        pressure_hpa=1013.0
    )
    # (10-5)*5 + 50*0.4 + 0 = 25 + 20 = 45.0
    assert res_at_18["stagnation_index"] == 45.0
    assert res_at_18["dispersion_class"] == "MODERATE_DISPERSION"

    # At 17.9C -> +20 bonus
    res_below_18 = OperationalDecisionEngine.evaluate_decisions(
        campus_code="TEMP_17_9",
        current_pm2_5=20.0,
        current_pm10=30.0,
        forecast_1h_pm2_5=20.0,
        forecast_6h_pm2_5=20.0,
        temperature_c=17.9,
        humidity_pct=50.0,
        wind_speed_m_s=5.0,
        wind_direction_deg=0.0,
        pressure_hpa=1013.0
    )
    # (10-5)*5 + 50*0.4 + 20 = 25 + 20 + 20 = 65.0
    assert res_below_18["stagnation_index"] == 65.0


# ============================================================================
# 3. STAGNATION SCORE EDGE BOUNDS & DISPERSION INVARIANTS
# ============================================================================

@pytest.mark.parametrize("wind,humidity,temp,expected_min,expected_max,expected_class", [
    (0.0, 100.0, 10.0, 100.0, 100.0, "POOR_TRAPPED_INVERSION"),  # 50 + 40 + 20 = 110 -> 100
    (10.0, 0.0, 25.0, 0.0, 0.0, "EXCELLENT_VENTILATION"),        # 0 + 0 + 0 = 0
    (5.0, 50.0, 20.0, 45.0, 45.0, "MODERATE_DISPERSION"),        # 25 + 20 + 0 = 45
    (6.0, 50.0, 20.0, 40.0, 40.0, "EXCELLENT_VENTILATION"),      # 20 + 20 + 0 = 40 (<=40 is EXCELLENT)
    (5.9, 50.0, 20.0, 40.5, 40.5, "MODERATE_DISPERSION"),        # 20.5 + 20 + 0 = 40.5 (>40 is MODERATE)
    (0.0, 50.0, 20.0, 70.0, 70.0, "MODERATE_DISPERSION"),        # 50 + 20 + 0 = 70 (<=70 is MODERATE)
    (0.0, 51.0, 20.0, 70.4, 70.4, "POOR_TRAPPED_INVERSION"),     # 50 + 20.4 + 0 = 70.4 (>70 is POOR)
])
def test_adversarial_stagnation_class_transitions(wind, humidity, temp, expected_min, expected_max, expected_class):
    """Verify exact dispersion transition thresholds at 40 and 70 score boundaries."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="TRANS_TEST",
        current_pm2_5=20.0,
        current_pm10=30.0,
        forecast_1h_pm2_5=20.0,
        forecast_6h_pm2_5=20.0,
        temperature_c=temp,
        humidity_pct=humidity,
        wind_speed_m_s=wind,
        wind_direction_deg=0.0,
        pressure_hpa=1013.0
    )
    assert expected_min <= res["stagnation_index"] <= expected_max
    assert res["dispersion_class"] == expected_class


# ============================================================================
# 4. CONFIDENCE SCORE CLAMP INVARIANTS [65.0%, 98.0%]
# ============================================================================

def test_adversarial_confidence_perfect_agreement():
    """When forecast drift is 0, confidence must clamp to upper bound 98.0%."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="PERFECT_FORECAST",
        current_pm2_5=50.0,
        current_pm10=75.0,
        forecast_1h_pm2_5=50.0,  # drift = 0
        forecast_6h_pm2_5=50.0,
        temperature_c=25.0,
        humidity_pct=50.0,
        wind_speed_m_s=3.0,
        wind_direction_deg=0.0,
        pressure_hpa=1013.0
    )
    assert res["confidence_pct"] == 98.0


def test_adversarial_confidence_massive_divergence():
    """When forecast drift is massive (e.g. 50 vs 5,000), confidence must clamp to lower bound 65.0%."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="DIVERGENT_FORECAST",
        current_pm2_5=50.0,
        current_pm10=75.0,
        forecast_1h_pm2_5=5000.0,  # massive drift
        forecast_6h_pm2_5=5000.0,
        temperature_c=25.0,
        humidity_pct=50.0,
        wind_speed_m_s=3.0,
        wind_direction_deg=0.0,
        pressure_hpa=1013.0
    )
    assert res["confidence_pct"] == 65.0


# ============================================================================
# 5. EXTREME PARTICULATE MATTER RANGES & CRITICAL TIER LOGIC
# ============================================================================

def test_adversarial_extreme_apocalyptic_pm25():
    """Verify behavior under apocalyptic PM2.5 concentration (10,000 µg/m³)."""
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="APOCALYPSE",
        current_pm2_5=10000.0,
        current_pm10=15000.0,
        forecast_1h_pm2_5=12000.0,
        forecast_6h_pm2_5=14000.0,
        temperature_c=15.0,
        humidity_pct=90.0,
        wind_speed_m_s=0.2,
        wind_direction_deg=45.0,
        pressure_hpa=1005.0
    )
    assert res["risk_tier"] == "CRITICAL_HAZARD"
    assert res["action_code"] == "ACT_EMERGENCY_SHUTDOWN_OUTDOOR"
    assert 65.0 <= res["confidence_pct"] <= 98.0
    assert res["stagnation_index"] == 100.0

    # Test all sector modules under apocalyptic load
    sectors = SectorIntelligenceEngine.get_all_sectors_summary(
        pm2_5=10000.0,
        pm10=15000.0,
        temp_c=15.0,
        humidity_pct=90.0,
        wind_speed_m_s=0.2,
        forecast_1h=12000.0
    )
    assert len(sectors) == 6
    sec_map = {s["sector_id"]: s for s in sectors}
    # Education, Healthcare, Municipal are Critical (Red)
    assert sec_map["education"]["status_color"] == "#FF2A55"
    assert sec_map["healthcare"]["status_color"] == "#FF2A55"
    assert sec_map["municipal"]["status_color"] == "#FF2A55"
    # HVAC and Industrial are Warning (Orange)
    assert sec_map["hvac"]["status_color"] == "#FF7A00"
    assert sec_map["industrial"]["status_color"] == "#FF7A00"
    # Agriculture at 90% RH indicates urban winter fog/smog, not dry rural stubble burning (RH < 65%)
    assert sec_map["agriculture"]["status"] == "CLEAR_HORIZON"
    assert sec_map["agriculture"]["status_color"] == "#00E599"

    # When apocalyptic PM2.5 occurs with low humidity (e.g. 30%), Agriculture flags UPWIND_PLUME_DETECTED
    agri_dry = SectorIntelligenceEngine.get_agriculture_intelligence(10000.0, 0.2, 30.0)
    assert agri_dry["status"] == "UPWIND_PLUME_DETECTED"
    assert agri_dry["status_color"] == "#FF2A55"

    # Healthcare vulnerability index must be clamped to 100
    health = SectorIntelligenceEngine.get_healthcare_intelligence(10000.0, 12000.0, 90.0)
    assert health["vulnerability_index"] == 100
    assert health["status"] == "CRITICAL_SURGE"

    # HVAC damper must be locked to 10%
    hvac = SectorIntelligenceEngine.get_hvac_intelligence(10000.0, 12000.0, 15.0, 90.0)
    assert hvac["damper_position_pct"] == 10
    assert hvac["filter_life_remaining_days"] == 12  # clamped lower bound


def test_adversarial_critical_hazard_dual_trigger_branch():
    """Verify branch 2 of CRITICAL_HAZARD: (current_pm2_5 >= 120.0 and forecast_1h_pm2_5 >= 140.0)."""
    # Even if max_horizon_pm2_5 is < 150 (e.g. 142.0), branch 2 fires if current >= 120 and forecast >= 140
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="BRANCH2_CRIT",
        current_pm2_5=125.0,
        current_pm10=180.0,
        forecast_1h_pm2_5=142.0,
        forecast_6h_pm2_5=145.0,  # 145 * 0.95 = 137.75
        temperature_c=22.0,
        humidity_pct=60.0,
        wind_speed_m_s=2.0,
        wind_direction_deg=180.0,
        pressure_hpa=1012.0
    )
    assert res["risk_tier"] == "CRITICAL_HAZARD"
    assert res["risk_color"] == "#FF2A55"


# ============================================================================
# 6. SECTOR INTELLIGENCE BOUNDARIES & INVARIANTS
# ============================================================================

def test_adversarial_education_ventilation_levels():
    """Verify Education sector ventilation levels 1, 2, 3, 4 across boundaries."""
    # Level 1: max_pm >= 100
    e1 = SectorIntelligenceEngine.get_education_intelligence(105.0, 90.0)
    assert "Level 1" in [k["value"] for k in e1["kpis"] if k["label"] == "Classroom Vent Stage"][0]

    # Level 2: 50 <= max_pm < 100
    e2 = SectorIntelligenceEngine.get_education_intelligence(65.0, 70.0)
    assert "Level 2" in [k["value"] for k in e2["kpis"] if k["label"] == "Classroom Vent Stage"][0]

    # Level 3: 25 <= max_pm < 50
    e3 = SectorIntelligenceEngine.get_education_intelligence(30.0, 32.0)
    assert "Level 3" in [k["value"] for k in e3["kpis"] if k["label"] == "Classroom Vent Stage"][0]

    # Level 4: max_pm < 25
    e4 = SectorIntelligenceEngine.get_education_intelligence(15.0, 18.0)
    assert "Level 4" in [k["value"] for k in e4["kpis"] if k["label"] == "Classroom Vent Stage"][0]


def test_adversarial_municipal_wind_pm_coupling():
    """Municipal stagnation occurs only when wind < 1.5 AND pm2_5 > 60.0."""
    # Low wind, high PM -> Stagnant
    m1 = SectorIntelligenceEngine.get_municipal_intelligence(pm2_5=65.0, wind_speed=1.0, forecast_1h=70.0)
    assert m1["status"] == "CONGESTION_SMOG_RISK"

    # Low wind, low PM -> Flow normal
    m2 = SectorIntelligenceEngine.get_municipal_intelligence(pm2_5=40.0, wind_speed=1.0, forecast_1h=45.0)
    assert m2["status"] == "FLOW_NORMAL"

    # High wind, high PM -> Flow normal
    m3 = SectorIntelligenceEngine.get_municipal_intelligence(pm2_5=85.0, wind_speed=3.5, forecast_1h=90.0)
    assert m3["status"] == "FLOW_NORMAL"


def test_adversarial_agriculture_dry_smoke_signature():
    """Agriculture smoke plume triggered only when pm2_5 > 65.0 AND humidity < 65.0%."""
    # Dirty & dry -> plume detected
    a1 = SectorIntelligenceEngine.get_agriculture_intelligence(pm2_5=70.0, wind_speed=2.0, humidity_pct=50.0)
    assert a1["status"] == "UPWIND_PLUME_DETECTED"

    # Dirty & humid (fog/smog, not dry smoke) -> clear horizon
    a2 = SectorIntelligenceEngine.get_agriculture_intelligence(pm2_5=70.0, wind_speed=2.0, humidity_pct=80.0)
    assert a2["status"] == "CLEAR_HORIZON"

    # Clean & dry -> clear horizon
    a3 = SectorIntelligenceEngine.get_agriculture_intelligence(pm2_5=30.0, wind_speed=2.0, humidity_pct=40.0)
    assert a3["status"] == "CLEAR_HORIZON"


# ============================================================================
# 7. RANDOMIZED MONTE CARLO / PROPERTY-BASED FUZZING (10,000 RUNS)
# ============================================================================

def test_adversarial_property_based_fuzzing_10000_iterations():
    """Stress-test decision engine and all sector engines with 10,000 randomized combinations.
    
    Verifies that no input combination crashes the system and all mathematical invariants hold.
    """
    random.seed(42)
    valid_risk_tiers = {"OPTIMAL_NORMAL", "MODERATE_ADVISORY", "HIGH_ALERT", "CRITICAL_HAZARD"}
    valid_dispersion_classes = {"POOR_TRAPPED_INVERSION", "MODERATE_DISPERSION", "EXCELLENT_VENTILATION"}
    valid_recess_ratings = {"PROHIBITED", "RESTRICTED_LOW_IMPACT", "FULLY_SAFE"}
    valid_hvac_dampers = {10, 20, 50, 80}

    for i in range(10000):
        # Generate adversarial telemetry values
        pm2_5 = max(0.0, random.uniform(-10.0, 1000.0))
        pm10 = max(0.0, random.uniform(-10.0, 2000.0))
        f_1h = max(0.0, random.uniform(-10.0, 1000.0))
        f_6h = max(0.0, random.uniform(-10.0, 1000.0))
        temp = random.uniform(-30.0, 60.0)
        hum = max(0.0, min(100.0, random.uniform(-10.0, 120.0)))
        wind_spd = max(0.0, random.uniform(-5.0, 60.0))
        wind_dir = random.uniform(0.0, 360.0)
        press = random.uniform(850.0, 1060.0)
        rain = random.choice([True, False])

        # 1. Evaluate Decision Engine
        dec = OperationalDecisionEngine.evaluate_decisions(
            campus_code=f"FUZZ_{i}",
            current_pm2_5=pm2_5,
            current_pm10=pm10,
            forecast_1h_pm2_5=f_1h,
            forecast_6h_pm2_5=f_6h,
            temperature_c=temp,
            humidity_pct=hum,
            wind_speed_m_s=wind_spd,
            wind_direction_deg=wind_dir,
            pressure_hpa=press,
            rain_flag=rain
        )

        # Invariants Check
        assert dec["risk_tier"] in valid_risk_tiers
        assert 65.0 <= dec["confidence_pct"] <= 98.0
        assert 0.0 <= dec["stagnation_index"] <= 100.0
        assert dec["dispersion_class"] in valid_dispersion_classes
        assert isinstance(dec["active_triggers"], list)
        assert len(dec["active_triggers"]) >= 2

        # 2. Evaluate All Sectors
        sectors = SectorIntelligenceEngine.get_all_sectors_summary(
            pm2_5=pm2_5,
            pm10=pm10,
            temp_c=temp,
            humidity_pct=hum,
            wind_speed_m_s=wind_spd,
            forecast_1h=f_1h
        )
        assert len(sectors) == 6

        # Granular sector invariant checks
        edu = SectorIntelligenceEngine.get_education_intelligence(pm2_5, f_1h)
        assert edu["recess_safety_rating"] in valid_recess_ratings
        assert 0 <= edu["safety_index"] <= 100

        health = SectorIntelligenceEngine.get_healthcare_intelligence(pm2_5, f_1h, hum)
        assert 0 <= health["vulnerability_index"] <= 100

        hvac = SectorIntelligenceEngine.get_hvac_intelligence(pm2_5, f_1h, temp, hum)
        assert hvac["damper_position_pct"] in valid_hvac_dampers
        assert hvac["filter_life_remaining_days"] >= 12

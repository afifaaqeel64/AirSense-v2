"""Challenger 2 Empirical Verification Test Suite.

Validates:
1. 10,000 randomized property fuzzing iterations across all decision engine inputs and sector intelligence.
2. Sector coupling consistency under sudden emergency triggers (spikes, inversions, dust storms, smoke plumes).
3. Alert acknowledgment idempotency under concurrent trigger floods.
"""

import asyncio
import random
import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from services.decision_intelligence.decision_engine import OperationalDecisionEngine
from services.decision_intelligence.sector_intelligence import SectorIntelligenceEngine
from services.decision_intelligence.news_and_alerts import NewsAndAlertsEngine


def test_empirical_10000_property_fuzzing_iterations():
    """Validate 10,000 randomized property fuzzing iterations across all decision engine and sector inputs."""
    random.seed(9999)
    valid_risk_tiers = {"OPTIMAL_NORMAL", "MODERATE_ADVISORY", "HIGH_ALERT", "CRITICAL_HAZARD"}
    valid_dispersion_classes = {"POOR_TRAPPED_INVERSION", "MODERATE_DISPERSION", "EXCELLENT_VENTILATION"}
    valid_recess = {"PROHIBITED", "RESTRICTED_LOW_IMPACT", "FULLY_SAFE"}
    valid_dampers = {10, 20, 50, 80}

    for i in range(10000):
        pm2_5 = max(0.0, random.uniform(-50.0, 3000.0))
        pm10 = max(0.0, random.uniform(-50.0, 5000.0))
        f_1h = max(0.0, random.uniform(-50.0, 3000.0))
        f_6h = max(0.0, random.uniform(-50.0, 3000.0))
        temp = random.uniform(-40.0, 65.0)
        hum = max(0.0, min(100.0, random.uniform(-20.0, 120.0)))
        wind_spd = max(0.0, random.uniform(-10.0, 100.0))
        wind_dir = random.uniform(0.0, 360.0)
        press = random.uniform(800.0, 1100.0)
        rain = random.choice([True, False])

        dec = OperationalDecisionEngine.evaluate_decisions(
            f"FZ_CHALLENGER2_{i}", pm2_5, pm10, f_1h, f_6h, temp, hum, wind_spd, wind_dir, press, rain
        )

        assert dec["risk_tier"] in valid_risk_tiers, f"Invalid risk tier {dec['risk_tier']} at iteration {i}"
        assert 65.0 <= dec["confidence_pct"] <= 98.0, f"Confidence out of bounds: {dec['confidence_pct']}"
        assert 0.0 <= dec["stagnation_index"] <= 100.0, f"Stagnation out of bounds: {dec['stagnation_index']}"
        assert dec["dispersion_class"] in valid_dispersion_classes
        assert isinstance(dec["active_triggers"], list)

        # Sector intelligence validation
        sectors = SectorIntelligenceEngine.get_all_sectors_summary(pm2_5, pm10, temp, hum, wind_spd, f_1h)
        assert len(sectors) == 6, f"Expected 6 sectors, got {len(sectors)}"

        edu = SectorIntelligenceEngine.get_education_intelligence(pm2_5, f_1h)
        assert edu["recess_safety_rating"] in valid_recess
        assert 0 <= edu["safety_index"] <= 100

        health = SectorIntelligenceEngine.get_healthcare_intelligence(pm2_5, f_1h, hum)
        assert 0 <= health["vulnerability_index"] <= 100

        hvac = SectorIntelligenceEngine.get_hvac_intelligence(pm2_5, f_1h, temp, hum)
        assert hvac["damper_position_pct"] in valid_dampers
        assert hvac["filter_life_remaining_days"] >= 12

        ind = SectorIntelligenceEngine.get_industrial_intelligence(pm2_5, pm10, wind_spd)
        assert ind["status"] in {"DUST_SUPPRESSION_TRIGGER", "COMPLIANT"}

        agri = SectorIntelligenceEngine.get_agriculture_intelligence(pm2_5, wind_spd, hum)
        assert agri["status"] in {"UPWIND_PLUME_DETECTED", "CLEAR_HORIZON"}


def test_sector_coupling_consistency_under_sudden_emergency():
    """Verify sector coupling consistency when an emergency trigger suddenly activates."""
    # Baseline condition: Clean air
    base_pm25 = 15.0
    base_pm10 = 25.0
    base_temp = 22.0
    base_hum = 45.0
    base_wind = 4.0
    base_f1 = 18.0

    dec_base = OperationalDecisionEngine.evaluate_decisions(
        "ISB_TEST", base_pm25, base_pm10, base_f1, 20.0, base_temp, base_hum, base_wind, 180.0, 1013.0
    )
    secs_base = SectorIntelligenceEngine.get_all_sectors_summary(
        base_pm25, base_pm10, base_temp, base_hum, base_wind, base_f1
    )

    assert dec_base["risk_tier"] == "OPTIMAL_NORMAL"
    assert all(s["status_color"] in {"#00E599", "#36D6E7"} for s in secs_base)

    # Sudden emergency trigger: Catastrophic winter smog & inversion shock
    em_pm25 = 280.0
    em_pm10 = 450.0
    em_temp = 8.0
    em_hum = 92.0
    em_wind = 0.4
    em_f1 = 320.0

    dec_em = OperationalDecisionEngine.evaluate_decisions(
        "ISB_TEST", em_pm25, em_pm10, em_f1, 350.0, em_temp, em_hum, em_wind, 90.0, 1022.0
    )
    secs_em = SectorIntelligenceEngine.get_all_sectors_summary(
        em_pm25, em_pm10, em_temp, em_hum, em_wind, em_f1
    )

    # 1. Decision engine coupling
    assert dec_em["risk_tier"] == "CRITICAL_HAZARD"
    assert dec_em["action_code"] == "ACT_EMERGENCY_SHUTDOWN_OUTDOOR"
    assert dec_em["stagnation_index"] >= 80.0
    assert dec_em["dispersion_class"] == "POOR_TRAPPED_INVERSION"

    sec_dict = {s["sector_id"]: s for s in secs_em}

    # 2. Education coupling
    assert sec_dict["education"]["status"] == "RESTRICTED"
    assert sec_dict["education"]["recess_safety_rating"] == "PROHIBITED"
    assert sec_dict["education"]["safety_index"] <= 20
    gates = next(a for a in sec_dict["education"]["actuators"] if "Gates" in a["name"])
    assert gates["state"] == "LOCKED"

    # 3. Healthcare coupling
    assert sec_dict["healthcare"]["status"] == "CRITICAL_SURGE"
    assert sec_dict["healthcare"]["vulnerability_index"] >= 70
    scrubbers = next(a for a in sec_dict["healthcare"]["actuators"] if "Scrubbers" in a["name"])
    assert scrubbers["state"] == "MAX_OVERPRESSURE"

    # 4. HVAC coupling
    assert sec_dict["hvac"]["damper_position_pct"] == 10
    assert sec_dict["hvac"]["status"] == "FILTER_PURGE"

    # 5. Municipal coupling (due to wind < 1.5 and PM > 60)
    assert sec_dict["municipal"]["status"] == "CONGESTION_SMOG_RISK"
    vms = next(a for a in sec_dict["municipal"]["actuators"] if "VMS" in a["name"])
    assert vms["state"] == "SMOG_ROUTE_ACTIVE"
    assert vms["active"] is True

    # 6. Industrial coupling (PM10 > 150)
    assert sec_dict["industrial"]["status"] == "DUST_SUPPRESSION_TRIGGER"
    cannons = next(a for a in sec_dict["industrial"]["actuators"] if "Mist Cannons" in a["name"])
    assert cannons["state"] == "AUTORUN"


@pytest.mark.asyncio
async def test_alert_acknowledgment_idempotency_under_concurrent_trigger_floods():
    """Verify alert acknowledgment idempotency when hammered by 100 concurrent requests."""
    test_alert_id = "flood_alert_test_999"

    # Reset any previous acknowledgment for clean test
    NewsAndAlertsEngine._acknowledged_alerts.discard(test_alert_id)
    assert test_alert_id not in NewsAndAlertsEngine._acknowledged_alerts

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Generate a concurrent flood of 100 acknowledgment requests for the same alert
        tasks = [
            client.post(f"/api/v2/alerts/{test_alert_id}/acknowledge")
            for _ in range(100)
        ]
        responses = await asyncio.gather(*tasks)

        # All 100 requests must succeed with 200 OK and idempotent response payload
        for res in responses:
            assert res.status_code == 200
            data = res.json()
            assert data["alert_id"] == test_alert_id
            assert data["status"] == "ACKNOWLEDGED"

        # The alert must be acknowledged in the engine
        assert test_alert_id in NewsAndAlertsEngine._acknowledged_alerts

        # Subsequent fetch must reflect acknowledged state
        alerts = NewsAndAlertsEngine.get_live_alerts(pm2_5=999.0, forecast_1h=999.0, wind_speed=1.0)
        # Note: live alerts generate id based on pm2.5, let's verify acknowledge on that ID
        live_crit_id = alerts[0]["id"]
        
        # Concurrently acknowledge live_crit_id with 50 tasks
        tasks_live = [
            client.post(f"/api/v2/alerts/{live_crit_id}/acknowledge")
            for _ in range(50)
        ]
        responses_live = await asyncio.gather(*tasks_live)
        for res in responses_live:
            assert res.status_code == 200
            assert res.json()["status"] == "ACKNOWLEDGED"

        refetched_alerts = NewsAndAlertsEngine.get_live_alerts(pm2_5=999.0, forecast_1h=999.0, wind_speed=1.0)
        matched = next(a for a in refetched_alerts if a["id"] == live_crit_id)
        assert matched["acknowledged"] is True

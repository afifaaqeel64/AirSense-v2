"""Unit tests for Next-Gen Operational Decision Intelligence Services."""

import pytest
from services.decision_intelligence.decision_engine import OperationalDecisionEngine
from services.decision_intelligence.sector_intelligence import SectorIntelligenceEngine
from services.decision_intelligence.news_and_alerts import NewsAndAlertsEngine


def test_operational_decision_engine_normal_tier():
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="ISB_CAMPUS",
        current_pm2_5=18.0,
        current_pm10=30.0,
        forecast_1h_pm2_5=20.0,
        forecast_6h_pm2_5=22.0,
        temperature_c=24.0,
        humidity_pct=50.0,
        wind_speed_m_s=3.5,
        wind_direction_deg=180.0,
        pressure_hpa=1013.25,
        rain_flag=False
    )
    assert res["risk_tier"] == "OPTIMAL_NORMAL"
    assert "NORMAL OPERATIONS" in res["primary_directive"]
    assert res["confidence_pct"] > 70.0
    assert len(res["active_triggers"]) > 0


def test_operational_decision_engine_critical_hazard():
    res = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KAR_CAMPUS",
        current_pm2_5=165.0,
        current_pm10=240.0,
        forecast_1h_pm2_5=180.0,
        forecast_6h_pm2_5=190.0,
        temperature_c=16.0,
        humidity_pct=85.0,
        wind_speed_m_s=0.8,
        wind_direction_deg=45.0,
        pressure_hpa=1006.0,
        rain_flag=False
    )
    assert res["risk_tier"] == "CRITICAL_HAZARD"
    assert "EMERGENCY CONTAINMENT" in res["primary_directive"]
    assert res["dispersion_class"] == "POOR_TRAPPED_INVERSION"


def test_sector_intelligence_all_six_sectors():
    sectors = SectorIntelligenceEngine.get_all_sectors_summary(
        pm2_5=45.0,
        pm10=70.0,
        temp_c=25.0,
        humidity_pct=60.0,
        wind_speed_m_s=2.5,
        forecast_1h=52.0
    )
    assert len(sectors) == 6
    sector_ids = [s["sector_id"] for s in sectors]
    assert "education" in sector_ids
    assert "healthcare" in sector_ids
    assert "hvac" in sector_ids
    assert "municipal" in sector_ids
    assert "industrial" in sector_ids
    assert "agriculture" in sector_ids


def test_news_and_alerts_engine():
    alerts = NewsAndAlertsEngine.get_live_alerts(pm2_5=85.0, forecast_1h=90.0, wind_speed=1.0)
    assert len(alerts) >= 2
    assert any(a["severity"] == "CRITICAL" for a in alerts)

    # Test alert acknowledgment
    alert_id = alerts[0]["id"]
    NewsAndAlertsEngine.acknowledge_alert(alert_id)
    refreshed_alerts = NewsAndAlertsEngine.get_live_alerts(pm2_5=85.0, forecast_1h=90.0, wind_speed=1.0)
    acknowledged_alt = next((a for a in refreshed_alerts if a["id"] == alert_id), None)
    assert acknowledged_alt is not None
    assert acknowledged_alt["acknowledged"] is True

    # Test news
    news = NewsAndAlertsEngine.get_curated_news()
    assert len(news) >= 3
    assert "Pak-EPA" in news[0]["source"] or "Environmental" in news[0]["source"]

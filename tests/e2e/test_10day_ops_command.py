import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_10day_horizon_endpoint():
    response = client.get("/api/v2/decisions/10-day-horizon?city=lahore")
    assert response.status_code == 200
    data = response.json()
    
    assert data["city"] == "LAHORE"
    assert data["forecast_horizon_days"] == 10
    assert "cumulative_financial_summary" in data
    assert "daily_horizons" in data
    assert len(data["daily_horizons"]) == 10

    horizons_by_day = {h["day"]: h for h in data["daily_horizons"]}
    assert len(horizons_by_day) == 10

    # 1. Verify exact dynamic tightening confidence interval regimes
    # - Days 10–7: Macro analog decadal matching (bounds: ±18%–22%)
    assert 18.0 <= horizons_by_day[10]["confidence_margin_pct"] <= 22.0, (
        f"Day 10 margin {horizons_by_day[10]['confidence_margin_pct']}% not in [18.0, 22.0]"
    )
    assert 18.0 <= horizons_by_day[7]["confidence_margin_pct"] <= 22.0, (
        f"Day 7 margin {horizons_by_day[7]['confidence_margin_pct']}% not in [18.0, 22.0]"
    )

    # - Days 6–4: Boundary layer trajectory convergence (bounds: ±12%–15%)
    assert 12.0 <= horizons_by_day[6]["confidence_margin_pct"] <= 15.0, (
        f"Day 6 margin {horizons_by_day[6]['confidence_margin_pct']}% not in [12.0, 15.0]"
    )
    assert 12.0 <= horizons_by_day[4]["confidence_margin_pct"] <= 15.0, (
        f"Day 4 margin {horizons_by_day[4]['confidence_margin_pct']}% not in [12.0, 15.0]"
    )

    # - Days 3–1: Hyper-local ground sensor fusion (bounds: ±4.5%–7.5%)
    assert 4.5 <= horizons_by_day[3]["confidence_margin_pct"] <= 7.5, (
        f"Day 3 margin {horizons_by_day[3]['confidence_margin_pct']}% not in [4.5, 7.5]"
    )
    assert 4.5 <= horizons_by_day[1]["confidence_margin_pct"] <= 7.5, (
        f"Day 1 margin {horizons_by_day[1]['confidence_margin_pct']}% not in [4.5, 7.5]"
    )

    # 2. Strict monotonic narrowing: margin(d) < margin(d+1) for all d in 1..9
    for d in range(1, 10):
        margin_current = horizons_by_day[d]["confidence_margin_pct"]
        margin_next = horizons_by_day[d + 1]["confidence_margin_pct"]
        assert margin_current < margin_next, (
            f"Monotonicity violation: Day {d} ({margin_current}%) >= Day {d+1} ({margin_next}%)"
        )

    # 3. Verify confidence score bounds and monotonic increase from Day 10 to Day 1
    # Day 1: 0.94–0.98
    assert 0.94 <= horizons_by_day[1]["confidence_score"] <= 0.98, (
        f"Day 1 confidence {horizons_by_day[1]['confidence_score']} not in [0.94, 0.98]"
    )
    # Day 6: 0.85–0.91
    assert 0.85 <= horizons_by_day[6]["confidence_score"] <= 0.91, (
        f"Day 6 confidence {horizons_by_day[6]['confidence_score']} not in [0.85, 0.91]"
    )
    # Day 10: 0.72–0.81
    assert 0.72 <= horizons_by_day[10]["confidence_score"] <= 0.81, (
        f"Day 10 confidence {horizons_by_day[10]['confidence_score']} not in [0.72, 0.81]"
    )

    # Strict monotonic increasing of confidence score: score(d) > score(d+1)
    for d in range(1, 10):
        score_current = horizons_by_day[d]["confidence_score"]
        score_next = horizons_by_day[d + 1]["confidence_score"]
        assert score_current > score_next, (
            f"Confidence monotonicity violation: Day {d} ({score_current}) <= Day {d+1} ({score_next})"
        )

    # 4. Verify disruption_risk and sentiment_disruption across all daily horizons
    for h in data["daily_horizons"]:
        assert "disruption_risk" in h, f"Missing disruption_risk in Day {h['day']}"
        assert isinstance(h["disruption_risk"], (int, float))
        assert 0.0 <= h["disruption_risk"] <= 1.0, (
            f"Day {h['day']} disruption_risk {h['disruption_risk']} out of [0.0, 1.0]"
        )

        assert "sentiment_disruption" in h, f"Missing sentiment_disruption in Day {h['day']}"
        assert isinstance(h["sentiment_disruption"], (int, float))
        assert 0.0 <= h["sentiment_disruption"] <= 100.0, (
            f"Day {h['day']} sentiment_disruption {h['sentiment_disruption']} out of [0.0, 100.0]"
        )

        assert "target_date" in h, f"Missing target_date in Day {h['day']}"
        assert len(h["target_date"].split("-")) == 3, f"Invalid date format: {h['target_date']}"

        assert "ci_lower" in h or "ci_lower_pm2_5" in h
        assert "ci_upper" in h or "ci_upper_pm2_5" in h
        pm_val = h.get("predicted_pm2_5", h.get("projected_pm2_5"))
        ci_lo = h.get("ci_lower", h.get("ci_lower_pm2_5"))
        ci_hi = h.get("ci_upper", h.get("ci_upper_pm2_5"))
        assert ci_lo <= pm_val <= ci_hi, f"PM2.5 {pm_val} outside CI [{ci_lo}, {ci_hi}]"

    # 5. Verify financial loss calculations
    assert data["cumulative_financial_summary"]["total_savings_mitigated_pkr"] > 0
    assert data["cumulative_financial_summary"]["net_loss_avoidance_roi_pct"] > 60.0


def test_10day_horizon_multiple_cities():
    """Validates 10-day horizon across different cities (Karachi, Islamabad)."""
    for city in ["karachi", "islamabad"]:
        res = client.get(f"/api/v2/decisions/10-day-horizon?city={city}")
        assert res.status_code == 200
        d = res.json()
        assert d["city"] == city.upper()
        assert len(d["daily_horizons"]) == 10
        h_by_day = {h["day"]: h for h in d["daily_horizons"]}
        assert 18.0 <= h_by_day[10]["confidence_margin_pct"] <= 22.0
        assert 12.0 <= h_by_day[6]["confidence_margin_pct"] <= 15.0
        assert 4.5 <= h_by_day[1]["confidence_margin_pct"] <= 7.5
        for d_idx in range(1, 10):
            assert h_by_day[d_idx]["confidence_margin_pct"] < h_by_day[d_idx + 1]["confidence_margin_pct"]


def test_10day_model_inference_and_fallback():
    """Validates MultiHorizonImpactModel directly with trained model and fallback."""
    from services.decision_intelligence.multi_horizon_impact_model import MultiHorizonImpactModel
    model = MultiHorizonImpactModel()

    # Verify models loaded from D: drive
    assert len(model.models) >= 4, "Trained models not loaded from joblib bundle"
    assert "enforcement_prob" in model.models
    assert "unmitigated_loss" in model.models
    assert "mitigated_savings" in model.models
    assert "sentiment_disruption" in model.models

    # Run inference with loaded models
    traj = model.generate_10day_trajectory(city="lahore", current_pm2_5=300.0)
    assert len(traj["daily_horizons"]) == 10
    d1 = next(h for h in traj["daily_horizons"] if h["day"] == 1)
    d10 = next(h for h in traj["daily_horizons"] if h["day"] == 10)
    assert d1["confidence_margin_pct"] == 4.5
    assert d10["confidence_margin_pct"] == 21.8
    assert 0.0 <= d1["disruption_risk"] <= 1.0
    assert 0.0 <= d10["disruption_risk"] <= 1.0

    # Test fallback path when models dictionary is cleared
    model.models = {}
    fallback_traj = model.generate_10day_trajectory(city="lahore", current_pm2_5=300.0)
    assert len(fallback_traj["daily_horizons"]) == 10
    fb_d1 = next(h for h in fallback_traj["daily_horizons"] if h["day"] == 1)
    fb_d10 = next(h for h in fallback_traj["daily_horizons"] if h["day"] == 10)
    assert fb_d1["confidence_margin_pct"] == 4.5
    assert fb_d10["confidence_margin_pct"] == 21.8
    assert 0.0 <= fb_d1["disruption_risk"] <= 1.0


def test_scraping_radar_endpoint():
    response = client.get("/api/v2/decisions/scraping-radar")
    assert response.status_code == 200
    data = response.json()
    
    assert data["cadence"] == "HOURLY_CONTINUOUS"
    assert data["total_domains"] == 8
    assert len(data["radar"]) == 8
    
    domain_keys = [d["domain_key"] for d in data["radar"]]
    assert "epa_gazettes" in domain_keys
    assert "motorway_traffic" in domain_keys
    assert "education_circulars" in domain_keys
    assert "biomass_hotspots" in domain_keys

def test_financial_loss_matrix_endpoint():
    response = client.get("/api/v2/decisions/financial-loss-matrix?severity_factor=1.2")
    assert response.status_code == 200
    data = response.json()
    
    assert "sectors" in data
    assert "aggregate" in data
    assert "logistics" in data["sectors"]
    assert "manufacturing" in data["sectors"]
    assert data["aggregate"]["total_mitigated_pkr"] > 0
    assert data["aggregate"]["overall_mitigation_efficiency_pct"] > 75.0

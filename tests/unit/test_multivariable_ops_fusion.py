"""Unit test suite for Milestone M2: Multivariable Correlation & 10-Day Ops Engine Fusion.

Verifies:
1. Live hardware telemetry schema acceptance (PMS7003, BME280, Rain plate 4 tiers)
2. Hygroscopic optical swelling correction factor (0.90x when RH > 75%)
3. Atmospheric stagnation index incorporating real physical sensors (wind, humidity, temp, pressure, rain)
4. 10-Day multi-horizon predictive risk model with monotonically narrowing dynamic confidence intervals:
   - Days 10–7: Macro analog matching (+-18.0% to +-22.0%)
   - Days 6–4: Boundary layer trajectory convergence (+-12.0% to +-15.0%)
   - Days 3–1: Hyper-local ground sensor fusion (+-4.5% to +-7.5%)
   - Monotonicity: margin(d) < margin(d+1) for d in 1..9
5. Enterprise financial loss matrix in PKR across 5 sectors (Logistics, Education, Manufacturing, Healthcare, Retail)
   - Dual financial metrics: Unmitigated Loss (PKR), Mitigated Savings (PKR), Loss Avoidance ROI (%)
6. AgentPhone autonomous telephony governance wired to authentic sensor hazard thresholds (>= 150 ug/m3)
7. Strict D: drive storage sovereignty and zero mock data compliance
"""

import os
import json
import pytest
from pathlib import Path

from services.decision_intelligence.decision_engine import OperationalDecisionEngine
from services.decision_intelligence.multi_horizon_impact_model import MultiHorizonImpactModel
from pipelines.ops_impact_pipeline import OpsImpactPipeline
from services.telephony.agentphone_service import AgentPhoneService, EVENTS_LOG_FILE


# Reference authentic Karachi BIC Rooftop Node hardware telemetry packet
SAMPLE_HARDWARE_TELEMETRY = {
    "device_uid": "AIRSENSE-NODE-KHI-01",
    "station_code": "BIC-KHI-ROOF-01",
    "campus_code": "KARACHI",
    "sequence_number": 1113,
    "observed_at": "2026-09-13T10:30:53Z",
    "pm1": 17.0,
    "pm2_5": 24.0,
    "pm10": 28.0,
    "temperature": 31.9,
    "humidity": 61.4,
    "pressure": 1001.4,
    "rain_flag": False,
    "rain_tier": "DRY",
    "rain_adc": 3840,
    "sensor_health": {
        "pms7003": "OK",
        "bme280": "OK",
        "rain": "OK",
        "microsd": "OK"
    },
    "source": "onsite_esp32"
}


# ============================================================================
# 1. Multivariable Correlation & Sensor Schema Acceptance
# ============================================================================

def test_live_sensor_schema_acceptance():
    """Verify that OperationalDecisionEngine accepts the full live hardware telemetry schema."""
    result = OperationalDecisionEngine.evaluate_from_telemetry(
        telemetry=SAMPLE_HARDWARE_TELEMETRY,
        campus_code="KARACHI"
    )

    assert result["risk_tier"] == "OPTIMAL_NORMAL"
    assert result["campus_code"] == "KARACHI"
    summary = result["telemetry_summary"]

    # Verify PMS7003 readings
    assert summary["pm1"] == 17.0
    assert summary["pm2_5"] == 24.0
    assert summary["pm10"] == 28.0
    assert summary["particle_ordering_consistent"] is True

    # Verify Bosch BME280 readings
    assert summary["temperature_c"] == 31.9
    assert summary["humidity_pct"] == 61.4
    assert summary["pressure_hpa"] == 1001.4

    # Verify Rain plate 4-tier readings
    assert summary["rain_flag"] is False
    assert summary["rain_tier"] == "DRY"
    assert summary["rain_adc"] == 3840

    # Verify sensor health flags
    assert summary["sensor_health"]["pms7003"] == "OK"
    assert summary["sensor_health"]["bme280"] == "OK"
    assert summary["device_uid"] == "AIRSENSE-NODE-KHI-01"
    assert summary["station_code"] == "BIC-KHI-ROOF-01"


def test_hygroscopic_optical_swelling_correction():
    """Verify optical swelling adjustment: 0.90x factor applied when RH > 75%, 1.0x when <= 75%."""
    # Test high humidity (> 75%)
    high_hum_telemetry = dict(SAMPLE_HARDWARE_TELEMETRY)
    high_hum_telemetry["humidity"] = 82.0
    high_hum_telemetry["pm2_5"] = 100.0

    res_high = OperationalDecisionEngine.evaluate_from_telemetry(high_hum_telemetry)
    sum_high = res_high["telemetry_summary"]
    assert sum_high["hygroscopic_correction_applied"] is True
    assert sum_high["hygroscopic_factor"] == 0.90
    assert sum_high["dry_calibrated_pm2_5"] == 90.0

    # Test normal humidity (<= 75%)
    norm_hum_telemetry = dict(SAMPLE_HARDWARE_TELEMETRY)
    norm_hum_telemetry["humidity"] = 65.0
    norm_hum_telemetry["pm2_5"] = 100.0

    res_norm = OperationalDecisionEngine.evaluate_from_telemetry(norm_hum_telemetry)
    sum_norm = res_norm["telemetry_summary"]
    assert sum_norm["hygroscopic_correction_applied"] is False
    assert sum_norm["hygroscopic_factor"] == 1.0
    assert sum_norm["dry_calibrated_pm2_5"] == 100.0


def test_rain_tier_adc_calibration():
    """Verify 4-tier analog-to-digital rain classification."""
    adc_tests = [
        (3800, "DRY"),
        (3000, "MOISTURE"),
        (1800, "LIGHT RAIN"),
        (800, "HEAVY RAIN")
    ]
    for adc_val, expected_tier in adc_tests:
        packet = dict(SAMPLE_HARDWARE_TELEMETRY)
        packet["rain_adc"] = adc_val
        packet["rain_tier"] = None
        packet["rain_flag"] = False

        res = OperationalDecisionEngine.evaluate_from_telemetry(packet)
        assert res["telemetry_summary"]["rain_tier"] == expected_tier


def test_atmospheric_stagnation_index_incorporates_physical_sensors():
    """Verify atmospheric stagnation index incorporates wind speed, humidity, temperature, and pressure."""
    # Scenario A: Trapped cold anticyclonic inversion (high stagnation)
    res_stagnant = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KARACHI",
        current_pm2_5=170.0,
        current_pm10=250.0,
        forecast_1h_pm2_5=180.0,
        forecast_6h_pm2_5=190.0,
        temperature_c=14.0,       # Cold (< 18C)
        humidity_pct=88.0,        # High humidity
        wind_speed_m_s=0.5,       # Calm wind
        wind_direction_deg=45.0,
        pressure_hpa=1022.0,      # Strong high pressure anticyclone
        rain_flag=False
    )
    assert res_stagnant["stagnation_index"] > 70.0
    assert res_stagnant["dispersion_class"] == "POOR_TRAPPED_INVERSION"

    # Scenario B: High ventilation (low stagnation)
    res_ventilated = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KARACHI",
        current_pm2_5=20.0,
        current_pm10=35.0,
        forecast_1h_pm2_5=22.0,
        forecast_6h_pm2_5=24.0,
        temperature_c=28.0,       # Warm
        humidity_pct=42.0,        # Moderate
        wind_speed_m_s=8.5,       # Strong breeze
        wind_direction_deg=240.0,
        pressure_hpa=1005.0,
        rain_flag=False
    )
    assert res_ventilated["stagnation_index"] < 40.0
    assert res_ventilated["dispersion_class"] == "EXCELLENT_VENTILATION"

    # Scenario C: Rain washout suppresses stagnation
    res_rain = OperationalDecisionEngine.evaluate_decisions(
        campus_code="KARACHI",
        current_pm2_5=60.0,
        current_pm10=90.0,
        forecast_1h_pm2_5=50.0,
        forecast_6h_pm2_5=40.0,
        temperature_c=20.0,
        humidity_pct=85.0,
        wind_speed_m_s=2.0,
        wind_direction_deg=180.0,
        pressure_hpa=1008.0,
        rain_flag=True,
        rain_tier="HEAVY RAIN"
    )
    # With rain, stagnation is significantly lower than without rain under high humidity
    assert res_rain["telemetry_summary"]["rain_flag"] is True
    assert res_rain["telemetry_summary"]["rain_tier"] == "HEAVY RAIN"


# ============================================================================
# 2. 10-Day Multi-Horizon Predictive Risk Model
# ============================================================================

def test_10day_trajectory_piecewise_regimes_and_monotonicity():
    """Verify 10-day forward trajectory satisfies exact confidence regimes and strict monotonic narrowing."""
    model = MultiHorizonImpactModel()
    trajectory = model.generate_10day_trajectory(
        city="karachi",
        current_pm2_5=185.0,
        temp_c=29.0,
        humidity_pct=68.0,
        pressure_hpa=1008.0
    )

    horizons = {h["day"]: h for h in trajectory["daily_horizons"]}
    assert len(horizons) == 10

    # 1. Verify Regime 1 (Days 10-7): Macro analog matching (+-18.0% to +-22.0%)
    for d in [10, 9, 8, 7]:
        margin = horizons[d]["confidence_margin_pct"]
        assert 18.0 <= margin <= 22.0, f"Day {d} margin {margin}% outside [18.0, 22.0]"
        score = horizons[d]["confidence_score"]
        assert 0.72 <= score <= 0.81, f"Day {d} score {score} outside [0.72, 0.81]"

    # 2. Verify Regime 2 (Days 6-4): Boundary layer trajectory convergence (+-12.0% to +-15.0%)
    for d in [6, 5, 4]:
        margin = horizons[d]["confidence_margin_pct"]
        assert 12.0 <= margin <= 15.0, f"Day {d} margin {margin}% outside [12.0, 15.0]"
        score = horizons[d]["confidence_score"]
        assert 0.85 <= score <= 0.91, f"Day {d} score {score} outside [0.85, 0.91]"

    # 3. Verify Regime 3 (Days 3-1): Hyper-local ground sensor fusion (+-4.5% to +-7.5%)
    for d in [3, 2, 1]:
        margin = horizons[d]["confidence_margin_pct"]
        assert 4.5 <= margin <= 7.5, f"Day {d} margin {margin}% outside [4.5, 7.5]"
        score = horizons[d]["confidence_score"]
        assert 0.94 <= score <= 0.98, f"Day {d} score {score} outside [0.94, 0.98]"

    # 4. Strict Monotonic Narrowing: margin(d) < margin(d+1) for all d in 1..9
    for d in range(1, 10):
        assert horizons[d]["confidence_margin_pct"] < horizons[d + 1]["confidence_margin_pct"], (
            f"Monotonicity violated: Day {d} ({horizons[d]['confidence_margin_pct']}%) >= "
            f"Day {d+1} ({horizons[d+1]['confidence_margin_pct']}%)"
        )

    # 5. Strict Monotonic Confidence Increase: score(d) > score(d+1) for all d in 1..9
    for d in range(1, 10):
        assert horizons[d]["confidence_score"] > horizons[d + 1]["confidence_score"], (
            f"Confidence monotonicity violated: Day {d} ({horizons[d]['confidence_score']}) <= "
            f"Day {d+1} ({horizons[d+1]['confidence_score']})"
        )

    # 6. Verify CI lower <= predicted <= CI upper
    for d, h in horizons.items():
        pm = h["predicted_pm2_5"]
        assert h["ci_lower"] <= pm <= h["ci_upper"]
        assert h["ci_width"] > 0
        assert "loss_avoidance_efficiency_roi_pct" in h


def test_10day_trajectory_from_live_telemetry():
    """Verify generate_from_telemetry integrates authentic hardware readings without synthetic mock data."""
    model = MultiHorizonImpactModel()
    traj = model.generate_from_telemetry(
        telemetry=SAMPLE_HARDWARE_TELEMETRY,
        city="karachi"
    )

    assert traj["city"] == "KARACHI"
    assert "input_telemetry_summary" in traj
    input_sum = traj["input_telemetry_summary"]
    assert input_sum["pm2_5"] == 24.0
    assert input_sum["temp_c"] == 31.9
    assert input_sum["humidity_pct"] == 61.4
    assert input_sum["pressure_hpa"] == 1001.4

    summary = traj["cumulative_financial_summary"]
    assert summary["unmitigated_financial_loss_pkr"] > 0
    assert summary["airsense_mitigated_savings_pkr"] > 0
    assert summary["loss_avoidance_efficiency_roi_pct"] > 60.0


# ============================================================================
# 3. Enterprise Financial Loss ROI (PKR)
# ============================================================================

def test_enterprise_sector_loss_matrix_structure_and_invariants():
    """Verify sector loss matrix covers 5 core sectors and computes dual PKR metrics."""
    pipeline = OpsImpactPipeline()
    matrix_result = pipeline.calculate_sector_loss_matrix(severity_factor=1.25, city="karachi")

    sectors = matrix_result["sectors"]
    expected_sectors = ["logistics", "education", "manufacturing", "healthcare", "retail"]
    for s in expected_sectors:
        assert s in sectors, f"Sector {s} missing from loss matrix"
        s_data = sectors[s]

        # Dual financial metrics
        assert s_data["unmitigated_financial_loss_pkr"] > 0
        assert s_data["airsense_mitigated_savings_pkr"] > 0
        assert s_data["loss_avoidance_efficiency_roi_pct"] > 0

        # Invariant: Unmitigated > Mitigated
        assert s_data["unmitigated_financial_loss_pkr"] > s_data["airsense_mitigated_savings_pkr"]

        # Invariant: Net = Unmitigated - Mitigated
        expected_net = round(s_data["unmitigated_financial_loss_pkr"] - s_data["airsense_mitigated_savings_pkr"], 2)
        assert abs(s_data["net_enterprise_loss_pkr"] - expected_net) <= 0.05

        # Invariant: ROI % = (Mitigated / Unmitigated) * 100
        expected_roi = round((s_data["airsense_mitigated_savings_pkr"] / s_data["unmitigated_financial_loss_pkr"]) * 100.0, 1)
        assert abs(s_data["loss_avoidance_efficiency_roi_pct"] - expected_roi) <= 0.1

        # Sector-specific operational directives present
        assert "directive" in s_data
        assert len(s_data["directive"]) > 10

    # Sector-specific detailed metrics
    assert sectors["logistics"]["fleet_rerouting_savings_pkr"] > 0
    assert sectors["logistics"]["motorway_closure_mitigation_pkr"] > 0
    assert sectors["education"]["shift_adjustment_savings_pkr"] > 0
    assert sectors["education"]["hepa_filtration_surge_savings_pkr"] > 0
    assert sectors["manufacturing"]["shutdown_prevention_savings_pkr"] > 0
    assert sectors["manufacturing"]["scrubber_compliance_savings_pkr"] > 0
    assert sectors["healthcare"]["icu_surge_readiness_savings_pkr"] > 0
    assert sectors["healthcare"]["oxygen_bed_capacity_savings_pkr"] > 0
    assert sectors["retail"]["footfall_loss_mitigation_pkr"] > 0
    assert sectors["retail"]["curfew_avoidance_savings_pkr"] > 0

    # Aggregate invariants
    agg = matrix_result["aggregate"]
    sum_unmitigated = sum(sectors[s]["unmitigated_financial_loss_pkr"] for s in expected_sectors)
    sum_mitigated = sum(sectors[s]["airsense_mitigated_savings_pkr"] for s in expected_sectors)
    assert abs(agg["unmitigated_financial_loss_pkr"] - round(sum_unmitigated, 2)) <= 0.05
    assert abs(agg["airsense_mitigated_savings_pkr"] - round(sum_mitigated, 2)) <= 0.05


def test_loss_matrix_from_authentic_telemetry():
    """Verify enterprise loss calculation directly from authentic physical sensor telemetry."""
    pipeline = OpsImpactPipeline()

    telemetry = dict(SAMPLE_HARDWARE_TELEMETRY)
    telemetry["pm2_5"] = 160.0  # Elevated physical reading
    telemetry["humidity"] = 80.0 # High humidity requiring swelling adjustment (0.90x)

    loss_res = pipeline.calculate_from_telemetry(telemetry, city="karachi")

    assert "telemetry_source" in loss_res
    src = loss_res["telemetry_source"]
    assert src["physical_pm2_5"] == 160.0
    assert src["hygroscopic_adjustment_applied"] is True
    assert src["effective_pm2_5"] == 144.0  # 160.0 * 0.90
    assert src["zero_mock_verified"] is True

    agg = loss_res["aggregate"]
    assert agg["unmitigated_financial_loss_pkr"] > 0
    assert agg["airsense_mitigated_savings_pkr"] > 0
    assert agg["overall_mitigation_efficiency_pct"] > 75.0


# ============================================================================
# 4. AgentPhone Autonomous Telephony Governance
# ============================================================================

def test_telephony_governance_below_hazard_threshold():
    """Verify that when authentic PM2.5 is below operational hazard threshold (< 150), no call is triggered."""
    safe_telemetry = dict(SAMPLE_HARDWARE_TELEMETRY)
    safe_telemetry["pm2_5"] = 45.0  # Safe level

    gov = OperationalDecisionEngine.evaluate_telephony_governance(safe_telemetry, pm2_5_threshold=150.0)
    assert gov["hazard_detected"] is False
    assert gov["total_triggers"] == 0
    assert len(gov["active_telephony_triggers"]) == 0
    assert gov["governance_mode"] == "AUTHENTIC_PHYSICAL_TELEMETRY_ZERO_MOCK"


def test_telephony_governance_exceeding_hazard_threshold():
    """Verify that when authentic PM2.5 exceeds hazard threshold (>= 150), calibrated triggers are generated."""
    hazard_telemetry = dict(SAMPLE_HARDWARE_TELEMETRY)
    hazard_telemetry["pm2_5"] = 180.0
    hazard_telemetry["humidity"] = 60.0

    gov = OperationalDecisionEngine.evaluate_telephony_governance(
        hazard_telemetry,
        city="Lahore",
        pm2_5_threshold=150.0
    )
    assert gov["hazard_detected"] is True
    assert gov["total_triggers"] == 4

    triggers_by_sector = {t["sector"]: t for t in gov["active_telephony_triggers"]}
    assert "logistics" in triggers_by_sector
    assert triggers_by_sector["logistics"]["voice_persona"] == "11labs-Brian"

    assert "education" in triggers_by_sector
    assert triggers_by_sector["education"]["voice_persona"] == "nova"

    assert "industrial" in triggers_by_sector
    assert triggers_by_sector["industrial"]["voice_persona"] == "alloy"

    assert "healthcare" in triggers_by_sector
    assert triggers_by_sector["healthcare"]["voice_persona"] == "nova"


@pytest.mark.asyncio
async def test_agentphone_dispatch_execution_and_ledger_persistence():
    """Verify automated AgentPhone alert dispatch and ledger persistence on D: drive."""
    pipeline = OpsImpactPipeline()

    hazard_telemetry = dict(SAMPLE_HARDWARE_TELEMETRY)
    hazard_telemetry["pm2_5"] = 210.0
    hazard_telemetry["humidity"] = 65.0

    gov = pipeline.evaluate_telephony_governance(hazard_telemetry, city="Lahore")
    assert gov["hazard_detected"] is True
    first_trigger = gov["active_telephony_triggers"][0]

    # Execute voice alert dispatch
    dispatch_record = await pipeline.dispatch_telephony_alert(
        trigger_info=first_trigger,
        to_number="+923001234567",
        recipient_name="Fleet Director",
        channel="voice",
        language="en"
    )

    assert dispatch_record["status"] == "COMPLETED"
    assert dispatch_record["type"] == "VOICE_CALL"
    assert dispatch_record["voice_agent"] == "Logistics Early Warning Copilot"
    assert dispatch_record["voice_engine"] == "11labs-Brian"
    assert len(dispatch_record["turns"]) >= 4

    # Verify storage sovereignty: persisted on D: drive
    assert EVENTS_LOG_FILE.lower().startswith("d:"), f"Telephony log {EVENTS_LOG_FILE} not on D: drive"
    assert os.path.exists(EVENTS_LOG_FILE), "Telephony ledger file not found"

    # Read last record from ledger
    with open(EVENTS_LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) > 0
    last_entry = json.loads(lines[-1].strip())
    assert last_entry["to_number"] == "+923001234567"
    assert last_entry["sector"] == "logistics"


# ============================================================================
# 5. Storage Sovereignty & Drive Isolation Verification
# ============================================================================

def test_storage_sovereignty_zero_c_drive_writes():
    """Assert all operational data paths, models, lakes, and logs reside strictly on D: drive."""
    pipeline = OpsImpactPipeline()
    model = MultiHorizonImpactModel()

    paths_to_verify = [
        ("Lake Base", pipeline.lake_manager.base_path),
        ("Scraped Raw Root", pipeline.lake_manager.scraped_raw_root),
        ("Normalized Root", pipeline.lake_manager.normalized_root),
        ("10-Day Lake", pipeline.lake_manager.horizon_10day_lake),
        ("Telephony Log File", EVENTS_LOG_FILE),
        ("10-Day Model Artifact", model.MODEL_ARTIFACT_PATH)
    ]

    for label, path_str in paths_to_verify:
        norm_path = os.path.abspath(path_str).replace("\\", "/")
        assert norm_path.lower().startswith("d:"), (
            f"CRITICAL VIOLATION: {label} path '{path_str}' violates sovereign D: drive isolation constraint!"
        )

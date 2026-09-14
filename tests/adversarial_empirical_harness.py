"""Empirical Challenger Comprehensive Verification Harness.

Stress-tests decision_engine.py and sector_intelligence.py across:
1. Boundary values and transition edges
2. Division-by-zero protection under all null/zero vectors
3. Extreme weather conditions (0 wind, 150 m/s hurricane, 100% RH, -40C cold, 60C heat)
4. Extreme particulate matter ranges (0 to 100,000 ug/m3)
5. Invariant checking: Stagnation in [0, 100], Confidence in [65, 98], Healthcare vuln in [0, 100], HVAC damper in {10,20,50,80}, Filter life >= 12
6. 100,000 randomized Monte Carlo vectors
"""

import sys
import math
import random
from typing import Dict, Any, List

from services.decision_intelligence.decision_engine import OperationalDecisionEngine
from services.decision_intelligence.sector_intelligence import SectorIntelligenceEngine


def run_all_empirical_tests() -> Dict[str, Any]:
    results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "failures": [],
        "sections": {}
    }

    def record_test(section: str, test_name: str, passed: bool, details: str = ""):
        results["total_tests"] += 1
        if section not in results["sections"]:
            results["sections"][section] = {"total": 0, "passed": 0, "failed": 0}
        results["sections"][section]["total"] += 1

        if passed:
            results["passed_tests"] += 1
            results["sections"][section]["passed"] += 1
        else:
            results["failed_tests"] += 1
            results["sections"][section]["failed"] += 1
            results["failures"].append({"section": section, "test": test_name, "details": details})

    # =========================================================================
    # SECTION 1: DIVISION-BY-ZERO PROTECTIONS
    # =========================================================================
    sec = "1. Division-by-Zero Protections"

    # Test 1.1: Decision Engine with current_pm2_5 = 0.0
    try:
        dec = OperationalDecisionEngine.evaluate_decisions(
            campus_code="TEST_ZERO", current_pm2_5=0.0, current_pm10=0.0,
            forecast_1h_pm2_5=0.0, forecast_6h_pm2_5=0.0, temperature_c=0.0,
            humidity_pct=0.0, wind_speed_m_s=0.0, wind_direction_deg=0.0, pressure_hpa=0.0
        )
        passed = (dec["confidence_pct"] == 98.0 and dec["stagnation_index"] == 70.0 and dec["risk_tier"] == "OPTIMAL_NORMAL")
        record_test(sec, "DecisionEngine All-Zero Telemetry", passed, f"Result: {dec}")
    except Exception as e:
        record_test(sec, "DecisionEngine All-Zero Telemetry", False, f"Exception: {e}")

    # Test 1.2: Industrial Coarse Ratio with pm2_5 = 0.0
    try:
        ind = SectorIntelligenceEngine.get_industrial_intelligence(pm2_5=0.0, pm10=100.0, wind_speed=0.0)
        passed = (ind["status"] == "DUST_SUPPRESSION_TRIGGER" and ind["kpis"][0]["value"] == "100 ug/m3")
        record_test(sec, "Industrial Zero PM2.5 Protection", passed, f"Result: {ind}")
    except Exception as e:
        record_test(sec, "Industrial Zero PM2.5 Protection", False, f"Exception: {e}")

    # Test 1.3: Industrial All-Zero
    try:
        ind0 = SectorIntelligenceEngine.get_industrial_intelligence(pm2_5=0.0, pm10=0.0, wind_speed=0.0)
        passed = (ind0["status"] == "COMPLIANT" and ind0["status_color"] == "#00E599")
        record_test(sec, "Industrial All-Zero", passed, f"Result: {ind0}")
    except Exception as e:
        record_test(sec, "Industrial All-Zero", False, f"Exception: {e}")

    # Test 1.4: Healthcare Zero Telemetry
    try:
        health0 = SectorIntelligenceEngine.get_healthcare_intelligence(pm2_5=0.0, forecast_1h=0.0, humidity_pct=0.0)
        passed = (health0["vulnerability_index"] == 0 and health0["status"] == "LOW_RISK")
        record_test(sec, "Healthcare Zero Telemetry", passed, f"Result: {health0}")
    except Exception as e:
        record_test(sec, "Healthcare Zero Telemetry", False, f"Exception: {e}")

    # Test 1.5: HVAC Zero Telemetry
    try:
        hvac0 = SectorIntelligenceEngine.get_hvac_intelligence(pm2_5=0.0, forecast_1h=0.0, temp_c=0.0, humidity_pct=0.0)
        passed = (hvac0["damper_position_pct"] == 80 and hvac0["filter_life_remaining_days"] == 90)
        record_test(sec, "HVAC Zero Telemetry", passed, f"Result: {hvac0}")
    except Exception as e:
        record_test(sec, "HVAC Zero Telemetry", False, f"Exception: {e}")

    # =========================================================================
    # SECTION 2: BOUNDARY VALUES & TRANSITION EDGES
    # =========================================================================
    sec = "2. Boundary Values & Transition Edges"

    # Test 2.1: Risk Tier 35.0 Boundary (MODERATE_ADVISORY vs OPTIMAL_NORMAL)
    d_34_9 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 34.9, 50.0, 34.9, 34.9, 25.0, 50.0, 3.0, 0.0, 1013.0)
    d_35_0 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 35.0, 50.0, 35.0, 35.0, 25.0, 50.0, 3.0, 0.0, 1013.0)
    record_test(sec, "Risk Tier 35.0 Threshold (34.9 -> OPTIMAL, 35.0 -> MODERATE)",
                d_34_9["risk_tier"] == "OPTIMAL_NORMAL" and d_35_0["risk_tier"] == "MODERATE_ADVISORY")

    # Test 2.2: Risk Tier 75.0 Boundary (HIGH_ALERT vs MODERATE_ADVISORY)
    d_74_9 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 74.9, 100.0, 74.9, 74.9, 25.0, 50.0, 3.0, 0.0, 1013.0)
    d_75_0 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 75.0, 100.0, 75.0, 75.0, 25.0, 50.0, 3.0, 0.0, 1013.0)
    record_test(sec, "Risk Tier 75.0 Threshold (74.9 -> MODERATE, 75.0 -> HIGH)",
                d_74_9["risk_tier"] == "MODERATE_ADVISORY" and d_75_0["risk_tier"] == "HIGH_ALERT")

    # Test 2.3: Risk Tier 150.0 Boundary (CRITICAL_HAZARD vs HIGH_ALERT in isolation)
    d_149_9 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 110.0, 200.0, 149.9, 100.0, 25.0, 50.0, 3.0, 0.0, 1013.0)
    d_150_0 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 110.0, 200.0, 150.0, 100.0, 25.0, 50.0, 3.0, 0.0, 1013.0)
    record_test(sec, "Risk Tier 150.0 Threshold (149.9 -> HIGH, 150.0 -> CRITICAL)",
                d_149_9["risk_tier"] == "HIGH_ALERT" and d_150_0["risk_tier"] == "CRITICAL_HAZARD")

    # Test 2.4: Critical Hazard Dual Condition (current >= 120 and forecast_1h >= 140)
    d_crit_dual_pass = OperationalDecisionEngine.evaluate_decisions("B_TEST", 120.0, 150.0, 140.0, 100.0, 25.0, 50.0, 3.0, 0.0, 1013.0)
    d_crit_dual_fail1 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 119.9, 150.0, 140.0, 100.0, 25.0, 50.0, 3.0, 0.0, 1013.0)
    d_crit_dual_fail2 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 120.0, 150.0, 139.9, 100.0, 25.0, 50.0, 3.0, 0.0, 1013.0)
    record_test(sec, "Critical Hazard Dual Condition Logic",
                d_crit_dual_pass["risk_tier"] == "CRITICAL_HAZARD" and
                d_crit_dual_fail1["risk_tier"] == "HIGH_ALERT" and
                d_crit_dual_fail2["risk_tier"] == "HIGH_ALERT")

    # Test 2.5: Humidity Swelling 75.0% Threshold
    d_rh_75 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 80.0, 100.0, 50.0, 50.0, 25.0, 75.0, 3.0, 0.0, 1013.0)
    d_rh_75_01 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 80.0, 100.0, 50.0, 50.0, 25.0, 75.01, 3.0, 0.0, 1013.0)
    record_test(sec, "Humidity Swelling Threshold at 75.0% (80 -> HIGH vs 72 -> MODERATE)",
                d_rh_75["risk_tier"] == "HIGH_ALERT" and d_rh_75_01["risk_tier"] == "MODERATE_ADVISORY")

    # Test 2.6: Temperature Inversion 18.0C Threshold (+20 stagnation bonus)
    d_temp_18_0 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 20.0, 30.0, 20.0, 20.0, 18.0, 50.0, 5.0, 0.0, 1013.0)
    d_temp_17_99 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 20.0, 30.0, 20.0, 20.0, 17.99, 50.0, 5.0, 0.0, 1013.0)
    record_test(sec, "Temperature 18.0C Stagnation Inversion Bonus",
                d_temp_18_0["stagnation_index"] == 45.0 and d_temp_17_99["stagnation_index"] == 65.0)

    # Test 2.7: Dispersion Class Score 40.0 Boundary
    # wind=6.0, hum=50, temp=20 -> (10-6)*5 + 50*0.4 = 20 + 20 = 40.0
    d_stag_40_0 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 20.0, 30.0, 20.0, 20.0, 20.0, 50.0, 6.0, 0.0, 1013.0)
    # wind=5.9, hum=50, temp=20 -> (10-5.9)*5 + 50*0.4 = 20.5 + 20 = 40.5
    d_stag_40_5 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 20.0, 30.0, 20.0, 20.0, 20.0, 50.0, 5.9, 0.0, 1013.0)
    record_test(sec, "Dispersion Class 40.0 Boundary (40.0 -> EXCELLENT, 40.5 -> MODERATE)",
                d_stag_40_0["dispersion_class"] == "EXCELLENT_VENTILATION" and
                d_stag_40_5["dispersion_class"] == "MODERATE_DISPERSION")

    # Test 2.8: Dispersion Class Score 70.0 Boundary
    # wind=0.0, hum=50, temp=20 -> 50 + 20 = 70.0
    d_stag_70_0 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 20.0, 30.0, 20.0, 20.0, 20.0, 50.0, 0.0, 0.0, 1013.0)
    # wind=0.0, hum=51, temp=20 -> 50 + 20.4 = 70.4
    d_stag_70_4 = OperationalDecisionEngine.evaluate_decisions("B_TEST", 20.0, 30.0, 20.0, 20.0, 20.0, 51.0, 0.0, 0.0, 1013.0)
    record_test(sec, "Dispersion Class 70.0 Boundary (70.0 -> MODERATE, 70.4 -> POOR)",
                d_stag_70_0["dispersion_class"] == "MODERATE_DISPERSION" and
                d_stag_70_4["dispersion_class"] == "POOR_TRAPPED_INVERSION")

    # Test 2.9: Education Recess Safety Boundaries
    edu_75 = SectorIntelligenceEngine.get_education_intelligence(75.0, 75.0)
    edu_74_9 = SectorIntelligenceEngine.get_education_intelligence(74.9, 74.9)
    edu_35 = SectorIntelligenceEngine.get_education_intelligence(35.0, 35.0)
    edu_34_9 = SectorIntelligenceEngine.get_education_intelligence(34.9, 34.9)
    record_test(sec, "Education Recess Safety Boundaries (75, 35)",
                edu_75["recess_safety_rating"] == "PROHIBITED" and
                edu_74_9["recess_safety_rating"] == "RESTRICTED_LOW_IMPACT" and
                edu_35["recess_safety_rating"] == "RESTRICTED_LOW_IMPACT" and
                edu_34_9["recess_safety_rating"] == "FULLY_SAFE")

    # Test 2.10: HVAC Damper Modulation Boundaries (100, 50, 25)
    hvac_101 = SectorIntelligenceEngine.get_hvac_intelligence(101.0, 0.0, 20.0, 50.0)
    hvac_100 = SectorIntelligenceEngine.get_hvac_intelligence(100.0, 0.0, 20.0, 50.0)
    hvac_51 = SectorIntelligenceEngine.get_hvac_intelligence(51.0, 0.0, 20.0, 50.0)
    hvac_50 = SectorIntelligenceEngine.get_hvac_intelligence(50.0, 0.0, 20.0, 50.0)
    hvac_26 = SectorIntelligenceEngine.get_hvac_intelligence(26.0, 0.0, 20.0, 50.0)
    hvac_25 = SectorIntelligenceEngine.get_hvac_intelligence(25.0, 0.0, 20.0, 50.0)
    record_test(sec, "HVAC Damper Modulation (10% >100, 20% >50, 50% >25, 80% <=25)",
                hvac_101["damper_position_pct"] == 10 and
                hvac_100["damper_position_pct"] == 20 and
                hvac_51["damper_position_pct"] == 20 and
                hvac_50["damper_position_pct"] == 50 and
                hvac_26["damper_position_pct"] == 50 and
                hvac_25["damper_position_pct"] == 80)

    # Test 2.11: Healthcare Vulnerability Index Thresholds (70, 40)
    h_crit = SectorIntelligenceEngine.get_healthcare_intelligence(130.0, 130.0, 50.0)
    h_elev = SectorIntelligenceEngine.get_healthcare_intelligence(60.0, 60.0, 40.0)
    h_low = SectorIntelligenceEngine.get_healthcare_intelligence(30.0, 30.0, 40.0)
    record_test(sec, "Healthcare Vulnerability Index Thresholds (>=70, >=40, <40)",
                h_crit["status"] == "CRITICAL_SURGE" and
                h_elev["status"] == "ELEVATED_RISK" and
                h_low["status"] == "LOW_RISK")

    # =========================================================================
    # SECTION 3: EXTREME WEATHER CONDITIONS & ADVERSARIAL TELEMETRY
    # =========================================================================
    sec = "3. Extreme Weather Conditions"

    # Test 3.1: Zero Wind Dead Calm Maximum Stagnation Clamp
    dec_calm = OperationalDecisionEngine.evaluate_decisions("W_TEST", 50.0, 80.0, 50.0, 50.0, 5.0, 100.0, 0.0, 0.0, 1030.0)
    record_test(sec, "Zero Wind (0 m/s) + 100% RH + Sub-18C -> Stagnation Clamped to 100.0",
                dec_calm["stagnation_index"] == 100.0 and dec_calm["dispersion_class"] == "POOR_TRAPPED_INVERSION")

    # Test 3.2: Hurricane Force Winds Maximum Dispersion Clamp
    dec_hurr = OperationalDecisionEngine.evaluate_decisions("W_TEST", 20.0, 30.0, 20.0, 20.0, 40.0, 0.0, 120.0, 180.0, 920.0)
    record_test(sec, "Hurricane Force Wind (120 m/s) + 0% RH -> Stagnation Clamped to 0.0",
                dec_hurr["stagnation_index"] == 0.0 and dec_hurr["dispersion_class"] == "EXCELLENT_VENTILATION")

    # Test 3.3: Extreme Sub-Zero Arctic Cold (-40C)
    dec_arctic = OperationalDecisionEngine.evaluate_decisions("W_TEST", 30.0, 40.0, 30.0, 30.0, -40.0, 80.0, 2.0, 0.0, 1040.0)
    record_test(sec, "Extreme Cold (-40C) Telemetry Handling",
                dec_arctic["stagnation_index"] == 92.0 and dec_arctic["dispersion_class"] == "POOR_TRAPPED_INVERSION")

    # Test 3.4: Extreme Desert Heat (+60C)
    dec_heat = OperationalDecisionEngine.evaluate_decisions("W_TEST", 30.0, 40.0, 30.0, 30.0, 60.0, 10.0, 8.0, 0.0, 990.0)
    record_test(sec, "Extreme Heat (+60C) Telemetry Handling",
                dec_heat["stagnation_index"] == 14.0 and dec_heat["dispersion_class"] == "EXCELLENT_VENTILATION")

    # Test 3.5: Apocalyptic Particulate Density (50,000 ug/m3)
    dec_apoc = OperationalDecisionEngine.evaluate_decisions("W_TEST", 50000.0, 80000.0, 60000.0, 70000.0, 15.0, 90.0, 0.1, 0.0, 1000.0)
    record_test(sec, "Apocalyptic PM2.5 (50,000 ug/m3) Stability & Clamps",
                dec_apoc["risk_tier"] == "CRITICAL_HAZARD" and
                65.0 <= dec_apoc["confidence_pct"] <= 98.0 and
                dec_apoc["stagnation_index"] == 100.0)

    # Test 3.6: All Sectors under Apocalyptic Load (50,000 ug/m3)
    sec_apoc = SectorIntelligenceEngine.get_all_sectors_summary(50000.0, 80000.0, 15.0, 90.0, 0.1, 60000.0)
    hvac_apoc = next(s for s in sec_apoc if s["sector_id"] == "hvac")
    health_apoc = next(s for s in sec_apoc if s["sector_id"] == "healthcare")
    edu_apoc = next(s for s in sec_apoc if s["sector_id"] == "education")
    record_test(sec, "All Sectors Apocalyptic Load Resilience",
                len(sec_apoc) == 6 and
                hvac_apoc["damper_position_pct"] == 10 and
                hvac_apoc["filter_life_remaining_days"] == 12 and
                health_apoc["vulnerability_index"] == 100 and
                edu_apoc["recess_safety_rating"] == "PROHIBITED")

    # =========================================================================
    # SECTION 4: CONFIDENCE SCORE & STAGNATION CLAMP INVARIANTS
    # =========================================================================
    sec = "4. Clamp Invariants"

    # Test 4.1: Confidence Score Upper Bound (98.0%)
    c_upper = OperationalDecisionEngine.evaluate_decisions("C_TEST", 100.0, 150.0, 100.0, 100.0, 20.0, 50.0, 3.0, 0.0, 1013.0)
    record_test(sec, "Confidence Score Upper Bound Exact 98.0%", c_upper["confidence_pct"] == 98.0)

    # Test 4.2: Confidence Score Lower Bound (65.0%)
    c_lower = OperationalDecisionEngine.evaluate_decisions("C_TEST", 10.0, 15.0, 10000.0, 10000.0, 20.0, 50.0, 3.0, 0.0, 1013.0)
    record_test(sec, "Confidence Score Lower Bound Exact 65.0%", c_lower["confidence_pct"] == 65.0)

    # Test 4.3: HVAC Filter Useful Life Lower Bound (12 Days)
    hvac_filt = SectorIntelligenceEngine.get_hvac_intelligence(1000.0, 1000.0, 25.0, 50.0)
    record_test(sec, "HVAC HEPA Filter Useful Life Lower Bound 12 Days", hvac_filt["filter_life_remaining_days"] == 12)

    # Test 4.4: Healthcare Vulnerability Index Upper Bound (100)
    health_vuln = SectorIntelligenceEngine.get_healthcare_intelligence(1000.0, 1000.0, 100.0)
    record_test(sec, "Healthcare Vulnerability Index Upper Bound 100", health_vuln["vulnerability_index"] == 100)

    # =========================================================================
    # SECTION 5: MASSIVE RANDOMIZED MONTE CARLO FUZZING (100,000 ITERATIONS)
    # =========================================================================
    sec = "5. Randomized Monte Carlo Invariant Fuzzing (100,000 runs)"
    random.seed(1337)
    fuzz_passed = True
    fuzz_error = ""

    valid_tiers = {"OPTIMAL_NORMAL", "MODERATE_ADVISORY", "HIGH_ALERT", "CRITICAL_HAZARD"}
    valid_disp_classes = {"POOR_TRAPPED_INVERSION", "MODERATE_DISPERSION", "EXCELLENT_VENTILATION"}
    valid_recess = {"PROHIBITED", "RESTRICTED_LOW_IMPACT", "FULLY_SAFE"}
    valid_dampers = {10, 20, 50, 80}

    for i in range(100000):
        try:
            pm2_5 = max(0.0, random.uniform(-10.0, 2000.0))
            pm10 = max(0.0, random.uniform(-10.0, 5000.0))
            f_1h = max(0.0, random.uniform(-10.0, 2000.0))
            f_6h = max(0.0, random.uniform(-10.0, 2000.0))
            temp = random.uniform(-50.0, 70.0)
            hum = max(0.0, min(100.0, random.uniform(-20.0, 120.0)))
            wind_spd = max(0.0, random.uniform(-10.0, 100.0))
            wind_dir = random.uniform(0.0, 360.0)
            press = random.uniform(800.0, 1100.0)
            rain = random.choice([True, False])

            # Decision Engine Check
            d = OperationalDecisionEngine.evaluate_decisions(
                f"FZ_{i}", pm2_5, pm10, f_1h, f_6h, temp, hum, wind_spd, wind_dir, press, rain
            )
            assert d["risk_tier"] in valid_tiers
            assert 65.0 <= d["confidence_pct"] <= 98.0
            assert 0.0 <= d["stagnation_index"] <= 100.0
            assert d["dispersion_class"] in valid_disp_classes

            # Sectors Check
            secs = SectorIntelligenceEngine.get_all_sectors_summary(pm2_5, pm10, temp, hum, wind_spd, f_1h)
            assert len(secs) == 6

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

        except Exception as ex:
            fuzz_passed = False
            fuzz_error = f"Iteration {i} failed: {ex} with inputs: pm25={pm2_5}, pm10={pm10}, f1={f_1h}, hum={hum}, wind={wind_spd}, temp={temp}"
            break

    record_test(sec, "100,000 Property-Based Fuzzing Iterations", fuzz_passed, fuzz_error)

    return results


if __name__ == "__main__":
    res = run_all_empirical_tests()
    print("=" * 70)
    print("EMPIRICAL CHALLENGER STRESS TEST RESULTS")
    print("=" * 70)
    print(f"Total Tests Executed: {res['total_tests']}")
    print(f"Passed: {res['passed_tests']}")
    print(f"Failed: {res['failed_tests']}")
    print("-" * 70)
    for s_name, s_data in res["sections"].items():
        status_str = "PASS" if s_data["failed"] == 0 else "FAIL"
        print(f"[{status_str}] {s_name}: {s_data['passed']}/{s_data['total']} passed")
    print("=" * 70)
    if res["failures"]:
        print("FAILURES:")
        for f in res["failures"]:
            print(f"  - [{f['section']}] {f['test']}: {f['details']}")
        sys.exit(1)
    else:
        print("ALL EMPIRICAL TESTS AND INVARIANTS PASSED PERFECTLY!")
        sys.exit(0)

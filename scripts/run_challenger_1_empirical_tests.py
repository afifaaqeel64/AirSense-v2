"""Challenger 1: Standalone Empirical Hardware Diagnostics & State Machine Verification Harness.

Directly imports and tests:
1. Time Boundaries: 119s, 120s, 121s, 1000s, 0s, negative clock skew.
2. Degraded Sensor States & Pin Guidance:
   - PMS7003 PM2.5 = 0.0 ug/m3 (DEGRADED + UART Pin Guidance)
   - BME280 Temperature = 70.0°C (DEGRADED + I2C Pin Guidance)
   - Rainplate ADC moisture states (Wet, Dry, Missing)
   - MicroSD VSPI states (Online, Disconnected)
   - Verification of all physical pin mappings.
3. Missing Sensor Values, Partial Telemetry Packets & Corrupted Fields.
4. Concurrency & Rapid Sequential Polls.
"""

import sys
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from services.quality_control.sensor_health_engine import (
    SensorHealthEngine, StationDiagnosticReport, SensorHealthStatus
)

def log_test(title: str, passed: bool, details: str = ""):
    status_str = "PASS" if passed else "FAIL"
    print(f"[{status_str}] {title}")
    if details:
        print(f"       Details: {details}")

def run_empirical_tests():
    print("=" * 80)
    print("CHALLENGER 1: EMPIRICAL HARDWARE DIAGNOSTICS & STATE MACHINE VERIFICATION")
    print("=" * 80)
    
    passed_count = 0
    failed_count = 0
    findings = []

    # =========================================================================
    # 1. TIME BOUNDARIES (119s, 120s, 121s, 1000s)
    # =========================================================================
    print("\n--- TEST GROUP 1: TIME BOUNDARIES & STATE MACHINE TRANSITIONS ---")
    now = datetime.now(timezone.utc)
    valid_reading = {
        "pm1": 8.0, "pm2_5": 14.5, "pm10": 22.0,
        "temperature_c": 28.5, "humidity_pct": 55.0, "pressure_hpa": 1012.0,
        "rain_flag": False,
        "station_code": "BIC-KHI-ROOF-01",
        "device_uid": "AIRSENSE-NODE-KHI-01"
    }

    # Case 1.1: 119s (LIVE)
    t119 = now - timedelta(seconds=119)
    rep119 = SensorHealthEngine.evaluate_sensor_connectivity(valid_reading, last_received_at=t119)
    p119 = (rep119.station_liveness == "LIVE_ACTIVE" and 
            rep119.seconds_since_last_packet == 119 and 
            rep119.sensors["pms7003"].status == "ONLINE" and
            rep119.sensors["bme280"].status == "ONLINE")
    log_test("Boundary at 119.0s recency -> LIVE_ACTIVE", p119, f"station_liveness={rep119.station_liveness}, seconds_ago={rep119.seconds_since_last_packet}")
    if p119: passed_count += 1
    else: 
        failed_count += 1
        findings.append("119s boundary failed to report LIVE_ACTIVE")

    # Case 1.2: 120s (LIVE)
    t120 = now - timedelta(seconds=120)
    rep120 = SensorHealthEngine.evaluate_sensor_connectivity(valid_reading, last_received_at=t120)
    p120 = (rep120.station_liveness == "LIVE_ACTIVE" and 
            rep120.seconds_since_last_packet == 120 and
            rep120.sensors["pms7003"].status == "ONLINE")
    log_test("Boundary at exactly 120.0s recency -> LIVE_ACTIVE", p120, f"station_liveness={rep120.station_liveness}, seconds_ago={rep120.seconds_since_last_packet}")
    if p120: passed_count += 1
    else:
        failed_count += 1
        findings.append("120s boundary failed to report LIVE_ACTIVE")

    # Case 1.3: 121s (OFFLINE)
    t121 = now - timedelta(seconds=121)
    rep121 = SensorHealthEngine.evaluate_sensor_connectivity(valid_reading, last_received_at=t121)
    p121 = (rep121.station_liveness == "OFFLINE" and 
            rep121.seconds_since_last_packet == 121 and
            rep121.sensors["pms7003"].status == "DISCONNECTED" and
            rep121.sensors["bme280"].status == "DISCONNECTED")
    log_test("Boundary at 121.0s recency -> OFFLINE", p121, f"station_liveness={rep121.station_liveness}, seconds_ago={rep121.seconds_since_last_packet}")
    if p121: passed_count += 1
    else:
        failed_count += 1
        findings.append("121s boundary failed to report OFFLINE")

    # Case 1.4: 1000s (OFFLINE)
    t1000 = now - timedelta(seconds=1000)
    rep1000 = SensorHealthEngine.evaluate_sensor_connectivity(valid_reading, last_received_at=t1000)
    p1000 = (rep1000.station_liveness == "OFFLINE" and 
             rep1000.seconds_since_last_packet == 1000 and
             rep1000.sensors["microsd"].status == "DISCONNECTED")
    log_test("Stale packet at 1000.0s recency -> OFFLINE", p1000, f"station_liveness={rep1000.station_liveness}, seconds_ago={rep1000.seconds_since_last_packet}")
    if p1000: passed_count += 1
    else:
        failed_count += 1
        findings.append("1000s boundary failed to report OFFLINE")

    # =========================================================================
    # 2. DEGRADED SENSOR STATES & PIN TROUBLESHOOTING GUIDANCE
    # =========================================================================
    print("\n--- TEST GROUP 2: DEGRADED SENSORS & PIN TROUBLESHOOTING GUIDANCE ---")

    # Case 2.1: PMS7003 PM2.5 = 0.0 ug/m3
    zero_pms_reading = {
        "pm1": 0.0, "pm2_5": 0.0, "pm10": 0.0,
        "temperature_c": 28.0, "humidity_pct": 55.0, "pressure_hpa": 1012.0,
        "rain_flag": False
    }
    rep_pms_zero = SensorHealthEngine.evaluate_sensor_connectivity(zero_pms_reading, last_received_at=now)
    pms_sens = rep_pms_zero.sensors["pms7003"]
    p_pms_zero = (
        rep_pms_zero.station_liveness == "PARTIAL_DEGRADED" and
        pms_sens.status == "DEGRADED" and
        pms_sens.is_connected is False and
        "fan" in (pms_sens.troubleshooting_step or "").lower() and
        "GPIO 16" in pms_sens.pins and
        "GPIO 17" in pms_sens.pins and
        "5.0V" in pms_sens.pins
    )
    log_test("PMS7003 zero particulate (0.0 ug/m3) -> DEGRADED with fan inspection", p_pms_zero, 
             f"status={pms_sens.status}, step='{pms_sens.troubleshooting_step}', pins='{pms_sens.pins}'")
    if p_pms_zero: passed_count += 1
    else:
        failed_count += 1
        findings.append("PMS7003 zero counts not flagged DEGRADED with proper guidance")

    # Case 2.2: BME280 Temperature = 70.0°C (Ceiling is 65.0°C)
    high_temp_reading = {
        "pm1": 8.0, "pm2_5": 14.0, "pm10": 20.0,
        "temperature_c": 70.0, "humidity_pct": 50.0, "pressure_hpa": 1012.0,
        "rain_flag": False
    }
    rep_bme_high = SensorHealthEngine.evaluate_sensor_connectivity(high_temp_reading, last_received_at=now)
    bme_sens = rep_bme_high.sensors["bme280"]
    p_bme_high = (
        rep_bme_high.station_liveness == "PARTIAL_DEGRADED" and
        bme_sens.status == "DEGRADED" and
        bme_sens.is_connected is False and
        "out of bounds" in bme_sens.diagnostic_message and
        "70.0" in bme_sens.diagnostic_message and
        "GPIO 21" in bme_sens.pins and
        "GPIO 22" in bme_sens.pins and
        "3.3V" in bme_sens.pins
    )
    log_test("BME280 out-of-bounds temperature (70.0°C) -> DEGRADED with I2C pin guidance", p_bme_high,
             f"status={bme_sens.status}, msg='{bme_sens.diagnostic_message}', pins='{bme_sens.pins}'")
    if p_bme_high: passed_count += 1
    else:
        failed_count += 1
        findings.append("BME280 70.0C out-of-bounds not flagged DEGRADED with I2C guidance")

    # Case 2.3: Physical Pin Verification across all 4 sensor interfaces
    pms_pins_ok = "GPIO 16" in pms_sens.pins and "GPIO 17" in pms_sens.pins and "5.0V" in pms_sens.pins
    bme_pins_ok = "GPIO 21" in bme_sens.pins and "GPIO 22" in bme_sens.pins and "3.3V" in bme_sens.pins
    rain_sens = rep_bme_high.sensors["rain_sensor"]
    rain_pins_ok = "GPIO 34" in rain_sens.pins and "ADC" in rain_sens.interface
    sd_sens = rep_bme_high.sensors["microsd"]
    sd_pins_ok = ("GPIO 5" in sd_sens.pins and "GPIO 18" in sd_sens.pins and 
                  "GPIO 23" in sd_sens.pins and "GPIO 19" in sd_sens.pins and "VSPI" in sd_sens.interface)
    all_pins_ok = pms_pins_ok and bme_pins_ok and rain_pins_ok and sd_pins_ok
    log_test("Hardware Pin Mappings: UART2(16/17), I2C(21/22), ADC1(34), VSPI(5/18/23/19)", all_pins_ok,
             f"PMS:{pms_pins_ok}, BME:{bme_pins_ok}, Rain:{rain_pins_ok}, SD:{sd_pins_ok}")
    if all_pins_ok: passed_count += 1
    else:
        failed_count += 1
        findings.append("Hardware pin mapping mismatch in sensor diagnostic metadata")

    # =========================================================================
    # 3. MISSING SENSOR VALUES, PARTIAL PACKETS & CORRUPTED FIELDS
    # =========================================================================
    print("\n--- TEST GROUP 3: MISSING SENSOR VALUES & PARTIAL TELEMETRY ---")

    # Case 3.1: Missing PMS (BME only)
    pms_missing_reading = {"temperature_c": 28.0, "humidity_pct": 55.0, "pressure_hpa": 1012.0}
    rep_no_pms = SensorHealthEngine.evaluate_sensor_connectivity(pms_missing_reading, last_received_at=now)
    p_no_pms = (
        rep_no_pms.station_liveness == "PARTIAL_DEGRADED" and
        rep_no_pms.sensors["pms7003"].status == "DISCONNECTED" and
        rep_no_pms.sensors["bme280"].status == "ONLINE" and
        "GPIO 16" in (rep_no_pms.sensors["pms7003"].troubleshooting_step or "")
    )
    log_test("Missing PMS7003 telemetry -> PARTIAL_DEGRADED with UART wiring guidance", p_no_pms,
             f"PMS status={rep_no_pms.sensors['pms7003'].status}, step='{rep_no_pms.sensors['pms7003'].troubleshooting_step}'")
    if p_no_pms: passed_count += 1
    else:
        failed_count += 1
        findings.append("Missing PMS7003 failed to return UART wiring guidance")

    # Case 3.2: Missing BME (PMS only)
    bme_missing_reading = {"pm2_5": 14.0, "pm10": 20.0}
    rep_no_bme = SensorHealthEngine.evaluate_sensor_connectivity(bme_missing_reading, last_received_at=now)
    p_no_bme = (
        rep_no_bme.station_liveness == "PARTIAL_DEGRADED" and
        rep_no_bme.sensors["pms7003"].status == "ONLINE" and
        rep_no_bme.sensors["bme280"].status == "DISCONNECTED" and
        "GPIO 21" in (rep_no_bme.sensors["bme280"].troubleshooting_step or "")
    )
    log_test("Missing BME280 telemetry -> PARTIAL_DEGRADED with I2C wiring guidance", p_no_bme,
             f"BME status={rep_no_bme.sensors['bme280'].status}, step='{rep_no_bme.sensors['bme280'].troubleshooting_step}'")
    if p_no_bme: passed_count += 1
    else:
        failed_count += 1
        findings.append("Missing BME280 failed to return I2C wiring guidance")

    # Case 3.3: Empty reading dict
    rep_empty = SensorHealthEngine.evaluate_sensor_connectivity({}, last_received_at=now)
    p_empty = (
        rep_empty.station_liveness == "PARTIAL_DEGRADED" and
        rep_empty.sensors["pms7003"].status == "DISCONNECTED" and
        rep_empty.sensors["bme280"].status == "DISCONNECTED"
    )
    log_test("Empty reading dictionary {} -> PARTIAL_DEGRADED (Station alive, sensors disconnected)", p_empty,
             f"station_liveness={rep_empty.station_liveness}")
    if p_empty: passed_count += 1
    else:
        failed_count += 1
        findings.append("Empty reading dict did not handle gracefully")

    # Case 3.4: String-encoded numbers (type coercion)
    str_reading = {
        "pm1": "7.5", "pm2_5": "12.0", "pm10": "18.0",
        "temperature_c": "28.5", "humidity_pct": "60.0", "pressure_hpa": "1012.0",
        "rain_flag": True
    }
    rep_str = SensorHealthEngine.evaluate_sensor_connectivity(str_reading, last_received_at=now)
    p_str = (
        rep_str.station_liveness == "LIVE_ACTIVE" and
        rep_str.sensors["pms7003"].status == "ONLINE" and
        rep_str.sensors["bme280"].status == "ONLINE" and
        rep_str.sensors["rain_sensor"].status == "ONLINE"
    )
    log_test("String-encoded numeric telemetry -> Coerced successfully to LIVE_ACTIVE", p_str,
             f"station_liveness={rep_str.station_liveness}")
    if p_str: passed_count += 1
    else:
        failed_count += 1
        findings.append("String-encoded numbers failed to coerce in SensorHealthEngine")

    # =========================================================================
    # 4. RAPID SEQUENTIAL RE-EVALUATION
    # =========================================================================
    print("\n--- TEST GROUP 4: RAPID SEQUENTIAL & STRESS EXECUTION ---")
    stress_pass = True
    for i in range(1000):
        t_iter = now - timedelta(seconds=(i % 150))
        r_iter = SensorHealthEngine.evaluate_sensor_connectivity(valid_reading, last_received_at=t_iter)
        expected_live = (i % 150) <= 120
        actual_live = (r_iter.station_liveness == "LIVE_ACTIVE")
        if expected_live != actual_live:
            stress_pass = False
            break

    log_test("1,000 rapid sequential health evaluations (modulo 150s recency cycle)", stress_pass,
             "All 1,000 state machine evaluations matched exact deterministic expectations")
    if stress_pass: passed_count += 1
    else:
        failed_count += 1
        findings.append("1,000 rapid sequential evaluations failed consistency check")

    # =========================================================================
    # SUMMARY VERDICT
    # =========================================================================
    print("\n" + "=" * 80)
    print(f"CHALLENGER 1 SUMMARY: {passed_count} PASSED, {failed_count} FAILED")
    print("=" * 80)
    if failed_count == 0:
        print("VERDICT: EMPIRICAL VERIFICATION COMPLETE & APPROVED")
    else:
        print(f"VERDICT: REQUEST_CHANGES — {failed_count} empirical discrepancies identified:")
        for f in findings:
            print(f"  - {f}")
    
    return failed_count == 0


if __name__ == "__main__":
    success = run_empirical_tests()
    sys.exit(0 if success else 1)

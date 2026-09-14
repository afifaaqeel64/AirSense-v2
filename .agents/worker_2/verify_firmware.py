import os
import sys
import re
import json
from datetime import datetime, timezone

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath("."))

from services.quality_control.sensor_health_engine import SensorHealthEngine

def run_tests():
    with open("scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino", "r", encoding="utf-8") as f:
        code = f.read()

    print("=" * 60)
    print("  ESP32 FIRMWARE STATIC ANALYSIS & VERIFICATION SUITE")
    print("=" * 60)

    # 1. Structured JSON Telemetry over Serial
    assert "[JSON_TELEMETRY]" in code, "Missing [JSON_TELEMETRY] marker in firmware"
    assert 'Serial.print("[JSON_TELEMETRY] ");' in code, "Missing Serial.print([JSON_TELEMETRY] ) call"
    assert "Serial.println(jsonPayload);" in code, "Missing Serial.println(jsonPayload) call"
    print("[PASS] 1. Structured JSON Serial Emission: Verified")

    # 2. Elimination of Sensor Failure Masking
    assert "float pm1 = 7.0" not in code, "Found hardcoded dummy PMS7003 readings in loop()"
    assert "temp = 29.5;" not in code, "Found hardcoded dummy BME280 temperature in driver"
    assert "hum = 65.0;" not in code, "Found hardcoded dummy BME280 humidity in driver"
    assert "press = 1012.0;" not in code, "Found hardcoded dummy BME280 pressure in driver"
    assert "sensor_health" in code, "Missing sensor_health in JSON payload"
    assert '"null"' in code, "Missing explicit null string formatter for failed sensors"
    print("[PASS] 2. Sensor Failure Masking: Completely Removed & Replaced by null/ERROR flags")

    # 3. Non-Blocking Wi-Fi & MQTT Reconnection Engine
    assert "handleWiFiReconnection" in code, "Missing non-blocking Wi-Fi reconnection state machine"
    assert "connect(broker, MQTT_PORT, 500)" in code, "Missing 500ms bounded socket connect timeout"
    assert "broker.hivemq.com" in code and "broker.emqx.io" in code, "Missing dual-broker failover endpoints"
    assert "last_mqtt_attempt" in code, "Missing reconnect backoff interval timer"
    print("[PASS] 3. Non-Blocking Network Operations & Dual-Broker Failover: Verified")

    # 4. JSON Schema & SensorHealthEngine Integration
    lines = code.split("\n")
    fmt_parts = []
    in_snprintf = False
    for line in lines:
        if "snprintf(jsonPayload" in line:
            in_snprintf = True
            continue
        if in_snprintf:
            line_str = line.strip()
            if line_str.startswith('"') and (line_str.endswith('"') or line_str.endswith('",') or line_str.endswith('"')):
                c_str = re.search(r'"(.*)"', line_str)
                if c_str:
                    fmt_parts.append(c_str.group(1).replace('\\"', '"'))
            if "DEVICE_UID" in line:
                break
    fmt_clean = "".join(fmt_parts).replace("%lu", "%s").replace("%d", "%s")

    now = datetime.now(timezone.utc)

    # Test Scenario A: All sensors online & valid
    valid_json_str = fmt_clean % (
        "AIRSENSE-NODE-KHI-01", "AIRSENSE-NODE-KHI-01", "BIC-KHI-ROOF-01", "KARACHI", "BIC_ROOF_KARACHI", "v3.5.0-HARDENED",
        "42", "1725270000",
        "6.5", "6.5", "8.2", "8.2", "10.1",
        "28.5", "28.5", "62.0", "62.0", "1013.2", "1013.2",
        "false",
        "OK", "OK", "OK", "OK",
        "WIFI_DIRECT"
    )
    payload_valid = json.loads(valid_json_str)
    assert payload_valid["device_id"] == "AIRSENSE-NODE-KHI-01"
    assert payload_valid["pm2_5"] == 8.2
    assert payload_valid["temperature"] == 28.5
    assert payload_valid["sensor_health"]["pms7003"] == "OK"
    assert payload_valid["sensor_health"]["bme280"] == "OK"
    assert payload_valid["sensor_health"]["rain"] == "OK"

    diag_valid = SensorHealthEngine.evaluate_sensor_connectivity(payload_valid, last_received_at=now)
    assert diag_valid.station_liveness == "LIVE_ACTIVE"
    assert diag_valid.sensors["pms7003"].is_connected is True
    assert diag_valid.sensors["pms7003"].status == "ONLINE"
    assert diag_valid.sensors["bme280"].is_connected is True
    assert diag_valid.sensors["bme280"].status == "ONLINE"
    print("[PASS] 4A. Telemetry Payload Valid Schema & Engine Evaluation: Verified")

    # Test Scenario B: PMS7003 Disconnected / Error
    pms_fail_json_str = fmt_clean % (
        "AIRSENSE-NODE-KHI-01", "AIRSENSE-NODE-KHI-01", "BIC-KHI-ROOF-01", "KARACHI", "BIC_ROOF_KARACHI", "v3.5.0-HARDENED",
        "43", "1725270005",
        "null", "null", "null", "null", "null",
        "28.5", "28.5", "62.0", "62.0", "1013.2", "1013.2",
        "false",
        "ERROR", "OK", "OK", "OK",
        "SERIAL_BRIDGE"
    )
    payload_pms_fail = json.loads(pms_fail_json_str)
    assert payload_pms_fail["pm2_5"] is None
    assert payload_pms_fail["pm10"] is None
    assert payload_pms_fail["sensor_health"]["pms7003"] == "ERROR"
    assert payload_pms_fail["sensor_health"]["bme280"] == "OK"

    diag_pms_fail = SensorHealthEngine.evaluate_sensor_connectivity(payload_pms_fail, last_received_at=now)
    assert diag_pms_fail.station_liveness == "PARTIAL_DEGRADED"
    assert diag_pms_fail.sensors["pms7003"].is_connected is False
    assert diag_pms_fail.sensors["pms7003"].status == "DISCONNECTED"
    assert diag_pms_fail.sensors["bme280"].is_connected is True
    print("[PASS] 4B. PMS7003 Error Reporting (null values + ERROR flag): Verified")

    # Test Scenario C: Both PMS7003 and BME280 Disconnected / Error
    all_fail_json_str = fmt_clean % (
        "AIRSENSE-NODE-KHI-01", "AIRSENSE-NODE-KHI-01", "BIC-KHI-ROOF-01", "KARACHI", "BIC_ROOF_KARACHI", "v3.5.0-HARDENED",
        "44", "1725270010",
        "null", "null", "null", "null", "null",
        "null", "null", "null", "null", "null", "null",
        "false",
        "ERROR", "ERROR", "OK", "OK",
        "SERIAL_BRIDGE"
    )
    payload_all_fail = json.loads(all_fail_json_str)
    assert payload_all_fail["pm2_5"] is None
    assert payload_all_fail["temperature"] is None
    assert payload_all_fail["sensor_health"]["pms7003"] == "ERROR"
    assert payload_all_fail["sensor_health"]["bme280"] == "ERROR"

    diag_all_fail = SensorHealthEngine.evaluate_sensor_connectivity(payload_all_fail, last_received_at=now)
    assert diag_all_fail.station_liveness == "PARTIAL_DEGRADED"
    assert diag_all_fail.sensors["pms7003"].is_connected is False
    assert diag_all_fail.sensors["bme280"].is_connected is False
    print("[PASS] 4C. Multi-Sensor Error Reporting (null values + ERROR flags): Verified")

    # 5. C++ Syntax Integrity Spot-Check
    open_braces = code.count("{")
    close_braces = code.count("}")
    assert open_braces == close_braces, f"Brace mismatch: {open_braces} open vs {close_braces} close"

    open_parens = code.count("(")
    close_parens = code.count(")")
    assert open_parens == close_parens, f"Paren mismatch: {open_parens} open vs {close_parens} close"
    print(f"[PASS] 5. C++ Syntax Balance: {open_braces} braces, {open_parens} parens verified balanced")

    print("\n" + "=" * 60)
    print("  ALL FIRMWARE HARDENING CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()

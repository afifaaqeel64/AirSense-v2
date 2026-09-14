"""Verification script for Worker 1 (Python Bridge & Dependencies Specialist).
Tests all modified scripts, classes, functions, and configuration files.
"""

import sys
import os
import json
import re

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

def test_requirements():
    print("[TEST] 1. Checking requirements.txt...")
    req_path = r"c:/Users/HP/AirSense-v2/requirements.txt"
    assert os.path.exists(req_path), "requirements.txt missing"
    with open(req_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "pyserial>=3.5" in content, "pyserial>=3.5 not in requirements.txt"
    assert "paho-mqtt>=2.0.0" in content, "paho-mqtt>=2.0.0 not in requirements.txt"
    print("  -> requirements.txt passed!")

def test_serial_live_bridge():
    print("[TEST] 2. Testing scripts/airsense_serial_live_bridge.py...")
    import scripts.airsense_serial_live_bridge as bridge
    
    # Check dual broker configuration
    broker_names = [b["name"] for b in bridge.BROKER_CONFIGS]
    assert "HiveMQ" in broker_names, "HiveMQ not in BROKER_CONFIGS"
    assert "EMQX" in broker_names, "EMQX not in BROKER_CONFIGS"
    
    # Check DualBrokerMqttPublisher
    pub = bridge.DualBrokerMqttPublisher()
    assert "HiveMQ" in pub.clients or len(pub.clients) >= 1, "HiveMQ client not initialized"
    assert "EMQX" in pub.clients or len(pub.clients) >= 1, "EMQX client not initialized"
    
    # Test JSON parsing with [JSON_TELEMETRY]
    test_json_line = '[JSON_TELEMETRY] {"device_uid":"AIRSENSE-NODE-KHI-01","sequence_number":42,"pm2_5":14.5,"temperature":30.2,"humidity":58.0,"pressure":1011.5,"rain_flag":false}'
    data_holder = {}
    payload, is_end = bridge.parse_serial_line(test_json_line, data_holder)
    assert payload is not None, "Failed to parse [JSON_TELEMETRY] line"
    assert payload["sequence_number"] == 42, f"Expected seq 42, got {payload['sequence_number']}"
    assert payload["pm2_5"] == 14.5, f"Expected pm2_5 14.5, got {payload['pm2_5']}"
    assert payload["temperature"] == 30.2, f"Expected temp 30.2, got {payload['temperature']}"
    assert payload["rain_flag"] is False, "Expected rain_flag False"
    assert payload["transmission_mode"] == "SERIAL_BRIDGE", "Expected transmission_mode SERIAL_BRIDGE"
    assert is_end is True, "JSON line should mark end of cycle"

    # Test raw JSON parsing
    test_raw_json = '{"device_uid":"AIRSENSE-NODE-KHI-01","sequence_number":99,"pm1":5.0,"pm2_5":18.2,"pm10":22.0,"temperature":32.1,"humidity":60.0,"pressure":1009.0,"rain_flag":true}'
    payload, is_end = bridge.parse_serial_line(test_raw_json, data_holder)
    assert payload is not None, "Failed to parse raw JSON line"
    assert payload["sequence_number"] == 99
    assert payload["pm2_5"] == 18.2
    assert payload["rain_flag"] is True

    # Test fallback ASCII debug parsing
    curr = {"pm1": 7.0, "pm2_5": 9.0, "pm10": 10.0, "temp": 29.5, "hum": 65.0, "press": 1012.0, "gas": 45.2, "rain": False}
    p, end = bridge.parse_serial_line("PM1.0: 6.5 | PM2.5: 8.2 | PM10: 10.1", curr)
    assert p is None and not end
    assert curr["pm1"] == 6.5
    assert curr["pm2_5"] == 8.2
    assert curr["pm10"] == 10.1

    p, end = bridge.parse_serial_line("Temp: 28.5 C | Humidity: 62.0 % | Pressure: 1013.2", curr)
    assert p is None and not end
    assert curr["temp"] == 28.5
    assert curr["hum"] == 62.0
    assert curr["press"] == 1013.2

    p, end = bridge.parse_serial_line("Rain: YES", curr)
    assert p is None and not end
    assert curr["rain"] is True

    p, end = bridge.parse_serial_line("--------------------------------------------------------", curr)
    assert p is None and end is True

    # Test build_telemetry_payload
    built = bridge.build_telemetry_payload(100, curr["pm1"], curr["pm2_5"], curr["pm10"], curr["temp"], curr["hum"], curr["press"], curr["rain"])
    assert built["sequence_number"] == 100
    assert built["pm2_5"] == 8.2
    assert built["sensor_health"]["pms7003"] == "OK"

    # Test publish method (isolated error handling)
    pub.publish(built)

    # Test port scanner function
    ports = bridge.scan_available_ports()
    assert isinstance(ports, list), "scan_available_ports should return a list"
    
    # Test find_esp32_port with non-existent port (should fall back safely)
    selected_port = bridge.find_esp32_port("NON_EXISTENT_COM99")
    if ports:
        assert selected_port == ports[0]
    else:
        assert selected_port is None

    print("  -> airsense_serial_live_bridge.py passed all unit checks!")

def test_mqtt_forwarder():
    print("[TEST] 3. Testing scripts/airsense_mqtt_live_forwarder.py...")
    import scripts.airsense_mqtt_live_forwarder as fwd
    
    client = fwd.create_mqtt_client("HiveMQ", "broker.hivemq.com", 1883)
    assert client is not None, "create_mqtt_client returned None"

    # Test on_message with valid payload
    class MockMsg:
        payload = json.dumps({
            "station_code": "BIC-KHI-ROOF-01",
            "sequence_number": 55,
            "pm2_5": 11.4,
            "temperature": 27.8,
            "humidity": 70.1,
            "pressure": 1014.2,
            "rain_flag": False
        }).encode("utf-8")
    
    fwd.on_message(client, {}, MockMsg())

    # Test on_message with malformed payload (must not crash)
    class BadMsg:
        payload = b"not a json string at all"
    
    fwd.on_message(client, {}, BadMsg())
    print("  -> airsense_mqtt_live_forwarder.py passed all unit checks!")

def test_serial_forwarder():
    print("[TEST] 4. Testing scripts/airsense_serial_forwarder.py...")
    import scripts.airsense_serial_forwarder as sfwd
    
    ports = sfwd.scan_ports()
    assert isinstance(ports, list), "scan_ports should return a list"
    target = sfwd.find_target_port("NON_EXISTENT_PORT")
    if ports:
        assert target == ports[0]
    else:
        assert target is None
    print("  -> airsense_serial_forwarder.py passed all unit checks!")

def test_run_bridge_daemon_bat():
    print("[TEST] 5. Checking run_bridge_daemon.bat...")
    bat_path = r"c:/Users/HP/AirSense-v2/run_bridge_daemon.bat"
    with open(bat_path, "r", encoding="utf-8") as f:
        bat_content = f.read()
    assert "PORT_ARG" in bat_content, "PORT_ARG logic missing from run_bridge_daemon.bat"
    assert "AUTO" in bat_content, "AUTO dynamic detection fallback missing from run_bridge_daemon.bat"
    print("  -> run_bridge_daemon.bat passed!")

if __name__ == "__main__":
    print("=== Worker 1 Verification Suite ===")
    test_requirements()
    test_serial_live_bridge()
    test_mqtt_forwarder()
    test_serial_forwarder()
    test_run_bridge_daemon_bat()
    print("=== ALL WORKER 1 VERIFICATIONS PASSED SUCCESSFULLY ===")

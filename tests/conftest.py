"""AirSense-v2 Pytest Shared Fixtures and Test Harness Utilities."""

import time
import pytest
from typing import Dict, Any, List, Generator
import paho.mqtt.client as mqtt


@pytest.fixture
def sample_contract_payload() -> Dict[str, Any]:
    """Canonical telemetry packet strictly conforming to PROJECT.md interface contract."""
    return {
        "device_id": "AIRSENSE-NODE-01",
        "node_id": "AIRSENSE-NODE-01",
        "location": "BIC_ROOF_KARACHI",
        "sequence_number": 1234,
        "timestamp_epoch": int(time.time()),
        "pm1_0": 6.5,
        "pm2_5": 8.2,
        "pm10": 10.1,
        "temperature_c": 28.5,
        "humidity_pct": 62.0,
        "pressure_hpa": 1013.2,
        "gas_resistance_kohm": 45.2,
        "rain_flag": False,
        "sensor_health": {
            "pms7003": "OK",
            "bme280": "OK",
            "rain": "OK"
        },
        "transmission_mode": "SERIAL_BRIDGE"
    }


@pytest.fixture
def sample_aliased_payload() -> Dict[str, Any]:
    """Legacy/bridge formatted payload using field aliases (pm25, temperature, humidity, pressure)."""
    return {
        "schema_version": "1.0",
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "campus_code": "KARACHI",
        "firmware_version": "v3.5.0-HARDWARE-SERIAL",
        "sequence_number": 5678,
        "timestamp_epoch": int(time.time()),
        "pm1": 7.0,
        "pm25": 9.2,
        "pm10": 11.5,
        "temperature": 29.8,
        "humidity": 64.5,
        "pressure": 1011.8,
        "rain_flag": True
    }


@pytest.fixture
def paho_mqtt_client_factory():
    """Factory fixture that generates Paho MQTT clients and ensures guaranteed teardown/disconnect."""
    created_clients: List[mqtt.Client] = []

    def _create(client_id_prefix: str = "test-client") -> mqtt.Client:
        cid = f"{client_id_prefix}-{int(time.time() * 1000)}"
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
        except AttributeError:
            client = mqtt.Client(client_id=cid)
        created_clients.append(client)
        return client

    yield _create

    for client in created_clients:
        try:
            client.loop_stop()
            if client.is_connected():
                client.disconnect()
        except Exception:
            pass

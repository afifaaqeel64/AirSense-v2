"""AirSense Pakistan Hardware Telemetry Bridge Package."""

from services.telemetry.hardware_telemetry_bridge import (
    HardwareTelemetryBridge,
    NormalizedReading,
    HardwareStatusResponse,
    get_hardware_bridge,
    assert_d_drive,
    OFFLINE_THRESHOLD_SECONDS,
    PRIMARY_MQTT_BROKER,
    PRIMARY_MQTT_PORT,
    PRIMARY_MQTT_TOPIC,
    SECONDARY_MQTT_BROKER,
    VERCEL_FALLBACK_URL
)

__all__ = [
    "HardwareTelemetryBridge",
    "NormalizedReading",
    "HardwareStatusResponse",
    "get_hardware_bridge",
    "assert_d_drive",
    "OFFLINE_THRESHOLD_SECONDS",
    "PRIMARY_MQTT_BROKER",
    "PRIMARY_MQTT_PORT",
    "PRIMARY_MQTT_TOPIC",
    "SECONDARY_MQTT_BROKER",
    "VERCEL_FALLBACK_URL"
]

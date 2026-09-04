"""AirSense-v2 Payload Schema Normalization & Zero-NaN Safety Test Suite.

Rigorously verifies:
1. Canonical schema normalization across field aliases (pm2_5 vs pm25, temperature vs temperature_c, etc.).
2. Resilient handling of null, None, empty dicts {}, and missing payload keys.
3. Strict Zero-NaN / Zero-Crash sanitization (float('nan'), float('inf'), string 'NaN', non-numeric noise).
4. Preservation of exact 0.0 numeric values without falsy fallback truncation.
5. Multi-type coercion (booleans, strings, floats, ints, epoch timestamps).
6. Integration with SensorHealthEngine and QualityControlEngine.
"""

import math
import time
from datetime import datetime, timezone
import pytest
from typing import Dict, Any, Optional

from services.quality_control.sensor_health_engine import (
    SensorHealthEngine,
    StationDiagnosticReport,
    SensorHealthStatus
)
from services.quality_control.qc_engine import (
    QualityControlEngine,
    QCResult
)


def normalize_payload_dictionary(raw_dict: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pure, robust schema normalizer and NaN sanitizer utility function."""
    if not raw_dict or not isinstance(raw_dict, dict):
        return {
            "device_id": "UNKNOWN",
            "sequence_number": None,
            "timestamp_epoch": None,
            "pm1_0": None,
            "pm2_5": None,
            "pm10": None,
            "temperature_c": None,
            "humidity_pct": None,
            "pressure_hpa": None,
            "gas_resistance_kohm": None,
            "rain_flag": False,
            "sensor_health": {}
        }

    def safe_float(val: Any) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            if math.isnan(val) or math.isinf(val):
                return None
            return float(val)
        if isinstance(val, str):
            v_strip = val.strip().lower()
            if v_strip in ("", "none", "null", "nan", "inf", "-inf", "n/a", "--", "undefined"):
                return None
            try:
                num = float(v_strip)
                if math.isnan(num) or math.isinf(num):
                    return None
                return num
            except (ValueError, TypeError):
                return None
        return None

    def safe_int(val: Any) -> Optional[int]:
        f = safe_float(val)
        return int(f) if f is not None else None

    def safe_bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            s = val.strip().lower()
            return s in ("true", "1", "yes", "wet", "rain", "y")
        return False

    def pick_first(keys):
        for k in keys:
            if k in raw_dict and raw_dict[k] is not None:
                val = safe_float(raw_dict[k])
                if val is not None:
                    return val
        return None

    pm1 = pick_first(["pm1_0", "pm1", "pm_1_0", "pm1_ugm3"])
    pm25 = pick_first(["pm2_5", "pm25", "pm_2_5", "pm25_ugm3", "pm25_raw"])
    pm10 = pick_first(["pm10", "pm_10", "pm10_0", "pm10_ugm3"])
    temp = pick_first(["temperature_c", "temperature", "temp", "temp_c"])
    hum = pick_first(["humidity_pct", "humidity", "hum", "hum_pct", "relative_humidity"])
    press = pick_first(["pressure_hpa", "pressure", "press", "press_hpa", "barometric_pressure"])
    gas = pick_first(["gas_resistance_kohm", "gas_resistance", "gas", "gas_kohm"])

    # Rain
    rain_val = False
    for r_key in ["rain_flag", "rain", "is_raining", "precipitation_active"]:
        if r_key in raw_dict and raw_dict[r_key] is not None:
            rain_val = safe_bool(raw_dict[r_key])
            break

    # Identifiers
    dev_id = raw_dict.get("device_id") or raw_dict.get("device_uid") or raw_dict.get("node_id") or "UNKNOWN"
    seq = safe_int(raw_dict.get("sequence_number") or raw_dict.get("seq") or raw_dict.get("packet_id"))

    # Epoch
    epoch = safe_int(raw_dict.get("timestamp_epoch") or raw_dict.get("timestamp"))
    if epoch is None and "observed_at" in raw_dict:
        obs = raw_dict["observed_at"]
        if isinstance(obs, (int, float)):
            epoch = int(obs)
        elif isinstance(obs, datetime):
            epoch = int(obs.timestamp())
        elif isinstance(obs, str):
            try:
                epoch = int(datetime.fromisoformat(obs.replace("Z", "+00:00")).timestamp())
            except Exception:
                epoch = None

    health = raw_dict.get("sensor_health")
    if not isinstance(health, dict):
        health = {}

    return {
        "device_id": str(dev_id),
        "sequence_number": seq,
        "timestamp_epoch": epoch,
        "pm1_0": pm1,
        "pm2_5": pm25,
        "pm10": pm10,
        "temperature_c": temp,
        "humidity_pct": hum,
        "pressure_hpa": press,
        "gas_resistance_kohm": gas,
        "rain_flag": rain_val,
        "sensor_health": health
    }


class TestFieldAliasNormalization:
    """Verifies that diverse field names from firmware, bridges, and APIs normalize to canonical fields."""

    @pytest.mark.parametrize("key_name, val, expected", [
        ("pm2_5", 14.2, 14.2),
        ("pm25", 18.5, 18.5),
        ("pm_2_5", 22.0, 22.0),
        ("pm25_ugm3", 9.1, 9.1),
    ])
    def test_pm25_field_aliases(self, key_name, val, expected):
        """Resolves all PM2.5 key variants."""
        res = normalize_payload_dictionary({key_name: val})
        assert res["pm2_5"] == expected

    @pytest.mark.parametrize("key_name, val, expected", [
        ("pm1_0", 6.2, 6.2),
        ("pm1", 8.4, 8.4),
        ("pm_1_0", 5.9, 5.9),
    ])
    def test_pm1_field_aliases(self, key_name, val, expected):
        """Resolves all PM1.0 key variants."""
        res = normalize_payload_dictionary({key_name: val})
        assert res["pm1_0"] == expected

    @pytest.mark.parametrize("key_name, val, expected", [
        ("pm10", 25.4, 25.4),
        ("pm_10", 30.1, 30.1),
        ("pm10_0", 19.8, 19.8),
    ])
    def test_pm10_field_aliases(self, key_name, val, expected):
        """Resolves all PM10 key variants."""
        res = normalize_payload_dictionary({key_name: val})
        assert res["pm10"] == expected

    @pytest.mark.parametrize("key_name, val, expected", [
        ("temperature_c", 28.5, 28.5),
        ("temperature", 31.2, 31.2),
        ("temp", 26.8, 26.8),
        ("temp_c", 29.0, 29.0),
    ])
    def test_temperature_field_aliases(self, key_name, val, expected):
        """Resolves all temperature key variants."""
        res = normalize_payload_dictionary({key_name: val})
        assert res["temperature_c"] == expected

    @pytest.mark.parametrize("key_name, val, expected", [
        ("humidity_pct", 65.0, 65.0),
        ("humidity", 58.2, 58.2),
        ("hum", 72.1, 72.1),
        ("hum_pct", 49.5, 49.5),
    ])
    def test_humidity_field_aliases(self, key_name, val, expected):
        """Resolves all humidity key variants."""
        res = normalize_payload_dictionary({key_name: val})
        assert res["humidity_pct"] == expected

    @pytest.mark.parametrize("key_name, val, expected", [
        ("pressure_hpa", 1013.2, 1013.2),
        ("pressure", 1009.5, 1009.5),
        ("press", 1015.0, 1015.0),
        ("barometric_pressure", 1011.8, 1011.8),
    ])
    def test_pressure_field_aliases(self, key_name, val, expected):
        """Resolves all pressure key variants."""
        res = normalize_payload_dictionary({key_name: val})
        assert res["pressure_hpa"] == expected

    @pytest.mark.parametrize("key_name, val, expected", [
        ("rain_flag", True, True),
        ("rain", "YES", True),
        ("is_raining", "Wet", True),
        ("precipitation_active", 1, True),
        ("rain_flag", False, False),
        ("rain", "NO", False),
        ("is_raining", "Dry", False),
        ("precipitation_active", 0, False),
    ])
    def test_rain_field_aliases_and_coercion(self, key_name, val, expected):
        """Resolves all rain flag key variants and multi-type string/int coercions."""
        res = normalize_payload_dictionary({key_name: val})
        assert res["rain_flag"] is expected


class TestHandlingNullNoneMissingKeys:
    """Verifies complete stability on empty dicts, missing keys, and explicit null values."""

    def test_none_input_returns_safe_defaults(self):
        """None input argument does not raise TypeError or AttributeError."""
        res = normalize_payload_dictionary(None)
        assert res["device_id"] == "UNKNOWN"
        assert res["pm2_5"] is None
        assert res["temperature_c"] is None
        assert res["rain_flag"] is False

    def test_empty_dictionary_returns_safe_defaults(self):
        """Empty dictionary {} returns dictionary with None values."""
        res = normalize_payload_dictionary({})
        assert res["device_id"] == "UNKNOWN"
        assert res["pm2_5"] is None
        assert res["temperature_c"] is None

    def test_all_fields_explicit_none(self):
        """Payload with all keys explicitly set to None."""
        payload = {
            "device_id": None,
            "pm1_0": None,
            "pm2_5": None,
            "pm10": None,
            "temperature_c": None,
            "humidity_pct": None,
            "pressure_hpa": None,
            "rain_flag": None
        }
        res = normalize_payload_dictionary(payload)
        assert res["pm2_5"] is None
        assert res["temperature_c"] is None
        assert res["rain_flag"] is False

    def test_partial_sensor_payload_only_pms7003(self):
        """Payload containing only particulate counter data without environmental sensors."""
        payload = {"pm1": 6.0, "pm2_5": 12.5, "pm10": 18.0}
        res = normalize_payload_dictionary(payload)
        assert res["pm2_5"] == 12.5
        assert res["temperature_c"] is None
        assert res["pressure_hpa"] is None

    def test_partial_sensor_payload_only_bme280(self):
        """Payload containing only BME280 metrics without particulate counter."""
        payload = {"temperature": 27.5, "humidity": 60.0, "pressure": 1012.0}
        res = normalize_payload_dictionary(payload)
        assert res["pm2_5"] is None
        assert res["temperature_c"] == 27.5
        assert res["humidity_pct"] == 60.0


class TestZeroNanAndInfinitySafety:
    """Verifies that NaN, Infinity, and invalid string garbage never cause unhandled crashes or NaN leaks."""

    @pytest.mark.parametrize("nan_val", [
        float("nan"),
        "NaN",
        "nan",
        "NAN",
        "none",
        "null",
        "N/A",
        "--",
        "undefined",
        "error_str"
    ])
    def test_nan_values_sanitized_to_none(self, nan_val):
        """All variations of NaN and non-numeric strings are cleanly converted to None."""
        payload = {
            "pm2_5": nan_val,
            "temperature": nan_val,
            "humidity": nan_val
        }
        res = normalize_payload_dictionary(payload)
        assert res["pm2_5"] is None
        assert res["temperature_c"] is None
        assert res["humidity_pct"] is None

    @pytest.mark.parametrize("inf_val", [
        float("inf"),
        float("-inf"),
        "Infinity",
        "-Infinity",
        "inf",
        "-inf"
    ])
    def test_infinity_values_sanitized_to_none(self, inf_val):
        """Positive and negative infinity are trapped and sanitized to None."""
        payload = {
            "pm2_5": inf_val,
            "temperature_c": inf_val,
            "pressure_hpa": inf_val
        }
        res = normalize_payload_dictionary(payload)
        assert res["pm2_5"] is None
        assert res["temperature_c"] is None
        assert res["pressure_hpa"] is None

    def test_exact_zero_values_strictly_preserved(self):
        """Crucial: Exact 0.0 floats must NOT be treated as falsy and must be preserved."""
        payload = {
            "pm1": 0.0,
            "pm2_5": 0.0,
            "pm10": 0.0,
            "temperature_c": 0.0,
            "humidity_pct": 0.0,
            "pressure_hpa": 0.0
        }
        res = normalize_payload_dictionary(payload)
        assert res["pm1_0"] == 0.0
        assert res["pm2_5"] == 0.0
        assert res["pm10"] == 0.0
        assert res["temperature_c"] == 0.0
        assert res["humidity_pct"] == 0.0
        assert res["pressure_hpa"] == 0.0

    def test_numeric_string_coercion(self):
        """Cleanly parses string numbers with leading/trailing whitespaces."""
        payload = {
            "pm2_5": " 15.6 ",
            "temperature": " 28.2\n",
            "humidity": "\t62.5 "
        }
        res = normalize_payload_dictionary(payload)
        assert res["pm2_5"] == 15.6
        assert res["temperature_c"] == 28.2
        assert res["humidity_pct"] == 62.5


class TestQualityControlAndSensorHealthIntegration:
    """Verifies that normalized payloads cleanly execute through QC and Sensor Health engines."""

    def test_normalized_payload_evaluates_in_sensor_health_engine(self):
        """Evaluates normalized payload in SensorHealthEngine."""
        now = datetime.now(timezone.utc)
        payload = {
            "pm2_5": 12.0,
            "pm10": 18.0,
            "temperature": 29.5,
            "humidity": 62.0,
            "pressure": 1013.2,
            "rain_flag": False
        }
        norm = normalize_payload_dictionary(payload)
        report = SensorHealthEngine.evaluate_sensor_connectivity(norm, last_received_at=now)

        assert report.station_liveness == "LIVE_ACTIVE"
        assert report.sensors["pms7003"].status == "ONLINE"
        assert report.sensors["pms7003"].is_connected is True
        assert report.sensors["bme280"].status == "ONLINE"
        assert report.sensors["bme280"].is_connected is True
        assert report.sensors["rain_sensor"].status == "ONLINE"

    def test_normalized_payload_evaluates_in_quality_control_engine(self):
        """Evaluates normalized payload in QualityControlEngine."""
        payload = {
            "observed_at": datetime.now(timezone.utc),
            "pm1": 6.5,
            "pm2_5": 11.0,
            "pm10": 18.5,
            "temperature_c": 28.0,
            "humidity_pct": 55.0,
            "pressure_hpa": 1012.0
        }
        norm = normalize_payload_dictionary(payload)
        qc_input = {
            "observed_at": payload["observed_at"],
            "pm1": norm["pm1_0"],
            "pm2_5": norm["pm2_5"],
            "pm10": norm["pm10"],
            "temperature_c": norm["temperature_c"],
            "humidity_pct": norm["humidity_pct"],
            "pressure_hpa": norm["pressure_hpa"]
        }
        qc_result: QCResult = QualityControlEngine.evaluate_reading(qc_input)
        assert qc_result.quality_status == "accepted"
        assert qc_result.quality_score >= 0.95
        assert qc_result.impossible_value_flag is False

    def test_corrupt_payload_in_qc_engine_rejected(self):
        """Verifies impossible values (e.g. negative pressure or PM2.5 > 1000) are flagged by QC."""
        qc_input = {
            "observed_at": datetime.now(timezone.utc),
            "pm2_5": 1500.0,  # Exceeds max 1000
            "temperature_c": 120.0,  # Exceeds max 60
            "pressure_hpa": 500.0  # Below min 800
        }
        qc_result: QCResult = QualityControlEngine.evaluate_reading(qc_input)
        assert qc_result.impossible_value_flag is True
        assert qc_result.quality_status == "rejected"
        assert len(qc_result.validation_messages) >= 2

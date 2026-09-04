"""Challenger 2 Empirical Stress Test Harness: Bridge Daemon, Hot-Plug & Port-Lock Resilience.

Adversarial Verification Suite for:
1. Dynamic USB hot-plugging simulation (port migration, COM disconnects, reappearance on new port).
2. Port locked / PermissionError simulation (Arduino IDE conflict, access denied, recovery after lock release).
3. Corrupted, malformed, truncated, and hostile serial lines (binary garbage, partial JSON, injection attacks).
4. Falsy zero preservation (0.0 values across PM1/2.5/10, Temp, Humidity, Pressure, Gas, and rain_flag=false).
5. Dual-broker failure isolation under transport failure.
"""

import json
import math
import random
import re
import time
from unittest.mock import MagicMock, patch, PropertyMock
import pytest
import serial

from scripts.airsense_serial_live_bridge import (
    find_esp32_port,
    scan_available_ports,
    push_to_local_api,
    build_telemetry_payload,
    parse_serial_line,
    DualBrokerMqttPublisher,
    run_bridge,
    KNOWN_PORT_KEYWORDS
)


class MockPortInfo:
    """Simulates serial.tools.list_ports_common.ListPortInfo."""
    def __init__(self, device: str, description: str, hwid: str = ""):
        self.device = device
        self.description = description
        self.hwid = hwid


class TestDynamicHotPluggingAndPortMigration:
    """Stress-tests USB disconnect, disappearance, and dynamic port migration across different COM interfaces."""

    @patch("scripts.airsense_serial_live_bridge.time.sleep", return_value=None)
    @patch("serial.Serial")
    @patch("serial.tools.list_ports.comports")
    def test_hotplug_port_migration_disconnect_and_reconnect_new_port(self, mock_comports, mock_serial, mock_sleep, capsys):
        """Simulates USB cable unplugged from COM3, scan showing 0 ports, then plugged into COM8 (CH340).
        Verifies daemon auto-discovers COM8 without crashing or exiting.
        """
        iteration = 0
        published_payloads = []

        def comports_side_effect():
            nonlocal iteration
            iteration += 1
            if iteration == 1:
                # Cycle 1: Connected to COM3
                return [MockPortInfo("COM3", "Silicon Labs CP210x USB to UART Bridge (COM3)")]
            elif iteration == 2:
                # Cycle 2: Cable unplugged, no USB ports in system
                return []
            elif iteration == 3:
                # Cycle 3: Re-plugged into another USB port (COM8)
                return [MockPortInfo("COM8", "USB-SERIAL CH340 (COM8)")]
            else:
                return [MockPortInfo("COM8", "USB-SERIAL CH340 (COM8)")]

        mock_comports.side_effect = comports_side_effect

        serial_inst_com3 = MagicMock()
        serial_inst_com3.is_open = True
        serial_inst_com3.readline.side_effect = [
            b"[JSON_TELEMETRY] {\"sequence_number\": 1, \"pm2_5\": 15.0, \"temperature\": 30.0}\n",
            serial.SerialException("ClearCommError failed (device unplugged)")
        ]

        serial_inst_com8 = MagicMock()
        serial_inst_com8.is_open = True
        serial_inst_com8.readline.side_effect = [
            b"[JSON_TELEMETRY] {\"sequence_number\": 2, \"pm2_5\": 16.5, \"temperature\": 29.8}\n",
            KeyboardInterrupt("End stress test")
        ]

        def serial_constructor(port, *args, **kwargs):
            if port == "COM3":
                return serial_inst_com3
            elif port == "COM8":
                return serial_inst_com8
            raise serial.SerialException(f"Unknown port {port}")

        mock_serial.side_effect = serial_constructor

        with patch.object(DualBrokerMqttPublisher, "publish", side_effect=lambda p: published_payloads.append(p)):
            run_bridge()

        # Assertions
        assert len(published_payloads) == 2
        assert published_payloads[0]["sequence_number"] == 1
        assert published_payloads[0]["pm2_5"] == 15.0
        assert published_payloads[1]["sequence_number"] == 2
        assert published_payloads[1]["pm2_5"] == 16.5

        out = capsys.readouterr().out
        assert "Connected to COM3" in out
        assert "No serial COM ports found" in out or "BRIDGE DISCONNECT" in out
        assert "Connected to COM8" in out

    @patch("scripts.airsense_serial_live_bridge.time.sleep", return_value=None)
    @patch("serial.Serial")
    @patch("serial.tools.list_ports.comports")
    def test_rapid_port_churn_and_transient_disconnections(self, mock_comports, mock_serial, mock_sleep):
        """Simulates rapid consecutive port changes: COM10 -> None -> COM12 -> None -> COM14.
        Verifies bridge maintains continuous reconnect loop.
        """
        step = 0

        def comports_step():
            nonlocal step
            step += 1
            if step == 1:
                return [MockPortInfo("COM10", "USB Serial Device (COM10)")]
            elif step == 2:
                return []
            elif step == 3:
                return [MockPortInfo("COM12", "WCH CH340 (COM12)")]
            elif step == 4:
                return []
            else:
                return [MockPortInfo("COM14", "CP2102 USB Bridge (COM14)")]

        mock_comports.side_effect = comports_step

        connection_attempts = []

        def serial_init(port, *args, **kwargs):
            connection_attempts.append(port)
            if port == "COM14":
                raise KeyboardInterrupt("Stop rapid churn test")
            raise serial.SerialException(f"Transient bus error on {port}")

        mock_serial.side_effect = serial_init

        run_bridge()

        assert len(connection_attempts) == 3
        assert "COM10" in connection_attempts
        assert "COM12" in connection_attempts
        assert "COM14" in connection_attempts


class TestPortLockAndPermissionErrorHandling:
    """Stress-tests locked serial ports, PermissionError / Access Denied from Arduino IDE, and retry recovery."""

    @patch("scripts.airsense_serial_live_bridge.time.sleep", return_value=None)
    @patch("serial.Serial")
    @patch("serial.tools.list_ports.comports")
    def test_permission_error_locked_port_retries_until_unlocked(self, mock_comports, mock_serial, mock_sleep, capsys):
        """Simulates Arduino IDE holding lock for 4 retry cycles, then releasing.
        Verifies actionable warning output, backoff sleep, and successful connection upon lock release.
        """
        mock_comports.return_value = [MockPortInfo("COM5", "Silicon Labs CP210x (COM5)")]
        attempts = 0
        published = []

        def serial_factory(port, *args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts <= 3:
                raise serial.SerialException(f"could not open port '{port}': PermissionError(13, 'Access is denied.', None, 5)")
            
            # 4th attempt: lock released
            mock_ser = MagicMock()
            mock_ser.is_open = True
            mock_ser.readline.side_effect = [
                b"[JSON_TELEMETRY] {\"sequence_number\": 10, \"pm2_5\": 8.5}\n",
                KeyboardInterrupt("Stop lock test")
            ]
            return mock_ser

        mock_serial.side_effect = serial_factory

        with patch.object(DualBrokerMqttPublisher, "publish", side_effect=lambda p: published.append(p)):
            run_bridge("COM5")

        assert attempts == 4
        assert len(published) == 1
        assert published[0]["sequence_number"] == 10
        assert published[0]["pm2_5"] == 8.5

        out = capsys.readouterr().out
        assert "Arduino IDE" in out
        assert "busy or open in another application" in out

    @patch("scripts.airsense_serial_live_bridge.time.sleep", return_value=None)
    @patch("serial.Serial")
    @patch("serial.tools.list_ports.comports")
    def test_unexpected_os_error_recovers_without_terminating(self, mock_comports, mock_serial, mock_sleep, capsys):
        """Simulates generic OSError (e.g. driver error, I/O device error).
        Verifies [BRIDGE ERROR] catch-all branch triggers exponential backoff and continues loop.
        """
        mock_comports.return_value = [MockPortInfo("COM2", "UART (COM2)")]
        calls = 0

        def serial_os_error(port, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("Device I/O error 0x8007045D")
            raise KeyboardInterrupt("Stop OSError test")

        mock_serial.side_effect = serial_os_error

        run_bridge("COM2")

        assert calls == 2
        out = capsys.readouterr().out
        assert "[BRIDGE ERROR] Unexpected exception: Device I/O error 0x8007045D" in out


class TestCorruptedMalformedAndHostileSerialLines:
    """Stress-tests garbage bytes, truncated JSON, invalid encoding, and hostile payloads."""

    def test_corrupted_raw_binary_noise_and_null_bytes(self):
        """Verifies binary noise, null bytes, and non-UTF8 characters do not crash parse_serial_line."""
        current_data = {"pm2_5": 12.0, "temp": 28.0}
        hostile_lines = [
            "\x00\x00\x00\x00",
            "\xff\xfe\xfd\xfc",
            "\x1b[2J\x1b[H",  # ANSI clear screen escape
            "???\x07\x07\x07\x08\x08",
            "   \r\n\t  ",
            "~~~~~~~~~~~~~~~~~~~~~~",
            "NULL NIL NONE UNDEFINED"
        ]
        for h_line in hostile_lines:
            payload, is_end = parse_serial_line(h_line, current_data)
            assert payload is None
            assert is_end is False
        assert current_data["pm2_5"] == 12.0

    def test_truncated_json_fragments(self):
        """Verifies partial / cut-off JSON packets are safely dropped without exception."""
        current_data = {}
        truncated_samples = [
            "[JSON_TELEMETRY] {\"sequence_number\": 5, \"pm2_5\": ",
            "[JSON_TELEMETRY] {\"device_uid\": \"AIRSENSE",
            "{\"pm1\": 5.0, \"pm2_5\":",
            "[JSON_TELEMETRY] {",
            "[JSON_TELEMETRY] }",
            "{\"broken_json\": [1, 2, 3,",
            "[JSON_TELEMETRY] {\"pm2_5\": 12.0, \"temperature\": 28.5"  # Missing closing brace
        ]
        for frag in truncated_samples:
            payload, is_end = parse_serial_line(frag, current_data)
            assert payload is None
            assert is_end is False

    def test_partial_ascii_lines_do_not_corrupt_state(self):
        """Verifies incomplete ASCII lines do not inject invalid regex values."""
        current_data = {"pm1": 7.0, "pm2_5": 9.0, "pm10": 10.0}
        
        # Missing PM10
        line1 = "PM1.0: 4.2 | PM2.5: 8.1 |"
        payload, is_end = parse_serial_line(line1, current_data)
        assert payload is None
        # PMS single PM2.5 fallback regex should catch PM2.5
        assert current_data["pm2_5"] == 8.1
        assert current_data["pm1"] == 7.0  # PM1 unchanged

    def test_hostile_injection_strings_in_json(self):
        """Verifies SQL injection, HTML tags, and massive strings parse safely into dict fields without crashing."""
        injection_json = {
            "device_uid": "AIRSENSE'; DROP TABLE telemetry; --",
            "sequence_number": 9999,
            "pm2_5": 14.2,
            "temperature": 29.0,
            "sensor_health": {"pms7003": "<script>alert('xss')</script>"}
        }
        line = f"[JSON_TELEMETRY] {json.dumps(injection_json)}"
        current_data = {}
        payload, is_end = parse_serial_line(line, current_data)
        
        assert payload is not None
        assert is_end is True
        assert payload["sequence_number"] == 9999
        assert payload["pm2_5"] == 14.2
        assert payload["sensor_health"]["pms7003"] == "<script>alert('xss')</script>"

    def test_interleaved_stream_of_noise_and_valid_packets(self):
        """Simulates real-world noisy UART: valid JSON -> garbage -> ASCII -> separator -> valid JSON."""
        current_data = {"pm1": 7.0, "pm2_5": 9.0, "pm10": 10.0, "temp": 29.5, "hum": 65.0, "press": 1012.0, "rain": False}
        stream = [
            b"rst:0x1 (POWERON_RESET),boot:0x13\r\n",
            b"[JSON_TELEMETRY] {\"sequence_number\": 1, \"pm2_5\": 10.0, \"temperature\": 25.0}\r\n",
            b"\xff\xfe\x00\x01 garbled serial byte stream\r\n",
            b"PM1.0: 5.0 | PM2.5: 12.0 | PM10: 15.0\r\n",
            b"Temp: 31.0 C | Humidity: 50.0 % | Pressure: 1010.0\r\n",
            b"Rain: Wet\r\n",
            b"--------------------------------------------------------\r\n",
            b"[JSON_TELEMETRY] {\"sequence_number\": 3, \"pm2_5\": 8.0, \"temperature\": 24.0}\r\n"
        ]

        collected_payloads = []
        for raw in stream:
            line = raw.decode('utf-8', errors='ignore').strip()
            p, is_end = parse_serial_line(line, current_data)
            if p:
                collected_payloads.append(p)
            elif is_end:
                payload = build_telemetry_payload(
                    2,
                    current_data["pm1"], current_data["pm2_5"], current_data["pm10"],
                    current_data["temp"], current_data["hum"], current_data["press"],
                    current_data["rain"], current_data.get("gas")
                )
                collected_payloads.append(payload)

        assert len(collected_payloads) == 3
        # Packet 1 (JSON)
        assert collected_payloads[0]["sequence_number"] == 1
        assert collected_payloads[0]["pm2_5"] == 10.0
        assert collected_payloads[0]["temperature"] == 25.0

        # Packet 2 (Cycle from ASCII)
        assert collected_payloads[1]["sequence_number"] == 2
        assert collected_payloads[1]["pm1"] == 5.0
        assert collected_payloads[1]["pm2_5"] == 12.0
        assert collected_payloads[1]["pm10"] == 15.0
        assert collected_payloads[1]["temperature"] == 31.0
        assert collected_payloads[1]["humidity"] == 50.0
        assert collected_payloads[1]["pressure"] == 1010.0
        assert collected_payloads[1]["rain_flag"] is True

        # Packet 3 (JSON)
        assert collected_payloads[2]["sequence_number"] == 3
        assert collected_payloads[2]["pm2_5"] == 8.0
        assert collected_payloads[2]["temperature"] == 24.0


class TestFalsyZeroPreservationAndBoundaryValues:
    """Stress-tests preservation of exact 0.0 values across all sensors and edge conditions."""

    def test_all_sensors_at_exact_zero_in_structured_json(self):
        """Ensures exact 0.0 values in JSON are NOT replaced by defaults (e.g. 7.0, 9.0, 29.5)."""
        zero_json = {
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "sequence_number": 0,
            "pm1_0": 0.0,
            "pm2_5": 0.0,
            "pm10": 0.0,
            "temperature_c": 0.0,
            "humidity_pct": 0.0,
            "pressure_hpa": 0.0,
            "gas_resistance_kohm": 0.0,
            "rain_flag": False
        }
        line = f"[JSON_TELEMETRY] {json.dumps(zero_json)}"
        current_data = {}
        payload, is_end = parse_serial_line(line, current_data)

        assert payload is not None
        assert is_end is True
        assert payload["sequence_number"] == 0
        assert payload["pm1"] == 0.0
        assert payload["pm2_5"] == 0.0
        assert payload["pm10"] == 0.0
        assert payload["temperature"] == 0.0
        assert payload["humidity"] == 0.0
        assert payload["pressure"] == 0.0
        assert payload["gas_resistance_kohm"] == 0.0
        assert payload["rain_flag"] is False

    def test_all_sensors_at_exact_zero_in_ascii_stream(self):
        """Ensures exact 0.0 values from ASCII format are preserved in current_data and build_telemetry_payload."""
        current_data = {"pm1": 99.0, "pm2_5": 99.0, "pm10": 99.0, "temp": 99.0, "hum": 99.0, "press": 99.0, "gas": 99.0, "rain": True}

        parse_serial_line("PM1.0: 0.0 | PM2.5: 0.0 | PM10: 0.0", current_data)
        parse_serial_line("Temp: 0.0 C | Humidity: 0.0 % | Pressure: 0.0", current_data)
        parse_serial_line("Gas Resistance: 0.0", current_data)
        parse_serial_line("Rain: NO", current_data)

        payload = build_telemetry_payload(
            0,
            current_data["pm1"], current_data["pm2_5"], current_data["pm10"],
            current_data["temp"], current_data["hum"], current_data["press"],
            current_data["rain"], current_data.get("gas")
        )

        assert payload["sequence_number"] == 0
        assert payload["pm1"] == 0.0
        assert payload["pm2_5"] == 0.0
        assert payload["pm10"] == 0.0
        assert payload["temperature"] == 0.0
        assert payload["humidity"] == 0.0
        assert payload["pressure"] == 0.0
        assert payload["gas_resistance_kohm"] == 0.0
        assert payload["rain_flag"] is False

    def test_negative_temperature_preservation(self):
        """Ensures sub-zero temperatures (e.g. -12.5 C) are correctly parsed."""
        current_data = {}
        line = "Temp: -12.5 C | Humidity: 45.0 % | Pressure: 1025.0"
        payload, is_end = parse_serial_line(line, current_data)
        assert payload is None
        assert current_data["temp"] == -12.5

        payload_obj = build_telemetry_payload(1, 5.0, 10.0, 15.0, current_data["temp"], 45.0, 1025.0, False)
        assert payload_obj["temperature"] == -12.5


class TestDualBrokerTransportFailureImmunity:
    """Stress-tests MQTT publishing when transport errors or exceptions occur on both brokers."""

    @patch("paho.mqtt.client.Client")
    def test_both_brokers_fail_simultaneously_without_crashing_daemon(self, mock_client_cls, capsys):
        """Simulates total network drop where both HiveMQ and EMQX throw socket exceptions.
        Verifies publish handles exceptions gracefully and daemon keeps running.
        """
        mock_hm = MagicMock()
        mock_em = MagicMock()
        mock_hm.publish.side_effect = ConnectionResetError("HiveMQ socket reset")
        mock_em.publish.side_effect = TimeoutError("EMQX publish timeout")

        pub = DualBrokerMqttPublisher()
        pub.clients = {"HiveMQ": mock_hm, "EMQX": mock_em}

        # Should not raise exception
        pub.publish({"device_id": "TEST", "pm2_5": 10.0})

        out = capsys.readouterr().out
        assert "Failed publishing to HiveMQ" in out
        assert "Failed publishing to EMQX" in out

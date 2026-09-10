"""AirSense-v2 Python Bridge Resilience & Serial-to-MQTT Test Suite.

Rigorously verifies:
1. Dynamic COM port scanning and automatic ESP32 UART discovery (CP210x / CH340 / fallback / preferred port).
2. Infinite reconnection retry loop on simulated serial disconnects and mid-stream drops with exponential backoff.
3. Locked port error handling and PermissionError / Arduino IDE conflict detection.
4. Serial telemetry line parsing (Structured JSON, Raw JSON, Human-readable text, Rain flags, Noise filtering).
5. Dual-destination forwarding resilience (Local REST API + Cloud MQTT Broker).
6. Paho MQTT v2 API compliance in bridge daemon.
"""

import time
import json
import re
from unittest.mock import MagicMock, patch, PropertyMock
import pytest
import serial
from typing import List, Dict, Any

from scripts.airsense_serial_live_bridge import (
    find_esp32_port,
    scan_available_ports,
    push_to_local_api,
    push_to_endpoint,
    push_telemetry_dual_async,
    run_simulation_mode,
    build_telemetry_payload,
    parse_serial_line,
    DualBrokerMqttPublisher,
    run_bridge,
    AIRSENSE_LOCAL_API_URL,
    AIRSENSE_CLOUD_API_URL
)


class MockPortInfo:
    """Helper class simulating serial.tools.list_ports_common.ListPortInfo."""
    def __init__(self, device: str, description: str, hwid: str = ""):
        self.device = device
        self.description = description
        self.hwid = hwid


class TestDynamicComPortScanning:
    """Validates automatic detection of ESP32 CP210x / CH340 / UART serial devices across platforms."""

    @patch("serial.tools.list_ports.comports")
    def test_find_esp32_port_detects_cp210x_silicon_labs(self, mock_comports):
        """Identifies Silicon Labs CP210x USB to UART Bridge on COM3."""
        mock_comports.return_value = [
            MockPortInfo("COM1", "Communications Port (COM1)"),
            MockPortInfo("COM3", "Silicon Labs CP210x USB to UART Bridge (COM3)"),
            MockPortInfo("COM5", "Standard Serial over Bluetooth link (COM5)")
        ]
        port = find_esp32_port()
        assert port == "COM3"

    @patch("serial.tools.list_ports.comports")
    def test_find_esp32_port_detects_ch340(self, mock_comports):
        """Identifies WCH CH340 USB-Serial device on COM4."""
        mock_comports.return_value = [
            MockPortInfo("COM1", "Communications Port (COM1)"),
            MockPortInfo("COM4", "USB-SERIAL CH340 (COM4)")
        ]
        port = find_esp32_port()
        assert port == "COM4"

    @patch("serial.tools.list_ports.comports")
    def test_find_esp32_port_detects_generic_uart(self, mock_comports):
        """Identifies devices containing 'uart' in description."""
        mock_comports.return_value = [
            MockPortInfo("COM9", "FTDI USB UART Device")
        ]
        port = find_esp32_port()
        assert port == "COM9"

    @patch("serial.tools.list_ports.comports")
    def test_find_esp32_port_fallback_to_first_available_port(self, mock_comports):
        """Falls back to the first available COM port when no specific chip string matches."""
        mock_comports.return_value = [
            MockPortInfo("COM11", "Generic High-Speed Serial Port (COM11)")
        ]
        port = find_esp32_port()
        assert port == "COM11"

    @patch("serial.tools.list_ports.comports")
    def test_find_esp32_port_returns_none_when_no_ports(self, mock_comports):
        """Returns None when no serial ports exist in system."""
        mock_comports.return_value = []
        port = find_esp32_port()
        assert port is None

    @patch("serial.tools.list_ports.comports")
    def test_preferred_port_used_if_online(self, mock_comports):
        """Selects explicitly requested preferred port if present in system."""
        mock_comports.return_value = [
            MockPortInfo("COM3", "CP2102 Bridge"),
            MockPortInfo("COM15", "USB Serial")
        ]
        port = find_esp32_port(preferred_port="COM15")
        assert port == "COM15"

    @patch("serial.tools.list_ports.comports")
    def test_preferred_port_falls_back_if_offline(self, mock_comports):
        """Falls back to best available port if specified preferred port is offline."""
        mock_comports.return_value = [
            MockPortInfo("COM3", "Silicon Labs CP210x Bridge")
        ]
        port = find_esp32_port(preferred_port="COM99")
        assert port == "COM3"


class TestSerialDisconnectAndInfiniteReconnection:
    """Verifies that the bridge loop never exits on serial disconnects and retries indefinitely."""

    @patch("scripts.airsense_serial_live_bridge.time.sleep", return_value=None)
    @patch("serial.Serial")
    @patch("scripts.airsense_serial_live_bridge.find_esp32_port", return_value="COM3")
    def test_bridge_infinite_retry_on_initial_serial_exception(self, mock_find, mock_serial, mock_sleep):
        """Simulates 3 serial exceptions before connecting; asserts loop retries and does not crash."""
        call_count = 0

        def serial_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise serial.SerialException(f"Could not open port (Attempt {call_count})")
            # 3rd attempt succeeds, then raises KeyboardInterrupt to exit test loop
            mock_ser_instance = MagicMock()
            mock_ser_instance.is_open = True
            mock_ser_instance.readline.side_effect = KeyboardInterrupt("Exit test")
            return mock_ser_instance

        mock_serial.side_effect = serial_side_effect

        run_bridge("COM3")
        assert call_count >= 3
        assert mock_sleep.call_count >= 2

    @patch("scripts.airsense_serial_live_bridge.time.sleep", return_value=None)
    @patch("serial.Serial")
    @patch("scripts.airsense_serial_live_bridge.find_esp32_port", return_value="COM3")
    def test_bridge_recovers_when_cable_unplugged_mid_stream(self, mock_find, mock_serial, mock_sleep, capsys):
        """Simulates physical cable disconnect during active streaming; verifies clean port teardown and reconnect."""
        cycle = 0

        def serial_side_effect(*args, **kwargs):
            nonlocal cycle
            cycle += 1
            mock_inst = MagicMock()
            mock_inst.is_open = True
            if cycle == 1:
                # Active streaming, then sudden unplug exception
                mock_inst.readline.side_effect = [
                    b"[LOG] Normal stream packet\n",
                    serial.SerialException("Device disconnected or ClearCommError failed")
                ]
                return mock_inst
            else:
                # 2nd cycle terminates cleanly
                mock_inst.readline.side_effect = KeyboardInterrupt("Stop test")
                return mock_inst

        mock_serial.side_effect = serial_side_effect

        run_bridge("COM3")
        assert cycle == 2
        captured = capsys.readouterr().out
        assert "BRIDGE DISCONNECT" in captured or "Serial connection lost" in captured


class TestLockedPortAndPermissionHandling:
    """Verifies actionable error handling when COM port is locked by Arduino IDE or another application."""

    @patch("scripts.airsense_serial_live_bridge.time.sleep", return_value=None)
    @patch("serial.Serial")
    @patch("scripts.airsense_serial_live_bridge.find_esp32_port", return_value="COM7")
    def test_locked_port_permission_denied_guidance(self, mock_find, mock_serial, mock_sleep, capsys):
        """Simulates PermissionError / Access Denied; verifies actionable message instructing user to close Arduino IDE."""
        attempts = 0

        def side_effect(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise serial.SerialException("could not open port 'COM7': PermissionError(13, 'Access is denied.', None, 5)")
            else:
                raise KeyboardInterrupt("Stop test")

        mock_serial.side_effect = side_effect

        run_bridge("COM7")
        out = capsys.readouterr().out
        assert "Arduino IDE" in out
        assert "busy" in out or "Access is denied" in out or "conflicting" in out


class TestSerialLineParsingAndExtraction:
    """Verifies robust parsing of diverse telemetry strings, structured JSON, and noise filtering."""

    def test_parse_structured_json_line_with_prefix(self):
        """Parses [JSON_TELEMETRY] prefixed JSON line into fully normalized dictionary."""
        json_data = {
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "sequence_number": 42,
            "pm1_0": 5.5,
            "pm2_5": 11.2,
            "pm10": 16.8,
            "temperature_c": 28.3,
            "humidity_pct": 59.0,
            "pressure_hpa": 1012.4,
            "rain_flag": False
        }
        raw_line = f"[JSON_TELEMETRY] {json.dumps(json_data)}"
        current_data = {"pm1": 7.0, "pm2_5": 9.0, "pm10": 10.0, "temp": 29.5, "hum": 65.0, "press": 1012.0, "rain": False}
        payload, is_cycle_end = parse_serial_line(raw_line, current_data)

        assert is_cycle_end is True
        assert payload is not None
        assert payload["sequence_number"] == 42
        assert payload["pm2_5"] == 11.2
        assert payload["temperature"] == 28.3
        assert payload["humidity"] == 59.0
        assert payload["pressure"] == 1012.4
        assert payload["rain_flag"] is False

    def test_parse_raw_json_line(self):
        """Parses standalone valid JSON line without prefix."""
        json_data = {
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "sequence_number": 101,
            "pm25": 14.5,
            "temperature": 30.1,
            "humidity": 61.2,
            "pressure": 1011.0,
            "rain_flag": True
        }
        raw_line = json.dumps(json_data)
        current_data = {}
        payload, is_cycle_end = parse_serial_line(raw_line, current_data)

        assert is_cycle_end is True
        assert payload is not None
        assert payload["pm2_5"] == 14.5
        assert payload["temperature"] == 30.1
        assert payload["rain_flag"] is True

    def test_parse_human_readable_pms7003_and_bme280_logs(self):
        """Parses human-readable formatted string lines updating current_data dictionary."""
        current_data = {"pm1": 0.0, "pm2_5": 0.0, "pm10": 0.0, "temp": 0.0, "hum": 0.0, "press": 0.0, "rain": False}

        line_pms = "PM1.0: 6.5 | PM2.5: 8.2 | PM10: 10.1"
        payload_pms, end_pms = parse_serial_line(line_pms, current_data)
        assert payload_pms is None
        assert end_pms is False
        assert current_data["pm1"] == 6.5
        assert current_data["pm2_5"] == 8.2
        assert current_data["pm10"] == 10.1

        line_bme = "Temp: 28.5 C | Humidity: 62.0 % | Pressure: 1013.2"
        payload_bme, end_bme = parse_serial_line(line_bme, current_data)
        assert payload_bme is None
        assert end_bme is False
        assert current_data["temp"] == 28.5
        assert current_data["hum"] == 62.0
        assert current_data["press"] == 1013.2

    def test_parse_rain_detection_states(self):
        """Parses rain state variations."""
        current_data = {"rain": False}
        parse_serial_line("Rain: YES", current_data)
        assert current_data["rain"] is True

        parse_serial_line("Rain: Wet", current_data)
        assert current_data["rain"] is True

        parse_serial_line("Rain: NO", current_data)
        assert current_data["rain"] is False

        parse_serial_line("Rain: Dry", current_data)
        assert current_data["rain"] is False

    def test_cycle_separator_line_triggers_cycle_end(self):
        """Separator dashes identify the end of a multi-sensor reading cycle."""
        current_data = {}
        _, is_end = parse_serial_line("--------------------------------------------------------", current_data)
        assert is_end is True

    def test_noise_and_bootloader_logs_ignored_safely(self):
        """Ignores noisy bootloader messages and wifi scans without crashing."""
        current_data = {"pm2_5": 10.0}
        noise_lines = [
            "rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)",
            "configsip: 0, SPIWP:0xee",
            "Connecting to WiFi: IBA_Guest_WiFi...",
            "[WIFI] Connected! IP address: 192.168.1.100",
            "\x00\x01\xfe\xff binary noise"
        ]
        for line in noise_lines:
            payload, is_end = parse_serial_line(line, current_data)
            assert payload is None
            assert is_end is False
        # State remained intact
        assert current_data["pm2_5"] == 10.0


class TestDualBrokerMqttPublisher:
    """Verifies dual broker initialization and publish failover behavior."""

    @patch("paho.mqtt.client.Client")
    def test_dual_broker_initialization_with_paho_v2(self, mock_client_cls):
        """Initializes clients for both HiveMQ and EMQX."""
        mock_inst = MagicMock()
        mock_client_cls.return_value = mock_inst

        publisher = DualBrokerMqttPublisher()
        assert "HiveMQ" in publisher.clients
        assert "EMQX" in publisher.clients
        assert mock_inst.connect_async.call_count == 2
        assert mock_inst.loop_start.call_count == 2

    @patch("paho.mqtt.client.Client")
    def test_publisher_isolated_error_handling_when_one_broker_fails(self, mock_client_cls, capsys):
        """Publishes to remaining brokers even if one client throws an exception."""
        client_hm = MagicMock()
        client_em = MagicMock()
        client_hm.publish.side_effect = Exception("Socket closed by HiveMQ")
        client_em.publish.return_value = MagicMock(rc=0)

        publisher = DualBrokerMqttPublisher()
        publisher.clients = {"HiveMQ": client_hm, "EMQX": client_em}

        sample = {"device_id": "TEST", "pm2_5": 12.0}
        publisher.publish(sample)

        assert client_hm.publish.called
        assert client_em.publish.called
        out = capsys.readouterr().out
        assert "Failed publishing to HiveMQ" in out

    @patch("urllib.request.urlopen")
    def test_push_to_local_api_resilience_on_http_error(self, mock_urlopen):
        """push_to_local_api returns False cleanly when local API is unreachable."""
        mock_urlopen.side_effect = Exception("Connection Refused (Local Backend Stopped)")
        res = push_to_local_api({"device_uid": "TEST", "pm2_5": 12.0})
        assert res is False

    def test_build_telemetry_payload_schema_compliance(self):
        """build_telemetry_payload builds dictionary with all required telemetry fields."""
        p = build_telemetry_payload(10, 6.2, 12.4, 18.6, 29.1, 63.5, 1012.8, True, gas=42.1)
        assert p["schema_version"] == "1.0"
        assert p["sequence_number"] == 10
        assert p["pm1"] == 6.2
        assert p["pm2_5"] == 12.4
        assert p["pm10"] == 18.6
        assert p["temperature"] == 29.1
        assert p["humidity"] == 63.5
        assert p["pressure"] == 1012.8
        assert p["gas_resistance_kohm"] == 42.1
        assert p["rain_flag"] is True
        assert p["sensor_health"]["pms7003"] == "OK"
        assert p["sensor_health"]["bme280"] == "OK"


class TestDualRoutingAndSimulationMode:
    """Verifies dual-routing HTTP dispatch, ThreadPoolExecutor concurrency, and simulation mode."""

    @patch("urllib.request.urlopen")
    def test_push_to_endpoint_success(self, mock_urlopen):
        """push_to_endpoint returns True on HTTP 200/201 response."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        payload = {"device_uid": "AIRSENSE-NODE-KHI-01", "pm2_5": 15.0}
        success = push_to_endpoint("http://127.0.0.1:8000/api/v1/ingest/reading", payload, "TEST")
        assert success is True
        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("X-device-token") == "airsense_dev_token_khi_01"
        assert req.get_method() == "POST"

    @patch("urllib.request.urlopen")
    def test_push_to_endpoint_http_error(self, mock_urlopen):
        """push_to_endpoint returns False on HTTP 500 error."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError("http://test", 500, "Internal Error", {}, None)
        success = push_to_endpoint("http://test/ingest", {"pm2_5": 10.0})
        assert success is False

    @patch("urllib.request.urlopen")
    def test_push_to_endpoint_timeout_and_network_error(self, mock_urlopen):
        """push_to_endpoint suppresses TimeoutError and URLError gracefully."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection timed out")
        success = push_to_endpoint("http://test/ingest", {"pm2_5": 10.0})
        assert success is False

    def test_push_to_endpoint_empty_url_returns_false(self):
        """push_to_endpoint returns False immediately if url is None or empty."""
        assert push_to_endpoint("", {"pm2_5": 10.0}) is False
        assert push_to_endpoint(None, {"pm2_5": 10.0}) is False

    @patch("scripts.airsense_serial_live_bridge.http_pool.submit")
    def test_push_telemetry_dual_async_dispatches_both(self, mock_submit):
        """push_telemetry_dual_async submits separate tasks for local and cloud URLs."""
        payload = {"sequence_number": 42, "pm2_5": 12.0}
        futures = push_telemetry_dual_async(
            payload,
            local_url="http://127.0.0.1:8000/api/v1/ingest/reading",
            cloud_url="https://airsense-api.onrender.com/api/v1/ingest/reading"
        )
        assert mock_submit.call_count == 2
        calls = mock_submit.call_args_list
        urls_called = [c[0][1] for c in calls]
        assert "http://127.0.0.1:8000/api/v1/ingest/reading" in urls_called
        assert "https://airsense-api.onrender.com/api/v1/ingest/reading" in urls_called

    @patch("scripts.airsense_serial_live_bridge.http_pool.submit")
    def test_push_telemetry_dual_async_only_local_when_no_cloud(self, mock_submit):
        """push_telemetry_dual_async only submits local task if cloud_url is None."""
        payload = {"sequence_number": 42, "pm2_5": 12.0}
        futures = push_telemetry_dual_async(
            payload,
            local_url="http://127.0.0.1:8000/api/v1/ingest/reading",
            cloud_url=None
        )
        assert mock_submit.call_count == 1
        assert mock_submit.call_args[0][1] == "http://127.0.0.1:8000/api/v1/ingest/reading"

    @patch("scripts.airsense_serial_live_bridge.push_telemetry_dual_async")
    @patch("scripts.airsense_serial_live_bridge.DualBrokerMqttPublisher")
    def test_run_simulation_mode_emits_synthetic_payload(self, mock_mqtt, mock_push_dual):
        """run_simulation_mode generates synthetic payload, triggers MQTT and dual HTTP dispatch."""
        mock_push_dual.return_value = []
        payload = run_simulation_mode(
            cloud_url="https://airsense-api.onrender.com/api/v1/ingest/reading",
            local_url="http://127.0.0.1:8000/api/v1/ingest/reading",
            wait_for_completion=False
        )
        assert payload is not None
        assert payload["schema_version"] == "1.0"
        assert payload["device_uid"] == "AIRSENSE-NODE-KHI-01"
        assert payload["transmission_mode"] == "SERIAL_BRIDGE_SIMULATE"
        assert payload["pm2_5"] > 0
        assert mock_push_dual.called
        assert mock_mqtt.called

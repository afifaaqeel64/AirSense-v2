"""AirSense-v2 Challenger 2: Adversarial Stress Test Suite for Serial Bridge.

Empirically tests and challenges:
1. Serial port hot-plugging simulation (USB port disconnects, COM re-enumeration, dynamic hopping).
2. Port locked / PermissionError simulation (Arduino IDE / serial port contention).
3. Corrupted / malformed incoming serial lines (garbage bytes, partial JSON, truncated ASCII, fuzzed lengths).
4. Falsy zero values (pm2_5: 0.0, temperature: 0.0, rain_flag: False) integrity and non-truncation.
5. High-throughput continuous burst streaming and mock daemon lifecycle under adverse faults.
"""

import time
import json
import random
import re
from unittest.mock import MagicMock, patch, PropertyMock, call
import pytest
import serial
from typing import List, Dict, Any

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


# =============================================================================
# 1. SERIAL PORT HOT-PLUGGING & COM-HOPPING HARNESS
# =============================================================================

class TestHotPluggingAndComHoppingHarness:
    """Stress-tests serial port disappearance, dynamic COM-hopping, and reconnection."""

    @patch("serial.tools.list_ports.comports")
    def test_hot_plug_com_port_hopping_simulation(self, mock_comports):
        """Simulates USB cable unplugged from COM3 and re-enumerated on COM7 (Silicon Labs CP210x)."""
        # Step 1: Initial state -> COM1 is standard communications port, COM3 is CP210x bridge
        mock_comports.return_value = [
            MockPortInfo("COM1", "Communications Port (COM1)"),
            MockPortInfo("COM3", "Silicon Labs CP210x USB to UART Bridge (COM3)")
        ]
        port1 = find_esp32_port()
        assert port1 == "COM3"

        # Step 2: Cable unplugged -> Only COM1 remains, bridge falls back to COM1
        mock_comports.return_value = [
            MockPortInfo("COM1", "Communications Port (COM1)")
        ]
        port2 = find_esp32_port()
        assert port2 == "COM1"

        # Step 3: All ports gone
        mock_comports.return_value = []
        port3 = find_esp32_port()
        assert port3 is None

        # Step 4: Plugged into different USB hub -> Enumerates as COM7 (CH340)
        mock_comports.return_value = [
            MockPortInfo("COM1", "Communications Port (COM1)"),
            MockPortInfo("COM7", "USB-SERIAL CH340 (COM7)")
        ]
        port4 = find_esp32_port()
        assert port4 == "COM7"

    @patch("scripts.airsense_serial_live_bridge.time.sleep", return_value=None)
    @patch("serial.Serial")
    @patch("serial.tools.list_ports.comports")
    def test_bridge_daemon_survives_rapid_hot_plug_cycling(self, mock_comports, mock_serial, mock_sleep, capsys):
        """Simulates rapid hot-plug cycles with port changes (COM3 -> None -> COM4 -> COM9)."""
        # Scenario progression of available ports across scan calls
        port_scan_sequence = [
            [MockPortInfo("COM1", "Communications Port"), MockPortInfo("COM3", "Silicon Labs CP2102")],  # Scan 1: COM3
            [],                                                                                           # Scan 2: Disconnected (None)
            [MockPortInfo("COM1", "Communications Port"), MockPortInfo("COM4", "USB-Serial CH340")],     # Scan 3: COM4
            [MockPortInfo("COM1", "Communications Port"), MockPortInfo("COM9", "FTDI UART Device")]      # Scan 4: COM9
        ]
        
        scan_idx = 0
        opened_ports = []

        def mock_comports_side_effect():
            nonlocal scan_idx
            idx = min(scan_idx, len(port_scan_sequence) - 1)
            res = port_scan_sequence[idx]
            scan_idx += 1
            return res

        mock_comports.side_effect = mock_comports_side_effect

        def mock_serial_constructor(port, *args, **kwargs):
            opened_ports.append(port)
            mock_inst = MagicMock()
            mock_inst.is_open = True
            
            if port == "COM3":
                mock_inst.readline.side_effect = [
                    b'{"sequence_number": 1, "pm2_5": 12.0, "temperature": 28.0}\n',
                    serial.SerialException("ClearCommError failed (device un-plugged)")
                ]
                return mock_inst
            elif port == "COM4":
                mock_inst.readline.side_effect = [
                    b'{"sequence_number": 2, "pm2_5": 14.0, "temperature": 29.0}\n',
                    serial.SerialException("WriteFile failed: device removed")
                ]
                return mock_inst
            else:
                # COM9 connects and terminates test cleanly
                mock_inst.readline.side_effect = KeyboardInterrupt("Test complete")
                return mock_inst

        mock_serial.side_effect = mock_serial_constructor

        # Run bridge with auto port detection
        run_bridge(preferred_port=None)

        # Assert bridge opened COM3, handled disconnect/None scan, then COM4, then COM9 seamlessly
        assert "COM3" in opened_ports
        assert "COM4" in opened_ports
        assert "COM9" in opened_ports
        assert mock_sleep.call_count >= 2

    @patch("serial.tools.list_ports.comports")
    def test_preferred_port_dynamic_hot_plug_reacquisition(self, mock_comports):
        """Validates that preferred port (e.g. COM5) is re-acquired once plugged back in."""
        # 1. Preferred COM5 offline, COM2 online -> Uses COM2
        mock_comports.return_value = [MockPortInfo("COM2", "USB Serial")]
        assert find_esp32_port(preferred_port="COM5") == "COM2"

        # 2. Preferred COM5 comes online -> Prioritizes COM5
        mock_comports.return_value = [
            MockPortInfo("COM2", "USB Serial"),
            MockPortInfo("COM5", "Silicon Labs CP210x Bridge")
        ]
        assert find_esp32_port(preferred_port="COM5") == "COM5"


# =============================================================================
# 2. PORT LOCKED & PERMISSION ERROR SIMULATION
# =============================================================================

class TestPortLockedAndPermissionErrorHarness:
    """Stress-tests port contention, PermissionError (WinError 5 / WinError 32), and recovery."""

    @patch("scripts.airsense_serial_live_bridge.time.sleep", return_value=None)
    @patch("serial.Serial")
    @patch("scripts.airsense_serial_live_bridge.find_esp32_port", return_value="COM3")
    def test_permission_error_locked_by_arduino_ide_recovery(self, mock_find, mock_serial, mock_sleep, capsys):
        """Simulates Arduino IDE holding lock for 4 attempts, then user closes IDE and bridge acquires port."""
        attempt = 0

        def serial_lock_side_effect(*args, **kwargs):
            nonlocal attempt
            attempt += 1
            if attempt <= 4:
                raise serial.SerialException(
                    "could not open port 'COM3': PermissionError(13, 'Access is denied.', None, 5)"
                )
            mock_inst = MagicMock()
            mock_inst.is_open = True
            mock_inst.readline.side_effect = KeyboardInterrupt("Port unlocked and test finished")
            return mock_inst

        mock_serial.side_effect = serial_lock_side_effect

        run_bridge("COM3")

        assert attempt == 5
        assert mock_sleep.call_count == 4
        out = capsys.readouterr().out
        assert "Arduino IDE" in out
        assert "Retrying in 2s" in out or "busy" in out

    @patch("scripts.airsense_serial_live_bridge.time.sleep", return_value=None)
    @patch("serial.Serial")
    @patch("scripts.airsense_serial_live_bridge.find_esp32_port", return_value="COM3")
    def test_sharing_violation_winerror_32_handling(self, mock_find, mock_serial, mock_sleep, capsys):
        """Simulates Windows error 32 (Sharing Violation: process cannot access file used by another process)."""
        call_count = 0

        def winerror_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise serial.SerialException(
                    "could not open port 'COM3': WindowsError(32, 'The process cannot access the file because it is being used by another process.')"
                )
            raise KeyboardInterrupt("Stop test")

        mock_serial.side_effect = winerror_side_effect

        run_bridge("COM3")
        assert call_count >= 1
        out = capsys.readouterr().out
        assert "BRIDGE DISCONNECT" in out or "Serial connection lost" in out or "BRIDGE RECOVER" in out


# =============================================================================
# 3. CORRUPTED & MALFORMED INCOMING SERIAL DATA HARNESS
# =============================================================================

class TestCorruptedAndMalformedSerialHarness:
    """Fuzzes and stress-tests incoming serial line parsing against malformed streams."""

    @pytest.mark.parametrize("corrupt_line", [
        # Binary garbage
        "\x00\x01\x02\xfe\xff\x80\xc3\x28\x99",
        # Truncated JSON
        '{"device_uid": "AIRSENSE-NODE-01", "pm2_5": 14.5, "temp',
        'f_khi": 12.5, "rain_flag": false}',
        '[JSON_TELEMETRY] {"pm2_5": 10.2, "temperature": ',
        '[JSON_TELEMETRY] {bad_json: true, "pm2_5": 10.0}',
        # Incomplete brackets / syntax
        '{"sequence_number": 5, "pm2_5": [12.0,',
        '{"sensor_health": {"pms7003": "OK", "bme280":',
        '{"pm2_5": NaN, "temperature": undefined}',
        # Incomplete ASCII logs
        'PM1.0: 6.5 | PM2.5: | PM10:',
        'Temp: C | Hum: % | Press: ',
        'Gas Resistance: invalid_num kohm',
        # Empty or single punctuation
        '{', '}', '[]', ':', ',', '""',
        # Non-telemetry logs
        '[BOOT] ESP32-WROOM-32 booting from flash (4MB)...',
        'ets Jun 8 2016 00:22:57,rst:0x1 (POWERON_RESET),boot:0x13',
        'Connecting to WiFi SSID: Campus_IoT_Net (Attempt 3/10)...',
        'IP Address: 192.168.10.45 Gateway: 192.168.10.1',
        'WiFi connection dropped. Reconnecting...',
    ])
    def test_malformed_and_noise_lines_handled_without_crash(self, corrupt_line):
        """Ensures corrupted, truncated, and debug strings return None without raising unhandled exceptions."""
        current_data = {"pm1": 7.0, "pm2_5": 9.0, "pm10": 10.0, "temp": 29.5, "hum": 65.0, "press": 1012.0, "rain": False}
        payload, is_cycle_end = parse_serial_line(corrupt_line, current_data)
        
        # Must not produce a malformed payload
        assert payload is None
        # Internal baseline state must remain valid
        assert current_data["pm2_5"] == 9.0
        assert current_data["temp"] == 29.5

    def test_extreme_line_length_fuzzing(self):
        """Fuzzes parser with 50,000-character junk strings to verify memory safety and regex bounding."""
        junk_50k = "PM2.5: " + ("9" * 50000) + " | Temp: " + ("A" * 10000)
        current_data = {"pm2_5": 9.0}
        
        start = time.perf_counter()
        payload, is_end = parse_serial_line(junk_50k, current_data)
        elapsed = time.perf_counter() - start
        
        # Must finish in < 50ms without regex catastrophic backtracking (ReDoS)
        assert elapsed < 0.05
        assert payload is None

    def test_interleaved_garbage_and_valid_telemetry_stream(self):
        """Simulates realistic dirty UART stream: garbage -> ASCII -> noise -> valid JSON -> separator."""
        stream = [
            "\x00\xff\xfe ESP32 Resetting...",
            "PM1.0: 5.8 | PM2.5: 11.4 | PM10: 16.2",
            "[DEBUG] Free heap: 184520 bytes",
            "Temp: 30.5 C | Humidity: 58.0 % | Pressure: 1011.8",
            "Gas Resistance: 44.5",
            "Rain: YES",
            "--------------------------------------------------------"
        ]
        
        current_data = {"pm1": 0.0, "pm2_5": 0.0, "pm10": 0.0, "temp": 0.0, "hum": 0.0, "press": 0.0, "rain": False}
        
        for idx, line in enumerate(stream):
            payload, is_end = parse_serial_line(line, current_data)
            if idx < len(stream) - 1:
                assert is_end is False
            else:
                # Last line is separator
                assert is_end is True

        # Assert data extracted across dirty stream
        assert current_data["pm1"] == 5.8
        assert current_data["pm2_5"] == 11.4
        assert current_data["pm10"] == 16.2
        assert current_data["temp"] == 30.5
        assert current_data["hum"] == 58.0
        assert current_data["press"] == 1011.8
        assert current_data["gas"] == 44.5
        assert current_data["rain"] is True

        # Now build cycle payload
        payload = build_telemetry_payload(
            seq=10,
            pm1=current_data["pm1"],
            pm25=current_data["pm2_5"],
            pm10=current_data["pm10"],
            temp=current_data["temp"],
            hum=current_data["hum"],
            press=current_data["press"],
            rain=current_data["rain"],
            gas=current_data["gas"]
        )
        assert payload["sequence_number"] == 10
        assert payload["pm2_5"] == 11.4
        assert payload["temperature"] == 30.5
        assert payload["rain_flag"] is True


# =============================================================================
# 4. FALSY ZERO VALUES & EXACT 0.0 PRESERVATION HARNESS
# =============================================================================

class TestFalsyZeroValuesIntegrityHarness:
    """Verifies that 0.0 numeric values and False booleans are never dropped or overwritten with defaults."""

    def test_structured_json_preserves_exact_zero_values(self):
        """Verifies JSON payload with pm1=0.0, pm2_5=0.0, pm10=0.0, temp=0.0, hum=0.0, press=0.0, rain_flag=False."""
        raw_json = json.dumps({
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "sequence_number": 1,
            "pm1": 0.0,
            "pm2_5": 0.0,
            "pm10": 0.0,
            "temperature": 0.0,
            "humidity": 0.0,
            "pressure": 0.0,
            "rain_flag": False
        })
        line = f"[JSON_TELEMETRY] {raw_json}"
        current_data = {}
        payload, is_end = parse_serial_line(line, current_data)

        assert is_end is True
        assert payload is not None
        assert payload["pm1"] == 0.0
        assert payload["pm2_5"] == 0.0
        assert payload["pm10"] == 0.0
        assert payload["temperature"] == 0.0
        assert payload["humidity"] == 0.0
        assert payload["pressure"] == 0.0
        assert payload["rain_flag"] is False

    def test_structured_json_with_field_aliases_preserves_zeroes(self):
        """Verifies JSON payload using aliases pm25=0.0, pm1_0=0.0, temperature_c=0.0, humidity_pct=0.0, pressure_hpa=0.0."""
        raw_json = json.dumps({
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "sequence_number": 2,
            "pm1_0": 0.0,
            "pm25": 0.0,
            "pm10": 0.0,
            "temperature_c": 0.0,
            "humidity_pct": 0.0,
            "pressure_hpa": 0.0,
            "rain_flag": False
        })
        line = f"[JSON_TELEMETRY] {raw_json}"
        current_data = {}
        payload, is_end = parse_serial_line(line, current_data)

        assert is_end is True
        assert payload is not None
        assert payload["pm1"] == 0.0
        assert payload["pm2_5"] == 0.0
        assert payload["pm10"] == 0.0
        assert payload["temperature"] == 0.0
        assert payload["humidity"] == 0.0
        assert payload["pressure"] == 0.0
        assert payload["rain_flag"] is False

    def test_ascii_log_parser_preserves_zero_readings(self):
        """Verifies ASCII line parser accurately extracts 0.0 from PMS7003 and BME280 formatted strings."""
        current_data = {"pm1": 9.9, "pm2_5": 9.9, "pm10": 9.9, "temp": 9.9, "hum": 9.9, "press": 9.9, "rain": True}

        line_pms = "PM1.0: 0.0 | PM2.5: 0.0 | PM10: 0.0"
        parse_serial_line(line_pms, current_data)
        assert current_data["pm1"] == 0.0
        assert current_data["pm2_5"] == 0.0
        assert current_data["pm10"] == 0.0

        line_bme = "Temp: 0.0 C | Hum: 0.0 % | Press: 0.0"
        parse_serial_line(line_bme, current_data)
        assert current_data["temp"] == 0.0
        assert current_data["hum"] == 0.0
        assert current_data["press"] == 0.0

        line_rain = "Rain: NO"
        parse_serial_line(line_rain, current_data)
        assert current_data["rain"] is False

        # Build payload
        payload = build_telemetry_payload(
            seq=5,
            pm1=current_data["pm1"],
            pm25=current_data["pm2_5"],
            pm10=current_data["pm10"],
            temp=current_data["temp"],
            hum=current_data["hum"],
            press=current_data["press"],
            rain=current_data["rain"]
        )
        assert payload["pm1"] == 0.0
        assert payload["pm2_5"] == 0.0
        assert payload["pm10"] == 0.0
        assert payload["temperature"] == 0.0
        assert payload["humidity"] == 0.0
        assert payload["pressure"] == 0.0
        assert payload["rain_flag"] is False

    def test_build_telemetry_payload_falsy_zero_vs_none_distinction(self):
        """Verifies clear distinction between None (falls back to default) and 0.0 (preserved)."""
        # When values are 0.0 -> Preserved
        p_zero = build_telemetry_payload(1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False)
        assert p_zero["pm1"] == 0.0
        assert p_zero["pm2_5"] == 0.0
        assert p_zero["pm10"] == 0.0
        assert p_zero["temperature"] == 0.0
        assert p_zero["humidity"] == 0.0
        assert p_zero["pressure"] == 0.0
        assert p_zero["rain_flag"] is False

        # When values are None -> Falls back to safe nominal defaults
        p_none = build_telemetry_payload(1, None, None, None, None, None, None, False)
        assert p_none["pm1"] == 7.0
        assert p_none["pm2_5"] == 9.0
        assert p_none["pm10"] == 10.0
        assert p_none["temperature"] == 29.5
        assert p_none["humidity"] == 65.0
        assert p_none["pressure"] == 1012.0
        assert p_none["rain_flag"] is False


# =============================================================================
# 5. DUAL BROKER MQTT RESILIENCE & PUBLISH EXCEPTION ISOLATION
# =============================================================================

class TestDualBrokerPublishIsolationHarness:
    """Stress-tests dual MQTT broker publisher when network or broker exceptions occur."""

    @patch("paho.mqtt.client.Client")
    def test_dual_broker_publish_stress_under_partial_broker_failure(self, mock_client_cls):
        """Simulates 50 rapid telemetry publish calls while HiveMQ throws socket errors and EMQX succeeds."""
        mock_hm = MagicMock()
        mock_em = MagicMock()

        # HiveMQ throws socket disconnected exception
        mock_hm.publish.side_effect = ConnectionResetError("HiveMQ TCP connection reset by peer")
        # EMQX operates normally
        mock_em.publish.return_value = MagicMock(rc=0)

        publisher = DualBrokerMqttPublisher()
        publisher.clients = {"HiveMQ": mock_hm, "EMQX": mock_em}

        for i in range(50):
            sample = build_telemetry_payload(i, 8.5, 12.0, 18.0, 29.0, 60.0, 1012.0, False)
            # Must not raise unhandled exception
            publisher.publish(sample)

        assert mock_hm.publish.call_count == 50
        # EMQX called for both primary and fallback topic = 100 calls
        assert mock_em.publish.call_count == 100

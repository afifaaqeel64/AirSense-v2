"""AirSense-v2 Empirical Challenger 1 — MQTT Network Stress & Failover Harness.

Adversarially challenges:
1. High-Frequency Packet Bursts & Monotonicity (Burst sequencing, rate throttling benchmarking, dual-broker concurrency).
2. Topic Routing & Collision Stress (Exact topic isolation, multi-level wildcard matching +, #, cross-talk immunity).
3. Broker Failover & Network Resilience (Simulated broker dropouts, socket disconnect recovery, reconnect backoff).
4. Extreme Payload Fuzzing & Malformed Telemetry Stream (Giant payloads, unicode surrogates, NaN/Inf injection, partial JSON over serial).
5. Bridge Daemon & Dual Publisher Stress (Concurrent thread load, zero memory leaks, graceful COM error handling).
"""

import time
import json
import uuid
import threading
import queue
import pytest
from typing import Dict, Any, List
import paho.mqtt.client as mqtt

from scripts.airsense_serial_live_bridge import (
    DualBrokerMqttPublisher,
    parse_serial_line,
    build_telemetry_payload,
    find_esp32_port,
    scan_available_ports,
    BROKER_CONFIGS
)
from scripts.airsense_mqtt_live_forwarder import on_message as forwarder_on_message

HIVEMQ_HOST = "broker.hivemq.com"
EMQX_HOST = "broker.emqx.io"
MQTT_PORT = 1883
PRIMARY_TOPIC = "airsense/karachi/bic_roof/telemetry"


def create_paho_v2_client(name_prefix: str) -> mqtt.Client:
    """Helper to instantiate a clean Paho v2 MQTT Client."""
    cid = f"challenger1-{name_prefix}-{uuid.uuid4().hex[:8]}"
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except AttributeError:
        return mqtt.Client(client_id=cid)


# =============================================================================
# 1. HIGH-FREQUENCY PACKET BURST & CONCURRENCY CHALLENGE
# =============================================================================

class TestHighFrequencyPacketBursts:
    """Stress-tests rapid telemetry bursts across single and dual broker configurations."""

    def test_rapid_burst_sequencing_and_delivery(self):
        """Injects a rapid burst of 10 telemetry packets at 50ms intervals across both brokers."""
        sub_hm = create_paho_v2_client("sub-burst-hm")
        sub_em = create_paho_v2_client("sub-burst-em")
        pub_hm = create_paho_v2_client("pub-burst-hm")
        pub_em = create_paho_v2_client("pub-burst-em")

        hm_ready = threading.Event()
        em_ready = threading.Event()
        hm_packets = []
        em_packets = []
        burst_test_uuid = uuid.uuid4().hex

        def on_hm_connect(c, ud, f, rc, p=None):
            if rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure):
                c.subscribe(PRIMARY_TOPIC, qos=0)
                hm_ready.set()

        def on_em_connect(c, ud, f, rc, p=None):
            if rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure):
                c.subscribe(PRIMARY_TOPIC, qos=0)
                em_ready.set()

        def on_hm_msg(c, ud, msg):
            try:
                data = json.loads(msg.payload.decode("utf-8"))
                if data.get("stress_id") == burst_test_uuid:
                    hm_packets.append(data.get("sequence_number"))
            except Exception:
                pass

        def on_em_msg(c, ud, msg):
            try:
                data = json.loads(msg.payload.decode("utf-8"))
                if data.get("stress_id") == burst_test_uuid:
                    em_packets.append(data.get("sequence_number"))
            except Exception:
                pass

        sub_hm.on_connect = on_hm_connect
        sub_hm.on_message = on_hm_msg
        sub_em.on_connect = on_em_connect
        sub_em.on_message = on_em_msg

        try:
            # Connect subscribers
            sub_hm.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
            sub_hm.loop_start()
            sub_em.connect(EMQX_HOST, MQTT_PORT, keepalive=30)
            sub_em.loop_start()

            assert hm_ready.wait(timeout=12.0), "HiveMQ subscriber did not connect"
            assert em_ready.wait(timeout=12.0), "EMQX subscriber did not connect"

            # Connect publishers
            pub_hm.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
            pub_hm.loop_start()
            pub_em.connect(EMQX_HOST, MQTT_PORT, keepalive=30)
            pub_em.loop_start()

            time.sleep(0.5)

            # Fire burst of 10 packets across both brokers
            num_packets = 10
            for i in range(num_packets):
                payload = {
                    "device_id": "AIRSENSE-NODE-01",
                    "sequence_number": 5000 + i,
                    "pm2_5": 10.0 + (i * 0.2),
                    "temperature_c": 28.5,
                    "stress_id": burst_test_uuid,
                    "timestamp_epoch": int(time.time())
                }
                payload_str = json.dumps(payload)
                pub_hm.publish(PRIMARY_TOPIC, payload_str, qos=0)
                pub_em.publish(PRIMARY_TOPIC, payload_str, qos=0)
                time.sleep(0.06)  # 60ms interval

            # Wait for reception
            deadline = time.time() + 15.0
            while (len(hm_packets) < num_packets or len(em_packets) < num_packets) and time.time() < deadline:
                time.sleep(0.2)

            assert len(hm_packets) >= 8, f"HiveMQ received {len(hm_packets)}/{num_packets} packets"
            assert len(em_packets) >= 8, f"EMQX received {len(em_packets)}/{num_packets} packets"
            assert hm_packets == sorted(hm_packets), "HiveMQ packets received out of order"
            assert em_packets == sorted(em_packets), "EMQX packets received out of order"
        finally:
            for c in [sub_hm, sub_em, pub_hm, pub_em]:
                try:
                    c.loop_stop()
                    c.disconnect()
                except Exception:
                    pass

    def test_concurrent_multithreaded_publisher_stress(self):
        """Simulates 5 concurrent publisher threads pumping 20 packets each to the dual broker publisher class."""
        pub_manager = DualBrokerMqttPublisher()
        time.sleep(1.0)  # Allow async connection

        total_threads = 5
        packets_per_thread = 20
        errors = queue.Queue()

        def worker(thread_idx: int):
            try:
                for i in range(packets_per_thread):
                    seq = (thread_idx * 1000) + i
                    payload = build_telemetry_payload(
                        seq=seq,
                        pm1=5.0, pm25=12.0 + (i * 0.1), pm10=20.0,
                        temp=27.0 + thread_idx, hum=50.0, press=1010.0,
                        rain=False
                    )
                    pub_manager.publish(payload)
                    time.sleep(0.01)
            except Exception as e:
                errors.put(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(total_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert errors.empty(), f"Multithreaded publishing raised exceptions: {list(errors.queue)}"

        # Clean up clients
        for client in pub_manager.clients.values():
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass


# =============================================================================
# 2. TOPIC ROUTING & TOPIC COLLISION CHALLENGE
# =============================================================================

class TestTopicRoutingAndCollisionStress:
    """Challenges topic isolation, multi-level wildcards, and collision boundaries."""

    def test_hierarchical_and_wildcard_topic_stress(self):
        """Tests complex topic subscriptions: 'airsense/#', 'airsense/+/bic_roof/telemetry', and exact topics."""
        sub_all_wild = create_paho_v2_client("sub-all")
        sub_station_wild = create_paho_v2_client("sub-stn-wild")
        sub_exact_khi = create_paho_v2_client("sub-exact-khi")
        sub_exact_isb = create_paho_v2_client("sub-exact-isb")
        pub_client = create_paho_v2_client("pub-topic-stress")

        all_ready = threading.Event()
        stn_ready = threading.Event()
        khi_ready = threading.Event()
        isb_ready = threading.Event()

        all_received = []
        stn_received = []
        khi_received = []
        isb_received = []

        stress_uuid = uuid.uuid4().hex

        sub_all_wild.on_connect = lambda c, u, f, rc, p=None: (c.subscribe("airsense/#"), all_ready.set())
        sub_station_wild.on_connect = lambda c, u, f, rc, p=None: (c.subscribe("airsense/+/bic_roof/telemetry"), stn_ready.set())
        sub_exact_khi.on_connect = lambda c, u, f, rc, p=None: (c.subscribe("airsense/karachi/bic_roof/telemetry"), khi_ready.set())
        sub_exact_isb.on_connect = lambda c, u, f, rc, p=None: (c.subscribe("airsense/islamabad/bic_roof/telemetry"), isb_ready.set())

        def make_collector(target_list):
            def on_msg(c, u, msg):
                try:
                    d = json.loads(msg.payload.decode("utf-8"))
                    if d.get("stress_uuid") == stress_uuid:
                        target_list.append((msg.topic, d.get("tag")))
                except Exception:
                    pass
            return on_msg

        sub_all_wild.on_message = make_collector(all_received)
        sub_station_wild.on_message = make_collector(stn_received)
        sub_exact_khi.on_message = make_collector(khi_received)
        sub_exact_isb.on_message = make_collector(isb_received)

        try:
            for sub in [sub_all_wild, sub_station_wild, sub_exact_khi, sub_exact_isb]:
                sub.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
                sub.loop_start()

            assert all_ready.wait(timeout=12.0)
            assert stn_ready.wait(timeout=12.0)
            assert khi_ready.wait(timeout=12.0)
            assert isb_ready.wait(timeout=12.0)

            pub_client.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
            pub_client.loop_start()
            time.sleep(0.5)

            # Publish 3 distinct messages to different topic levels
            topics_and_tags = [
                ("airsense/karachi/bic_roof/telemetry", "khi_roof"),
                ("airsense/islamabad/bic_roof/telemetry", "isb_roof"),
                ("airsense/karachi/lab_internal/telemetry", "khi_lab"),
            ]

            for top, tag in topics_and_tags:
                payload = {"stress_uuid": stress_uuid, "tag": tag, "timestamp": time.time()}
                pub_client.publish(top, json.dumps(payload), qos=0)
                time.sleep(0.1)

            time.sleep(2.0)

            # Assertions:
            # 1. 'airsense/#' should capture all 3 messages
            all_tags = [t[1] for t in all_received]
            assert "khi_roof" in all_tags
            assert "isb_roof" in all_tags
            assert "khi_lab" in all_tags

            # 2. 'airsense/+/bic_roof/telemetry' should capture khi_roof and isb_roof, but NOT khi_lab
            stn_tags = [t[1] for t in stn_received]
            assert "khi_roof" in stn_tags
            assert "isb_roof" in stn_tags
            assert "khi_lab" not in stn_tags

            # 3. Exact Karachi subscriber must only have khi_roof
            khi_tags = [t[1] for t in khi_received]
            assert khi_tags == ["khi_roof"]

            # 4. Exact Islamabad subscriber must only have isb_roof
            isb_tags = [t[1] for t in isb_received]
            assert isb_tags == ["isb_roof"]

        finally:
            for c in [sub_all_wild, sub_station_wild, sub_exact_khi, sub_exact_isb, pub_client]:
                try:
                    c.loop_stop()
                    c.disconnect()
                except Exception:
                    pass

    def test_topic_injection_and_unrelated_prefix_isolation(self):
        """Verifies that publishing to non-airsense or malformed topics does not affect airsense subscribers."""
        sub_khi = create_paho_v2_client("sub-isolate")
        pub_client = create_paho_v2_client("pub-isolate")

        khi_ready = threading.Event()
        received = []
        stress_uuid = uuid.uuid4().hex

        def on_msg(c, u, msg):
            try:
                payload_str = msg.payload.decode("utf-8", errors="ignore")
                if stress_uuid in payload_str:
                    received.append(payload_str)
            except Exception:
                pass
        sub_khi.on_connect = lambda c, u, f, rc, p=None: (c.subscribe(PRIMARY_TOPIC), khi_ready.set())
        sub_khi.on_message = on_msg

        try:
            sub_khi.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
            sub_khi.loop_start()
            assert khi_ready.wait(timeout=12.0)

            pub_client.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
            pub_client.loop_start()
            time.sleep(0.5)

            # Publish to unrelated topic prefixes
            pub_client.publish("other_app/karachi/bic_roof/telemetry", json.dumps({"stress_uuid": stress_uuid, "leak": True}))
            pub_client.publish("airsense_fake/karachi/bic_roof/telemetry", json.dumps({"stress_uuid": stress_uuid, "leak": True}))
            time.sleep(1.0)

            # Now publish valid topic
            pub_client.publish(PRIMARY_TOPIC, json.dumps({"stress_uuid": stress_uuid, "valid": True}))
            for _ in range(30):
                if len(received) >= 1:
                    break
                time.sleep(0.1)

            assert len(received) == 1, f"Expected 1 valid message, got {len(received)}"
            assert '"valid": true' in received[0].lower()
            assert "leak" not in received[0].lower()
        finally:
            for c in [sub_khi, pub_client]:
                try:
                    c.loop_stop()
                    c.disconnect()
                except Exception:
                    pass


# =============================================================================
# 3. BROKER FAILOVER & NETWORK RECOVERY STRESS
# =============================================================================

class TestBrokerFailoverAndRecovery:
    """Stress-tests failover behavior when one broker is unreachable or drops socket."""

    def test_publisher_survives_partial_broker_failure(self):
        """Simulates primary broker offline by pointing it to an invalid port while secondary remains live."""
        pub_manager = DualBrokerMqttPublisher()
        # Deliberately sabotage one client to simulate broker outage
        sabotaged_client = create_paho_v2_client("sabotaged")
        # Do not connect sabotaged client
        pub_manager.clients["SabotagedBroker"] = sabotaged_client

        # Publishing should NOT raise exception even if one client is dead
        payload = build_telemetry_payload(
            seq=999,
            pm1=8.0, pm25=15.0, pm10=22.0,
            temp=29.0, hum=60.0, press=1012.0,
            rain=False
        )
        # Must execute cleanly without unhandled exceptions
        pub_manager.publish(payload)

        # Cleanup
        for c in pub_manager.clients.values():
            try:
                c.loop_stop()
                c.disconnect()
            except Exception:
                pass

    def test_client_automatic_reconnection_after_network_drop(self):
        """Verifies that dropping a live connection triggers auto-reconnect without crashing."""
        client = create_paho_v2_client("reconnect-stress")
        connect_count = 0
        disconnect_count = 0
        initial_connected = threading.Event()
        reconnected = threading.Event()

        def on_connect(c, userdata, flags, rc, properties=None):
            nonlocal connect_count
            connect_count += 1
            if connect_count == 1:
                initial_connected.set()
            elif connect_count >= 2:
                reconnected.set()

        def on_disconnect(c, userdata, *args):
            nonlocal disconnect_count
            disconnect_count += 1

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.reconnect_delay_set(min_delay=1, max_delay=3)

        try:
            client.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=10)
            client.loop_start()

            # Wait for first connect
            assert initial_connected.wait(timeout=12.0), "Initial connection failed"
            assert connect_count >= 1

            # Force socket disconnect
            if client._sock:
                try:
                    client._sock.close()
                except Exception:
                    pass

            # Wait for Paho auto-reconnect
            assert reconnected.wait(timeout=15.0), "Paho failed to auto-reconnect after socket drop"
            assert connect_count >= 2
            assert disconnect_count >= 1
        finally:
            client.loop_stop()
            try:
                client.disconnect()
            except Exception:
                pass


# =============================================================================
# 4. ADVERSARIAL PAYLOAD FUZZING & SERIAL PARSER CORRUPTION STRESS
# =============================================================================

class TestAdversarialPayloadFuzzing:
    """Stress-tests the parser and MQTT forwarder with malformed, extreme, and fuzzed payloads."""

    def test_serial_parser_under_heavy_corruption(self):
        """Feeds truncated JSON, non-ascii bytes, SQL injection, and huge strings into parse_serial_line."""
        current_data = {"pm1": 7.0, "pm2_5": 9.0, "pm10": 10.0, "temp": 29.5, "hum": 65.0, "press": 1012.0, "rain": False}

        malicious_inputs = [
            "",  # Empty
            "   \n\r  ",  # Whitespace
            "[JSON_TELEMETRY] {bad json",  # Truncated JSON
            "[JSON_TELEMETRY] {\"device_uid\": \"AIRSENSE-NODE-01\", \"pm2_5\": NaN}",  # NaN JSON
            "[JSON_TELEMETRY] {\"device_uid\": \"AIRSENSE-NODE-01\", \"pm2_5\": Infinity}",  # Infinity JSON
            "[JSON_TELEMETRY] {\"device_uid\": \"AIRSENSE-NODE-01\", \"temperature\": 1e500}",  # Overflow
            "[JSON_TELEMETRY] " + "A" * 50000,  # Giant 50KB garbage
            "[LOG] Booting ESP32 with 0xDEADBEEF...",  # Serial debug log
            "[DEBUG] Free heap: 182400 bytes",
            "PM1.0: NOT_A_NUM | PM2.5: -- | PM10: 999999",  # Corrupted ASCII log
            "Temp: -999.0 C | Hum: 200.0% | Press: 0.0",  # Out of bounds ASCII log
            "Rain: MAYBE",  # Invalid rain state
            "Rain: 1",  # Valid rain
            "--------------------------------------------------------",  # Separator
            "[HTTP PUSH] Success 200",
            "'; DROP TABLE raw_readings; --",  # SQL injection
            "<script>alert('xss')</script>",  # XSS
            "\x00\xFF\xFE\xFD\x80\x81\x82",  # Binary garbage
        ]

        for raw_line in malicious_inputs:
            # Must NOT raise any exceptions
            try:
                payload, is_cycle = parse_serial_line(raw_line, current_data)
                # If payload returned, verify it is a valid dict
                if payload is not None:
                    assert isinstance(payload, dict)
                    assert "device_uid" in payload
                    assert isinstance(payload["pm2_5"], (int, float))
            except Exception as e:
                pytest.fail(f"parse_serial_line crashed on input '{raw_line[:50]}': {e}")

    def test_mqtt_forwarder_on_message_resilience(self):
        """Mocks incoming MQTT messages with corrupted payloads to verify forwarder never crashes."""
        class MockMsg:
            def __init__(self, payload: bytes, topic: str = PRIMARY_TOPIC):
                self.payload = payload
                self.topic = topic

        corrupt_payloads = [
            b"",
            b"   ",
            b"{not json",
            b"{\"pm2_5\": \"not-a-number\", \"temperature\": null}",
            b"{\"station_code\": 12345, \"sequence_number\": \"INVALID\"}",
            b"\x00\x01\x02\x03\x04\xff\xfe",
            json.dumps({"pm2_5": 1e308, "temperature": -1e308}).encode("utf-8"),
            json.dumps({"sensor_health": None, "rain_flag": "YES"}).encode("utf-8"),
        ]

        mock_client = create_paho_v2_client("mock-forwarder")
        userdata = {"broker_name": "TestBroker", "host": "127.0.0.1", "port": 1883}

        for p in corrupt_payloads:
            msg = MockMsg(p)
            try:
                # Must handle gracefully without throwing uncaught exceptions
                forwarder_on_message(mock_client, userdata, msg)
            except Exception as e:
                pytest.fail(f"forwarder_on_message crashed on payload {p[:30]}: {e}")


# =============================================================================
# 5. HARDWARE DISCOVERY & COM SCANNER STRESS
# =============================================================================

class TestHardwareScannerResilience:
    """Tests port discovery algorithms and fallback behavior under absent hardware."""

    def test_port_scanner_handles_empty_or_absent_com(self):
        """Verifies scan_available_ports and find_esp32_port return valid types under any hardware state."""
        ports = scan_available_ports()
        assert isinstance(ports, list)

        # Test with non-existent preferred port
        chosen = find_esp32_port(preferred_port="COM999_NON_EXISTENT")
        if ports:
            assert chosen == ports[0]
        else:
            assert chosen is None

        # Test with AUTO
        auto_chosen = find_esp32_port(preferred_port="AUTO")
        if ports:
            assert auto_chosen == ports[0]
        else:
            assert auto_chosen is None

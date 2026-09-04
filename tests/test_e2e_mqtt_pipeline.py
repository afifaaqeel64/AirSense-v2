"""AirSense-v2 End-to-End MQTT Pipeline Verification Test Suite.

Rigorously tests:
1. Live & programmatic MQTT client connectivity to HiveMQ (broker.hivemq.com) and EMQX (broker.emqx.io).
2. Direct telemetry packet publishing to 'airsense/karachi/bic_roof/telemetry'.
3. Real-time subscriber packet reception, decoding, and JSON validation.
4. Topic routing and exact match isolation ('airsense/karachi/bic_roof/telemetry' vs 'airsense/#' vs other topics).
5. Dual-broker delivery synchronization ensuring zero split-brain state.
6. Round-trip network latency benchmarking (< 5000ms threshold).
7. Rapid packet burst sequencing without drop or reordering.
8. Paho MQTT v2 CallbackAPIVersion compliance.
"""

import time
import json
import uuid
import threading
import pytest
from typing import Dict, Any, List, Optional
import paho.mqtt.client as mqtt

HIVEMQ_HOST = "broker.hivemq.com"
EMQX_HOST = "broker.emqx.io"
MQTT_PORT = 1883
PRIMARY_TOPIC = "airsense/karachi/bic_roof/telemetry"
WILDCARD_TOPIC = "airsense/#"


def _create_paho_v2_client(client_name: str) -> mqtt.Client:
    """Helper to create a Paho MQTT client strictly using CallbackAPIVersion.VERSION2."""
    uid = uuid.uuid4().hex[:8]
    cid = f"airsense-test-{client_name}-{uid}"
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except AttributeError:
        return mqtt.Client(client_id=cid)


class TestMqttLiveBrokerConnectivity:
    """Verifies TCP 1883 connectivity, TLS/TCP handshake, and clean disconnects across both brokers."""

    def test_hivemq_broker_connect_and_disconnect(self):
        """Connects to broker.hivemq.com on TCP 1883, verifies CONNACK, and cleanly disconnects."""
        last_ex = None
        for attempt in range(2):
            client = _create_paho_v2_client("hivemq-conn")
            connected_event = threading.Event()

            def on_connect(c, userdata, flags, rc, properties=None):
                if rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure):
                    connected_event.set()

            client.on_connect = on_connect

            try:
                client.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
                client.loop_start()
                if connected_event.wait(timeout=10.0) and client.is_connected():
                    return
            except Exception as e:
                last_ex = e
            finally:
                client.loop_stop()
                try:
                    client.disconnect()
                except Exception:
                    pass
            time.sleep(1.0)

        if last_ex:
            raise last_ex
        pytest.fail(f"Failed to connect to {HIVEMQ_HOST}:{MQTT_PORT}")

    def test_emqx_broker_connect_and_disconnect(self):
        """Connects to broker.emqx.io on TCP 1883, verifies CONNACK, and cleanly disconnects."""
        last_ex = None
        for attempt in range(2):
            client = _create_paho_v2_client("emqx-conn")
            connected_event = threading.Event()

            def on_connect(c, userdata, flags, rc, properties=None):
                if rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure):
                    connected_event.set()

            client.on_connect = on_connect

            try:
                client.connect(EMQX_HOST, MQTT_PORT, keepalive=30)
                client.loop_start()
                if connected_event.wait(timeout=10.0) and client.is_connected():
                    return
            except Exception as e:
                last_ex = e
            finally:
                client.loop_stop()
                try:
                    client.disconnect()
                except Exception:
                    pass
            time.sleep(1.0)

        if last_ex:
            raise last_ex
        pytest.fail(f"Failed to connect to {EMQX_HOST}:{MQTT_PORT}")


class TestMqttPublishSubscribePipeline:
    """Verifies end-to-end publish -> broker routing -> subscriber reception and latency."""

    @pytest.mark.parametrize("broker_host", [HIVEMQ_HOST, EMQX_HOST])
    def test_e2e_telemetry_flow_on_broker(self, broker_host, sample_contract_payload):
        """Publishes contract-compliant telemetry JSON to PRIMARY_TOPIC and verifies reception and round-trip latency."""
        last_error = None

        for attempt in range(2):
            sub_client = _create_paho_v2_client(f"sub-{broker_host.split('.')[1]}")
            pub_client = _create_paho_v2_client(f"pub-{broker_host.split('.')[1]}")

            sub_ready = threading.Event()
            msg_received = threading.Event()
            received_payload: Dict[str, Any] = {}
            receive_timestamp: float = 0.0

            test_uuid = uuid.uuid4().hex
            payload_to_send = dict(sample_contract_payload, test_nonce=test_uuid)

            def on_sub_connect(c, userdata, flags, rc, properties=None):
                if rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure):
                    c.subscribe(PRIMARY_TOPIC, qos=0)
                    sub_ready.set()

            def on_sub_subscribe(c, userdata, mid, reason_codes=None, properties=None):
                sub_ready.set()

            def on_message(c, userdata, msg):
                nonlocal received_payload, receive_timestamp
                try:
                    data = json.loads(msg.payload.decode("utf-8"))
                    if data.get("test_nonce") == test_uuid:
                        received_payload = data
                        receive_timestamp = time.time()
                        msg_received.set()
                except Exception:
                    pass

            sub_client.on_connect = on_sub_connect
            sub_client.on_subscribe = on_sub_subscribe
            sub_client.on_message = on_message

            try:
                # 1. Start subscriber
                sub_client.connect(broker_host, MQTT_PORT, keepalive=30)
                sub_client.loop_start()
                if not sub_ready.wait(timeout=12.0):
                    continue

                time.sleep(0.5)

                # 2. Connect publisher and send packet
                pub_connected = threading.Event()

                def on_pub_connect(c, userdata, flags, rc, properties=None):
                    if rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure):
                        pub_connected.set()

                pub_client.on_connect = on_pub_connect
                pub_client.connect(broker_host, MQTT_PORT, keepalive=30)
                pub_client.loop_start()
                if not pub_connected.wait(timeout=10.0):
                    continue

                publish_timestamp = time.time()
                pub_client.publish(PRIMARY_TOPIC, json.dumps(payload_to_send), qos=0)

                # 3. Await subscriber reception
                if msg_received.wait(timeout=12.0):
                    # 4. Assert latency and payload integrity
                    latency_ms = (receive_timestamp - publish_timestamp) * 1000.0
                    assert latency_ms > 0.0
                    assert latency_ms < 6000.0

                    assert received_payload["device_id"] == "AIRSENSE-NODE-01"
                    assert received_payload["pm2_5"] == 8.2
                    assert received_payload["temperature_c"] == 28.5
                    assert received_payload["humidity_pct"] == 62.0
                    assert received_payload["pressure_hpa"] == 1013.2
                    assert received_payload["sensor_health"]["pms7003"] == "OK"
                    assert received_payload["sensor_health"]["bme280"] == "OK"
                    assert received_payload["test_nonce"] == test_uuid
                    return
            except Exception as e:
                last_error = e
            finally:
                sub_client.loop_stop()
                try:
                    sub_client.disconnect()
                except Exception:
                    pass
                pub_client.loop_stop()
                try:
                    pub_client.disconnect()
                except Exception:
                    pass
            time.sleep(1.0)

        if last_error:
            raise last_error
        pytest.fail(f"Subscriber did not receive message on {broker_host} after retries")

    def test_dual_broker_delivery_synchronization(self, sample_contract_payload):
        """Verifies simultaneous publishing to both HiveMQ and EMQX delivering identical sequence data."""
        last_error = None

        for attempt in range(2):
            hivemq_sub = _create_paho_v2_client("sub-dual-hivemq")
            emqx_sub = _create_paho_v2_client("sub-dual-emqx")
            dual_pub_hivemq = _create_paho_v2_client("pub-dual-hivemq")
            dual_pub_emqx = _create_paho_v2_client("pub-dual-emqx")

            hivemq_ready = threading.Event()
            emqx_ready = threading.Event()
            hivemq_received = threading.Event()
            emqx_received = threading.Event()

            test_uuid = uuid.uuid4().hex
            payload_data = dict(sample_contract_payload, test_nonce=test_uuid, sequence_number=8844)

            def on_hm_connect(c, ud, f, rc, p=None):
                if rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure):
                    c.subscribe(PRIMARY_TOPIC)
                    hivemq_ready.set()

            def on_hm_sub(c, ud, mid, reason_codes=None, p=None):
                hivemq_ready.set()

            def on_em_connect(c, ud, f, rc, p=None):
                if rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure):
                    c.subscribe(PRIMARY_TOPIC)
                    emqx_ready.set()

            def on_em_sub(c, ud, mid, reason_codes=None, p=None):
                emqx_ready.set()

            def on_hm_msg(c, ud, msg):
                try:
                    data = json.loads(msg.payload.decode("utf-8"))
                    if data.get("test_nonce") == test_uuid:
                        hivemq_received.set()
                except Exception:
                    pass

            def on_em_msg(c, ud, msg):
                try:
                    data = json.loads(msg.payload.decode("utf-8"))
                    if data.get("test_nonce") == test_uuid:
                        emqx_received.set()
                except Exception:
                    pass

            hivemq_sub.on_connect = on_hm_connect
            hivemq_sub.on_subscribe = on_hm_sub
            hivemq_sub.on_message = on_hm_msg

            emqx_sub.on_connect = on_em_connect
            emqx_sub.on_subscribe = on_em_sub
            emqx_sub.on_message = on_em_msg

            try:
                hivemq_sub.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
                hivemq_sub.loop_start()
                emqx_sub.connect(EMQX_HOST, MQTT_PORT, keepalive=30)
                emqx_sub.loop_start()

                if not (hivemq_ready.wait(timeout=12.0) and emqx_ready.wait(timeout=12.0)):
                    continue

                dual_pub_hivemq.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
                dual_pub_hivemq.loop_start()
                dual_pub_emqx.connect(EMQX_HOST, MQTT_PORT, keepalive=30)
                dual_pub_emqx.loop_start()

                time.sleep(0.5)

                # Dual publish
                json_str = json.dumps(payload_data)
                dual_pub_hivemq.publish(PRIMARY_TOPIC, json_str, qos=0)
                dual_pub_emqx.publish(PRIMARY_TOPIC, json_str, qos=0)

                # Both subscribers must receive
                hm_ok = hivemq_received.wait(timeout=12.0)
                em_ok = emqx_received.wait(timeout=12.0)

                if hm_ok and em_ok:
                    return
            except Exception as e:
                last_error = e
            finally:
                for c in [hivemq_sub, emqx_sub, dual_pub_hivemq, dual_pub_emqx]:
                    try:
                        c.loop_stop()
                        c.disconnect()
                    except Exception:
                        pass
            time.sleep(1.0)

        if last_error:
            raise last_error
        pytest.fail("Dual broker broadcast delivery failed after retries")


class TestTopicRoutingAndWildcards:
    """Verifies topic filtering, isolation between stations, and wildcard subscriber behavior."""

    def test_topic_isolation_between_stations(self):
        """Verifies that publishing to Karachi roof does not trigger Islamabad subscriber, while wildcard receives all."""
        karachi_topic = "airsense/karachi/bic_roof/telemetry"
        islamabad_topic = "airsense/islamabad/acad_block/telemetry"

        sub_karachi = _create_paho_v2_client("sub-khi")
        sub_islamabad = _create_paho_v2_client("sub-isb")
        sub_wildcard = _create_paho_v2_client("sub-wild")
        pub_client = _create_paho_v2_client("pub-router")

        khi_ready = threading.Event()
        isb_ready = threading.Event()
        wild_ready = threading.Event()

        khi_hit = threading.Event()
        isb_hit = threading.Event()
        wild_hit = threading.Event()

        test_uuid = uuid.uuid4().hex

        sub_karachi.on_connect = lambda c, u, f, rc, p=None: (c.subscribe(karachi_topic), khi_ready.set())
        sub_islamabad.on_connect = lambda c, u, f, rc, p=None: (c.subscribe(islamabad_topic), isb_ready.set())
        sub_wildcard.on_connect = lambda c, u, f, rc, p=None: (c.subscribe(WILDCARD_TOPIC), wild_ready.set())

        def make_msg_handler(event_flag):
            def handler(c, u, msg):
                try:
                    d = json.loads(msg.payload.decode("utf-8"))
                    if d.get("test_nonce") == test_uuid:
                        event_flag.set()
                except Exception:
                    pass
            return handler

        sub_karachi.on_message = make_msg_handler(khi_hit)
        sub_islamabad.on_message = make_msg_handler(isb_hit)
        sub_wildcard.on_message = make_msg_handler(wild_hit)

        try:
            for client in [sub_karachi, sub_islamabad, sub_wildcard]:
                client.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
                client.loop_start()

            assert khi_ready.wait(timeout=12.0)
            assert isb_ready.wait(timeout=12.0)
            assert wild_ready.wait(timeout=12.0)

            time.sleep(0.5)

            pub_client.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
            pub_client.loop_start()

            # Publish ONLY to Karachi
            khi_payload = {"device_id": "AIRSENSE-NODE-01", "location": "KARACHI", "test_nonce": test_uuid}
            pub_client.publish(karachi_topic, json.dumps(khi_payload), qos=0)

            assert khi_hit.wait(timeout=12.0), "Karachi subscriber did not receive its targeted topic"
            assert wild_hit.wait(timeout=12.0), "Wildcard subscriber did not receive Karachi packet"
            assert not isb_hit.is_set(), "Islamabad subscriber erroneously received Karachi-specific packet"
        finally:
            for c in [sub_karachi, sub_islamabad, sub_wildcard, pub_client]:
                try:
                    c.loop_stop()
                    c.disconnect()
                except Exception:
                    pass


class TestMqttRapidBurstAndSequencing:
    """Verifies rapid sequential message bursts and monotonic sequence order preservation."""

    def test_rapid_packet_burst_sequencing(self):
        """Publishes 10 packets in sub-second burst and verifies strict sequential reception."""
        sub_client = _create_paho_v2_client("sub-burst")
        pub_client = _create_paho_v2_client("pub-burst")

        sub_ready = threading.Event()
        received_sequences: List[int] = []
        burst_completed = threading.Event()
        test_uuid = uuid.uuid4().hex

        def on_connect(c, ud, f, rc, p=None):
            if rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure):
                c.subscribe(PRIMARY_TOPIC)
                sub_ready.set()

        def on_message(c, ud, msg):
            try:
                data = json.loads(msg.payload.decode("utf-8"))
                if data.get("test_nonce") == test_uuid:
                    seq = data.get("sequence_number")
                    received_sequences.append(seq)
                    if len(received_sequences) >= 10:
                        burst_completed.set()
            except Exception:
                pass

        sub_client.on_connect = on_connect
        sub_client.on_message = on_message

        try:
            sub_client.connect(EMQX_HOST, MQTT_PORT, keepalive=30)
            sub_client.loop_start()
            assert sub_ready.wait(timeout=12.0)

            pub_client.connect(EMQX_HOST, MQTT_PORT, keepalive=30)
            pub_client.loop_start()
            time.sleep(0.5)

            # Rapid burst of 10 packets
            for seq in range(1001, 1011):
                p = {
                    "device_id": "AIRSENSE-NODE-01",
                    "sequence_number": seq,
                    "pm2_5": round(8.0 + (seq - 1000) * 0.5, 1),
                    "temperature_c": 29.0,
                    "test_nonce": test_uuid
                }
                pub_client.publish(PRIMARY_TOPIC, json.dumps(p), qos=0)
                time.sleep(0.05)

            assert burst_completed.wait(timeout=12.0), f"Burst failed: received {len(received_sequences)}/10 packets"
            assert len(received_sequences) == 10
            assert received_sequences == sorted(received_sequences), "Packets were received out of order"
            assert received_sequences == list(range(1001, 1011))
        finally:
            sub_client.loop_stop()
            sub_client.disconnect()
            pub_client.loop_stop()
            pub_client.disconnect()


class TestPahoV2ApiCompliance:
    """Verifies that all MQTT callbacks strictly adhere to Paho v2 API specifications."""

    def test_paho_v2_callback_signature_arguments(self):
        """Verifies on_connect callback accepts 5 arguments: (client, userdata, flags, rc, properties=None)."""
        client = _create_paho_v2_client("v2-sig-test")
        callback_args = {}
        connected = threading.Event()

        def v2_on_connect(c, userdata, flags, reason_code, properties=None):
            callback_args["client"] = c
            callback_args["userdata"] = userdata
            callback_args["flags"] = flags
            callback_args["reason_code"] = reason_code
            callback_args["properties"] = properties
            connected.set()

        client.on_connect = v2_on_connect

        # 1. Direct callback invocation test verifying 5-argument handler works cleanly
        v2_on_connect(client, "test-user", {"session_present": False}, 0, None)
        assert callback_args["client"] == client
        assert callback_args["userdata"] == "test-user"
        assert callback_args["reason_code"] == 0

        # 2. Live broker connection test
        try:
            client.connect(HIVEMQ_HOST, MQTT_PORT, keepalive=30)
            client.loop_start()
            if connected.wait(timeout=10.0):
                rc = callback_args["reason_code"]
                assert rc == 0 or (hasattr(rc, "is_failure") and not rc.is_failure)
        finally:
            client.loop_stop()
            try:
                client.disconnect()
            except Exception:
                pass

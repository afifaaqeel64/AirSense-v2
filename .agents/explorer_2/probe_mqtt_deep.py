import paho.mqtt.client as mqtt
import time
import json

def test_broker(host, port, transport="tcp"):
    print(f"Testing {host}:{port} (transport={transport})...")
    received = []
    
    def on_connect(client, userdata, flags, rc, properties=None):
        print(f"  [{host}] Connected with code {rc}")
        client.subscribe("airsense/karachi/bic_roof/telemetry")
        client.subscribe("airsense/#")

    def on_message(client, userdata, msg):
        print(f"  [{host}] Received message on {msg.topic}: {msg.payload.decode()[:60]}")
        received.append(msg.payload.decode())

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"airsense-probe-{int(time.time()*1000)%100000}", transport=transport)
    except AttributeError:
        client = mqtt.Client(client_id=f"airsense-probe-{int(time.time()*1000)%100000}", transport=transport)

    if transport == "websockets":
        client.ws_set_options(path="/mqtt")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(host, port, keepalive=30)
        client.loop_start()
        time.sleep(2.0)
        
        sample_payload = json.dumps({
            "schema_version": "1.0",
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "station_code": "BIC-KHI-ROOF-01",
            "sequence_number": 42,
            "pm2_5": 14.2,
            "temperature": 30.1,
            "humidity": 62.0
        })
        
        print(f"  [{host}] Publishing probe message...")
        pub_info = client.publish("airsense/karachi/bic_roof/telemetry", sample_payload, qos=0)
        pub_info.wait_for_publish(timeout=3.0)
        
        time.sleep(2.0)
        client.loop_stop()
        client.disconnect()
        print(f"  [{host}] Result: {len(received)} message(s) received.\n")
    except Exception as e:
        print(f"  [{host}] Exception: {e}\n")

if __name__ == "__main__":
    print("=== TESTING TCP MQTT (Port 1883) ===")
    test_broker("broker.hivemq.com", 1883, "tcp")
    test_broker("broker.emqx.io", 1883, "tcp")

    print("\n=== TESTING WEBSOCKETS (HTTP / non-SSL) ===")
    test_broker("broker.hivemq.com", 8000, "websockets")
    test_broker("broker.emqx.io", 8083, "websockets")

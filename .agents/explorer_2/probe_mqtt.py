import paho.mqtt.client as mqtt
import time
import json

def test_broker(host, port):
    print(f"Testing {host}:{port}...")
    received = []
    
    def on_connect(client, userdata, flags, rc, properties=None):
        client.subscribe("airsense/test/probe")

    def on_message(client, userdata, msg):
        received.append(msg.payload.decode())

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"probe-{int(time.time())}")
    except AttributeError:
        client = mqtt.Client(client_id=f"probe-{int(time.time())}")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(host, port, keepalive=10)
        client.loop_start()
        time.sleep(1.0)
        client.publish("airsense/test/probe", json.dumps({"status": "alive", "time": time.time()}))
        time.sleep(2.0)
        client.loop_stop()
        client.disconnect()
        print(f"SUCCESS on {host}: received {len(received)} message(s) -> {received}")
    except Exception as e:
        print(f"FAILURE on {host}: {e}")

if __name__ == "__main__":
    print("Testing HiveMQ...")
    test_broker("broker.hivemq.com", 1883)
    print("\nTesting EMQX...")
    test_broker("broker.emqx.io", 1883)

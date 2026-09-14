import paho.mqtt.client as mqtt
import time
import json
import ssl

def test_wss(host, port):
    print(f"Testing WSS on {host}:{port}...")
    received = []
    
    def on_connect(client, userdata, flags, rc, properties=None):
        print(f"  [{host}:{port}] Connected WSS successfully (rc={rc})")
        client.subscribe("airsense/karachi/bic_roof/telemetry")

    def on_message(client, userdata, msg):
        print(f"  [{host}:{port}] WSS received: {msg.payload.decode()[:60]}")
        received.append(msg.payload.decode())

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"wss-probe-{int(time.time()*1000)%100000}", transport="websockets")
    except AttributeError:
        client = mqtt.Client(client_id=f"wss-probe-{int(time.time()*1000)%100000}", transport="websockets")

    client.ws_set_options(path="/mqtt")
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(host, port, keepalive=30)
        client.loop_start()
        time.sleep(2.0)
        
        sample = json.dumps({"schema_version": "1.0", "pm2_5": 11.5, "station_code": "BIC-KHI-ROOF-01"})
        pub = client.publish("airsense/karachi/bic_roof/telemetry", sample, qos=0)
        pub.wait_for_publish(timeout=3.0)
        time.sleep(2.0)
        client.loop_stop()
        client.disconnect()
        print(f"  [{host}:{port}] WSS Result: {len(received)} message(s) received.\n")
    except Exception as e:
        print(f"  [{host}:{port}] WSS Exception: {e}\n")

if __name__ == "__main__":
    test_wss("broker.hivemq.com", 8884)
    test_wss("broker.emqx.io", 8084)

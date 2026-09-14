import json
import logging
import sqlite3
import datetime
import uuid
import hashlib
import paho.mqtt.client as mqtt

BROKER = "562b34e92dc74f71895ba99ac87c8667.s1.eu.hivemq.cloud"
PORT = 8883
TOPIC = "airsense/+/+/telemetry"
USER = "airsense_node_01"
PASSWORD = "AirSense2026!"
DB_PATH = "data/airsense.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logging.info("[MQTT CLOUD] Connected to HiveMQ Cloud successfully!")
        client.subscribe(TOPIC)
        logging.info(f"[MQTT CLOUD] Subscribed to topic: {TOPIC}")
    else:
        logging.error(f"[MQTT CLOUD] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        logging.info(f"[MQTT CLOUD PACKET] Received from {msg.topic}: {payload}")
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        reading_id = str(uuid.uuid4())
        c_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        
        pm1 = payload.get("pm1")
        pm2_5 = payload.get("pm2_5")
        pm10 = payload.get("pm10")
        temp = payload.get("temperature") or payload.get("temperature_c")
        hum = payload.get("humidity") or payload.get("humidity_pct")
        press = payload.get("pressure") or payload.get("pressure_hpa")
        rain = payload.get("rain_flag", False)
        seq = payload.get("sequence_number", 0)
        
        cur.execute("""
            INSERT INTO raw_readings (
                id, campus_id, station_id, device_id,
                observed_at, source_timestamp_original, received_at,
                source, pm1, pm2_5, pm10,
                temperature_c, humidity_pct, pressure_hpa, rain_flag,
                payload_json, pollutant_metadata_json, ingested_via,
                sequence_number, schema_version, content_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reading_id,
            "3dd29b2e-98cc-4328-a28f-28e994b7c2a4",
            "stn_khi_01",
            "dev_khi_01",
            now_utc,
            now_utc,
            now_utc,
            "onsite_esp32",
            pm1,
            pm2_5,
            pm10,
            temp,
            hum,
            press,
            rain,
            json.dumps(payload),
            json.dumps({}),
            "hivemq_cloud_mqtt",
            seq,
            "1.0",
            c_hash,
            now_utc
        ))
        conn.commit()
        conn.close()
        logging.info(f"[MQTT CLOUD] Saved packet #{seq} into SQLite raw_readings successfully.")
    except Exception as e:
        logging.error(f"[MQTT CLOUD ERROR] Processing message failed: {e}")

def start_mqtt_listener():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="airsense-backend-worker")
    client.username_pw_set(USER, PASSWORD)
    client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    
    logging.info(f"Connecting to HiveMQ Cloud at {BROKER}:{PORT}...")
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_forever()

if __name__ == "__main__":
    start_mqtt_listener()


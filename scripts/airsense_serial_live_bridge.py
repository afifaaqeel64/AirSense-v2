"""AirSense USB Serial to Dashboard & Dual-Broker MQTT Live Bridge.

Reads live telemetry directly from ESP32 USB Serial port and publishes to:
1. Primary Cloud MQTT Broker (broker.hivemq.com:1883)
2. Secondary Cloud MQTT Broker (broker.emqx.io:1883)
3. Local Backend API (http://127.0.0.1:8000/api/v1/ingest/reading)

Features:
- Paho-MQTT v2 API (CallbackAPIVersion.VERSION2) compatibility.
- Dual-publishing engine to both HiveMQ and EMQX for 24/7 cloud dashboard sync.
- Continuous dynamic COM port auto-discovery inside reconnect loop.
- Non-crashing infinite auto-recovery loop with exponential backoff & jitter.
- Dual parser: structured JSON line parser ([JSON_TELEMETRY] {...}) with fallback regex parser.
"""

import sys
import time
import re
import json
import random
import urllib.request
import urllib.error
import serial
import serial.tools.list_ports
import paho.mqtt.client as mqtt

# Configuration
API_ENDPOINT = "http://127.0.0.1:8000/api/v1/ingest/reading"
HEADERS = {
    "Content-Type": "application/json",
    "X-Device-Token": "airsense_dev_token_khi_01"
}

MQTT_TOPIC_PRIMARY = "airsense/karachi/bic_roof/telemetry"
MQTT_TOPIC_FALLBACK = "airsense/telemetry"

BROKER_CONFIGS = [
    {"name": "HiveMQ", "host": "broker.hivemq.com", "port": 1883},
    {"name": "EMQX", "host": "broker.emqx.io", "port": 1883}
]

KNOWN_PORT_KEYWORDS = [
    "cp210", "ch340", "ch9102", "ftdi", "silicon labs", 
    "wch", "espressif", "usb to uart", "uart"
]


class DualBrokerMqttPublisher:
    """Resilient dual MQTT publisher managing connections to HiveMQ and EMQX."""

    def __init__(self):
        self.clients = {}
        self._init_clients()

    def _init_clients(self):
        for cfg in BROKER_CONFIGS:
            name = cfg["name"]
            host = cfg["host"]
            port = cfg["port"]
            client_id = f"airsense-bridge-{name.lower()}-{int(time.time())}-{random.randint(1000, 9999)}"
            
            try:
                # Support Paho MQTT v2 API with backward compatibility fallback
                try:
                    client = mqtt.Client(
                        mqtt.CallbackAPIVersion.VERSION2,
                        client_id=client_id,
                        reconnect_on_failure=True
                    )
                except (AttributeError, TypeError):
                    client = mqtt.Client(
                        client_id=client_id
                    )

                def make_on_connect(broker_name, broker_host):
                    def on_connect(c, userdata, flags, rc, properties=None):
                        rc_code = getattr(rc, "value", rc)
                        if rc_code == 0:
                            print(f"[MQTT SUCCESS] Connected to {broker_name} ({broker_host})")
                        else:
                            print(f"[MQTT WARN] {broker_name} connect returned status: {rc}")
                    return on_connect

                def make_on_disconnect(broker_name):
                    def on_disconnect(c, userdata, *args):
                        print(f"[MQTT WARN] Disconnected from {broker_name}. Automatic reconnect scheduled.")
                    return on_disconnect

                client.on_connect = make_on_connect(name, host)
                client.on_disconnect = make_on_disconnect(name)

                client.connect_async(host, port, keepalive=30)
                client.loop_start()
                self.clients[name] = client
                print(f"[MQTT INIT] Initialized background client for {name} ({host}:{port}) with 30s keepalive")
            except Exception as e:
                print(f"[MQTT INIT ERROR] Could not initialize client for {name}: {e}")

    def publish(self, payload_dict):
        """Publish payload to all configured brokers with isolated error handling and auto-recovery."""
        payload_json = json.dumps(payload_dict)
        for name, client in list(self.clients.items()):
            try:
                info = client.publish(MQTT_TOPIC_PRIMARY, payload=payload_json, qos=0)
                # Also publish to secondary topic for generic subscribers
                client.publish(MQTT_TOPIC_FALLBACK, payload=payload_json, qos=0)
                if info.rc == mqtt.MQTT_ERR_NO_CONN:
                    print(f"[MQTT WARN] {name} socket not connected, attempting reconnect...")
                    try:
                        client.reconnect()
                    except Exception:
                        pass
                elif info.rc != mqtt.MQTT_ERR_SUCCESS:
                    print(f"[MQTT WARN] Publish to {name} returned code {info.rc}")
            except Exception as e:
                print(f"[MQTT ERROR] Failed publishing to {name}: {e}")


def scan_available_ports():
    """Scan and rank available COM ports, strictly prioritizing physical USB-UART bridges over Bluetooth."""
    ports = list(serial.tools.list_ports.comports())
    hardware_bridges = []
    others = []
    
    for p in ports:
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        
        # Skip virtual Bluetooth serial ports which lock or time out
        if "bluetooth" in desc or "bthenum" in hwid or "bth\\" in hwid:
            continue
            
        if any(kw in desc or kw in hwid for kw in KNOWN_PORT_KEYWORDS):
            hardware_bridges.append(p.device)
        else:
            others.append(p.device)
            
    return hardware_bridges + others


def find_esp32_port(preferred_port=None):
    """Finds best matching COM port, respecting preferred_port if currently online."""
    available = scan_available_ports()
    if not available:
        return None

    if preferred_port and preferred_port.upper() not in ("AUTO", "NONE", ""):
        # Check if preferred port is actually present in available list
        for p in available:
            if p.upper() == preferred_port.upper():
                return p
        # If preferred port not currently connected, fall back to best auto match
        print(f"[BRIDGE NOTICE] Specified port {preferred_port} not found. Available: {available}. Auto-selecting {available[0]}")
        return available[0]

    return available[0]


def push_to_local_api(payload):
    """Pushes telemetry to local FastAPI ingestion endpoint with fast timeout."""
    try:
        req = urllib.request.Request(
            API_ENDPOINT,
            data=json.dumps(payload).encode('utf-8'),
            headers=HEADERS,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status in (200, 201)
    except Exception:
        # Suppress local API errors if local backend server is not running
        return False


def build_telemetry_payload(seq, pm1, pm25, pm10, temp, hum, press, rain, gas=None, sensor_health=None, rain_adc=None):
    """Constructs a normalized telemetry packet conforming to PROJECT.md schema."""
    # Sanitize BME280 error states (e.g. -148.5C on I2C bus error)
    if temp is not None:
        try:
            t_val = float(temp)
            if t_val < -40.0 or t_val > 85.0 or t_val == -148.5:
                temp = None
            else:
                temp = round(t_val, 1)
        except (ValueError, TypeError):
            temp = None

    if hum is not None:
        try:
            h_val = float(hum)
            if h_val < 0.0 or h_val > 100.0 or (temp is None and h_val == 0.0):
                hum = None
            else:
                hum = round(h_val, 1)
        except (ValueError, TypeError):
            hum = None

    if press is not None:
        try:
            p_val = float(press)
            if p_val < 300.0 or p_val > 1200.0 or (temp is None and p_val > 1150.0):
                press = None
            else:
                press = round(p_val, 1)
        except (ValueError, TypeError):
            press = None

    # Sanitize PMS7003 particle values
    pms_ok = False
    if pm25 is not None:
        try:
            p25_val = float(pm25)
            if 0.0 <= p25_val <= 1000.0:
                pm25 = round(p25_val, 1)
                pms_ok = True
            else:
                pm25 = min(max(round(p25_val, 1), 0.0), 1000.0)
        except (ValueError, TypeError):
            pm25 = 15.0
    else:
        pm25 = 15.0

    pm1 = round(float(pm1), 1) if pm1 is not None else round(pm25 * 0.75, 1)
    pm10 = round(float(pm10), 1) if pm10 is not None else round(pm25 * 1.25, 1)

    # Check if BME280 is stuck on static emergency fallback constants or missing
    is_bme_fallback = (temp is not None and round(float(temp), 1) == 29.5 and 
                       hum is not None and round(float(hum), 1) == 65.0 and 
                       press is not None and round(float(press), 1) == 1012.0)
    
    if is_bme_fallback:
        bme_status_str = "DEGRADED_FROZEN"
    elif temp is not None and hum is not None:
        bme_status_str = "OK"
    else:
        bme_status_str = "DISCONNECTED"

    computed_health = sensor_health or {
        "pms7003": "OK" if pms_ok else "ERROR",
        "bme280": bme_status_str,
        "rain": "OK"
    }
    if isinstance(computed_health, dict) and is_bme_fallback:
        computed_health["bme280"] = "DEGRADED_FROZEN"

    return {
        "schema_version": "1.0",
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "campus_code": "KARACHI",
        "firmware_version": "v3.5.0-HARDWARE-SERIAL",
        "sequence_number": int(seq),
        "timestamp_epoch": int(time.time()),
        "pm1": pm1,
        "pm2_5": pm25,
        "pm10": pm10,
        "temperature": temp if temp is not None else 29.5,
        "humidity": hum if hum is not None else 65.0,
        "pressure": press if press is not None else 1012.0,
        "gas_resistance_kohm": round(float(gas), 2) if gas is not None else None,
        "rain_flag": bool(rain),
        "rain_adc": int(rain_adc) if rain_adc is not None else None,
        "sensor_health": computed_health,
        "transmission_mode": "SERIAL_BRIDGE"
    }


def parse_serial_line(line, current_data):
    """Parses a serial line using either structured JSON or regex fallback.
    
    Returns:
        tuple: (parsed_payload_dict or None, is_cycle_end)
    """
    clean_line = line.strip()
    if not clean_line:
        return None, False

    # 1. Structured JSON Line Detection
    json_candidate = None
    if clean_line.startswith("[JSON_TELEMETRY]"):
        json_candidate = clean_line.replace("[JSON_TELEMETRY]", "").strip()
    elif clean_line.startswith("{") and clean_line.endswith("}"):
        json_candidate = clean_line

    if json_candidate:
        try:
            parsed = json.loads(json_candidate)
            if isinstance(parsed, dict) and any(k in parsed for k in ("device_uid", "pm2_5", "pm25", "temperature", "sequence_number")):
                # Extract and normalize
                seq = parsed.get("sequence_number", 1)
                pm1 = parsed.get("pm1", parsed.get("pm1_0"))
                pm25 = parsed.get("pm2_5", parsed.get("pm25"))
                pm10 = parsed.get("pm10")
                temp = parsed.get("temperature", parsed.get("temperature_c"))
                hum = parsed.get("humidity", parsed.get("humidity_pct"))
                press = parsed.get("pressure", parsed.get("pressure_hpa"))
                rain = parsed.get("rain_flag", False)
                gas = parsed.get("gas_resistance_kohm", parsed.get("gas_resistance"))
                health = parsed.get("sensor_health")
                
                payload = build_telemetry_payload(seq, pm1, pm25, pm10, temp, hum, press, rain, gas, health)
                return payload, True
        except json.JSONDecodeError:
            pass

    # 2. Fallback ASCII Regex Parsing
    is_cycle_end = False

    # PMS7003 Pattern
    m_pms = re.search(r"PM1\.0:\s*([\d\.]+)\s*\|\s*PM2\.5:\s*([\d\.]+)\s*\|\s*PM10:\s*([\d\.]+)", clean_line, re.IGNORECASE)
    if m_pms:
        p1 = float(m_pms.group(1))
        p25 = float(m_pms.group(2))
        p10 = float(m_pms.group(3))
        # Validate physical particulate range
        if 0.0 <= p25 <= 1000.0 and 0.0 <= p10 <= 1500.0:
            current_data["pm1"] = p1
            current_data["pm2_5"] = p25
            current_data["pm10"] = p10
    else:
        m_pm25 = re.search(r"PM2\.5:\s*([\d\.]+)", clean_line, re.IGNORECASE)
        if m_pm25:
            p25 = float(m_pm25.group(1))
            if 0.0 <= p25 <= 1000.0:
                current_data["pm2_5"] = p25

    # BME280 Pattern
    m_bme = re.search(r"Temp(?:erature)?:\s*([\d\.-]+)\s*C?\s*\|\s*Hum(?:idity)?:\s*([\d\.]+)\s*%\s*\|\s*Press(?:ure)?:\s*([\d\.]+)", clean_line, re.IGNORECASE)
    if m_bme:
        t = float(m_bme.group(1))
        h = float(m_bme.group(2))
        p = float(m_bme.group(3))
        # Filter out hardware I2C error states (-148.5C, 0% hum, 1179.7 hPa)
        if -40.0 <= t <= 85.0 and t != -148.5 and 0.0 <= h <= 100.0 and 300.0 <= p <= 1200.0:
            current_data["temp"] = t
            current_data["hum"] = h
            current_data["press"] = p
        else:
            current_data["temp"] = None
            current_data["hum"] = None
            current_data["press"] = None

    # Gas Pattern
    m_gas = re.search(r"Gas(?:\s*Resistance)?:\s*([\d\.]+)", clean_line, re.IGNORECASE)
    if m_gas:
        current_data["gas"] = float(m_gas.group(1))

    # Rain Pattern: Parse both raw ADC count and Rain Status / Rain Flag
    m_rain_adc = re.search(r"Raw ADC:\s*(\d+)", clean_line, re.IGNORECASE)
    if m_rain_adc:
        adc_val = int(m_rain_adc.group(1))
        current_data["rain_adc"] = adc_val
        # Physical rain plate threshold: <= 2800 indicates moisture/rain, > 2800 is dry
        current_data["rain"] = (adc_val <= 2800)

    # Match explicit string indicators e.g. "Rain Flag: YES (Wet)", "Status: HEAVY RAIN", "Rain: Wet"
    if re.search(r"Rain(?:\s*Flag)?:\s*(?:YES|Wet|True|1)|Status:\s*(?:HEAVY RAIN|MODERATE RAIN|LIGHT RAIN|RAIN|DROPLETS|WET)", clean_line, re.IGNORECASE) or "rain_flag\":true" in clean_line:
        current_data["rain"] = True
    elif re.search(r"Rain(?:\s*Flag)?:\s*(?:NO|Dry|False|0)|Status:\s*DRY", clean_line, re.IGNORECASE) or "rain_flag\":false" in clean_line:
        if current_data.get("rain_adc") is not None:
            current_data["rain"] = (current_data["rain_adc"] <= 2800)
        else:
            current_data["rain"] = False

    # Cycle Separators
    if "--------------------------------------------------------" in clean_line or "[HTTP PUSH]" in clean_line or "[CYCLE_END]" in clean_line:
        is_cycle_end = True

    return None, is_cycle_end


def run_bridge(preferred_port=None, baudrate=115200):
    """Main daemon runner with infinite auto-recovery loop, dynamic COM scanning, and dual MQTT publishing."""
    print("=" * 70)
    print("  AirSense Pakistan: USB Serial Live Bridge & Dual MQTT Daemon  ")
    print("=" * 70)
    print(f"Preferred Port: {preferred_port or 'AUTO-DETECT'}")
    print(f"Baud Rate:      {baudrate}")
    print(f"MQTT Brokers:   HiveMQ (broker.hivemq.com) & EMQX (broker.emqx.io)")
    print(f"Local API:      {API_ENDPOINT}")
    print("=" * 70)

    # Initialize Dual Broker MQTT Engine
    mqtt_publisher = DualBrokerMqttPublisher()

    current_data = {
        "pm1": 7.0, "pm2_5": 9.0, "pm10": 10.0,
        "temp": 29.5, "hum": 65.0, "press": 1012.0,
        "gas": 45.2, "rain": False
    }
    seq = 1
    last_push_time = 0
    backoff = 1.0
    max_backoff = 8.0

    while True:
        ser = None
        current_port = None
        try:
            current_port = find_esp32_port(preferred_port)
            if not current_port:
                jitter = random.uniform(0.1, 0.5)
                sleep_duration = min(backoff + jitter, max_backoff)
                print(f"[BRIDGE SCAN] No serial COM ports found. Retrying scan in {sleep_duration:.1f}s...")
                time.sleep(sleep_duration)
                backoff = min(backoff * 1.5, max_backoff)
                continue

            print(f"[BRIDGE ATTEMPT] Connecting to serial port {current_port} at {baudrate} baud...")
            ser = serial.Serial(current_port, baudrate=baudrate, timeout=2.0)
            print(f"\n[BRIDGE SUCCESS] Connected to {current_port}! Streaming live hardware telemetry...")
            backoff = 1.0  # Reset backoff on successful connection

            while True:
                raw_bytes = ser.readline()
                if not raw_bytes:
                    continue

                line = raw_bytes.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                print(f"[ESP32 RAW] {line}")

                payload, is_cycle_end = parse_serial_line(line, current_data)
                now_t = time.time()

                if payload:
                    # Direct structured JSON packet received
                    mqtt_publisher.publish(payload)
                    push_to_local_api(payload)
                    print(f"[DASHBOARD LIVE] Pushed JSON Packet #{payload['sequence_number']} -> PM2.5={payload['pm2_5']} ug/m3 | Temp={payload['temperature']}C | Hum={payload['humidity']}% | Rain={payload['rain_flag']} | Status: OK")
                    seq = payload['sequence_number'] + 1
                    last_push_time = now_t

                elif is_cycle_end and (now_t - last_push_time >= 0.8):
                    # Cycle boundary reached for ASCII debug readings
                    last_push_time = now_t
                    payload = build_telemetry_payload(
                        seq,
                        current_data["pm1"], current_data["pm2_5"], current_data["pm10"],
                        current_data["temp"], current_data["hum"], current_data["press"],
                        current_data["rain"], current_data.get("gas"),
                        rain_adc=current_data.get("rain_adc")
                    )
                    mqtt_publisher.publish(payload)
                    push_to_local_api(payload)
                    print(f"[DASHBOARD LIVE] Pushed Cycle #{seq} -> PM2.5={payload['pm2_5']} ug/m3 | Temp={payload['temperature']}C | Hum={payload['humidity']}% | Rain={payload['rain_flag']} | Status: OK")
                    seq += 1

        except serial.SerialException as se:
            err_str = str(se)
            if "PermissionError" in err_str or "Access is denied" in err_str:
                print(f"[BRIDGE WAITING] Port {current_port} is busy or open in another application (e.g. Arduino IDE). Close conflicting apps. Retrying in 2s...")
            else:
                print(f"[BRIDGE DISCONNECT] Serial connection lost on {current_port}: {se}.")
            
            jitter = random.uniform(0.1, 0.4)
            sleep_duration = min(backoff + jitter, max_backoff)
            print(f"[BRIDGE RECOVER] Scanning for re-connection in {sleep_duration:.1f}s...")
            time.sleep(sleep_duration)
            backoff = min(backoff * 1.5, max_backoff)

        except KeyboardInterrupt:
            print("\n[AirSense] Bridge stopped by user.")
            break

        except Exception as ex:
            print(f"[BRIDGE ERROR] Unexpected exception: {ex}.")
            jitter = random.uniform(0.1, 0.4)
            sleep_duration = min(backoff + jitter, max_backoff)
            print(f"[BRIDGE RECOVER] Retrying in {sleep_duration:.1f}s...")
            time.sleep(sleep_duration)
            backoff = min(backoff * 1.5, max_backoff)

        finally:
            if ser and ser.is_open:
                try:
                    ser.close()
                except Exception:
                    pass


if __name__ == "__main__":
    cli_port = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        arg = sys.argv[1].strip()
        if arg.upper() not in ("AUTO", "DEFAULT"):
            cli_port = arg

    try:
        run_bridge(cli_port)
    except KeyboardInterrupt:
        print("\n[AirSense] Daemon exited cleanly.")

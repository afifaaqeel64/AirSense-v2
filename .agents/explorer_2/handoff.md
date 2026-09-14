# AirSense Pakistan: Explorer 2 (Python Bridge & MQTT Specialist) Handoff Report

## 1. Observation

Directly observed files, lines, configurations, and empirical test results:

### 1.1 MQTT Broker Configurations Across Codebase
- **ESP32 Firmware**: `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino:32-34`
  ```cpp
  const char* MQTT_BROKER = "broker.emqx.io";
  const int   MQTT_PORT   = 1883;
  const char* MQTT_TOPIC  = "airsense/karachi/bic_roof/telemetry";
  ```
- **Serial Live Bridge**: `scripts/airsense_serial_live_bridge.py:68-76`
  ```python
  client = mqtt.Client(client_id="airsense-bridge-" + str(int(time.time())))
  client.connect("broker.emqx.io", 1883, 60)
  client.loop_start()
  push_to_api.mqtt_client = client
  push_to_api.mqtt_client.publish(
      "airsense/karachi/bic_roof/telemetry",
      payload=json.dumps(payload),
      qos=0
  )
  ```
- **FastAPI Ingest Router**: `apps/api/routers/ingest_router.py:23-33`
  ```python
  def _broadcast_to_hivemq(payload_data: dict):
      try:
          mqtt_publish.single(
              "airsense/karachi/bic_roof/telemetry",
              payload=json.dumps(payload_data),
              hostname="broker.hivemq.com",
              port=1883,
              keepalive=10
          )
  ```
- **MQTT Live Forwarder**: `scripts/airsense_mqtt_live_forwarder.py:16-18`
  ```python
  BROKER_HOST = "broker.hivemq.com"
  BROKER_PORT = 1883
  BROKER_TOPIC = "airsense/#"
  ```
- **Public Dashboard**: `public/hardware.html:880-882`
  ```javascript
  const mqttHost = "broker.hivemq.com";
  const mqttPort = isHttps ? 8884 : 8000;
  const mqttPath = "/mqtt";
  ```
- **Public Index Dashboard**: `public/index.html:872-875`
  ```javascript
  const mqttBroker = "broker.emqx.io"; 
  const isHttps = window.location.protocol === "https:";
  const mqttPort = isHttps ? 8084 : 8083; 
  const mqttPath = "/mqtt";
  ```

### 1.2 Package Dependencies
- `c:/Users/HP/AirSense-v2/requirements.txt`:
  Contains `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `aiosqlite`, `asyncpg`, `alembic`, `numpy`, `pandas`, `scikit-learn`, `xgboost`, `lightgbm`, `joblib`, `httpx`, `python-dotenv`, `pytest`, `pytest-asyncio`.
  **Neither `pyserial` nor `paho-mqtt` is present in `requirements.txt`**.

### 1.3 COM Port Management
- `scripts/airsense_serial_live_bridge.py:86`:
  `port = port_name or find_esp32_port()` evaluates `port` exactly once before the `while True:` reconnect loop.
- `run_bridge_daemon.bat:3`: `py -u scripts\airsense_serial_live_bridge.py COM7`
- `start_serial_bridge.bat:10`: `py -u scripts\airsense_serial_live_bridge.py COM7`
- `run_airsense_all_in_one.bat:13`: `start /min "AirSense Serial Bridge" cmd /c "py -u scripts\airsense_serial_live_bridge.py COM7"`

### 1.4 Forwarder Crash Points
- `scripts/airsense_mqtt_live_forwarder.py:101-108`:
  ```python
  try:
      client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
      client.loop_forever()
  except KeyboardInterrupt:
      client.disconnect()
  except Exception as e:
      print(f"[MQTT FATAL] Error: {e}")
  ```
  If `connect()` fails, the script terminates immediately with no retry loop.
- `scripts/airsense_serial_forwarder.py:33-37`:
  ```python
  try:
      ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
  except Exception as e:
      print(f"[ERROR] Could not open {COM_PORT}: {e}")
      return
  ```
  If `COM_PORT` (`COM11`) fails to open on boot, the function returns and exits.

### 1.5 Empirical Broker Verification Results
- `broker.hivemq.com`: Port 1883 (TCP) and Port 8884 (WSS / TLS) tested via `probe_wss.py`: **Connected and received probe telemetry packet**.
- `broker.emqx.io`: Port 1883 (TCP) and Port 8084 (WSS / TLS) tested via `probe_wss.py`: **Connected and received probe telemetry packet**.

---

## 2. Logic Chain

1. **Broker Split-Brain Causes Dashboard Offline State**:
   - Hardware ESP32 firmware publishes to `broker.emqx.io:1883` on `airsense/karachi/bic_roof/telemetry` (Observation 1.1).
   - Python serial bridge publishes to `broker.emqx.io:1883` on `airsense/karachi/bic_roof/telemetry` (Observation 1.1).
   - Public Vercel dashboard (`public/hardware.html`) subscribes to `broker.hivemq.com:8884/mqtt` on `airsense/#` and `airsense/karachi/bic_roof/telemetry` (Observation 1.1).
   - Because `broker.emqx.io` and `broker.hivemq.com` are completely independent public brokers with no message bridging between them, packets sent by ESP32 or serial bridge to EMQX never reach HiveMQ.
   - Consequently, any client accessing `public/hardware.html` receives no MQTT packets and remains permanently in `🔴 ESP32 DISCONNECTED` state unless the local FastAPI server happens to be running and relaying packets to HiveMQ via HTTP POST.

2. **Static Port Binding Causes Bridge Hangs**:
   - Launch scripts pass `COM7` as an explicit argument (Observation 1.3).
   - `airsense_serial_live_bridge.py` uses `port_name` (`COM7`) and skips dynamic port discovery (Observation 1.3).
   - When the ESP32 is attached to any other port (`COM3`, `COM4`, `COM8`, `COM11`) or changes port on USB re-plug, the bridge repeatedly fails to open `COM7` and never searches for active devices.

3. **Fresh Deployments Fail Without Core Dependencies**:
   - `pyserial` and `paho-mqtt` are essential for serial communication and MQTT dispatch.
   - Their absence from `requirements.txt` (Observation 1.2) means automated build/deploy environments and fresh virtual environments will fail with `ModuleNotFoundError`.

4. **Single-Attempt MQTT Connect Causes Forwarder Death**:
   - In `airsense_mqtt_live_forwarder.py`, `client.connect()` is called outside a retry loop (Observation 1.4).
   - Any transient network interruption during startup kills the forwarder process.

---

## 3. Caveats

1. **Physical Hardware Presence**:
   - Physical ESP32 hardware and COM port connectivity could not be physically hot-plugged during this read-only audit turn; analysis was verified via code inspection, port enumeration tools, and mock socket connections.
2. **Public Broker Rate Limits**:
   - Both `broker.hivemq.com` and `broker.emqx.io` are shared public test brokers. While currently responsive, enterprise production deployment should ideally utilize a dedicated HiveMQ Cloud or EMQX Cloud instance with TLS credentials.

---

## 4. Conclusion

The AirSense-v2 Python bridge and MQTT streaming subsystem has two primary root causes preventing reliable 24/7 cloud connectivity:
1. **The Broker Disconnect**: Publishers broadcast to `broker.emqx.io` while consumers listen on `broker.hivemq.com`.
2. **Static COM Port Binding**: The bridge daemon does not dynamically re-scan COM ports during reconnect loops.

### Actionable Remediation Plan:
1. **Unify Publishing**: Update `scripts/airsense_serial_live_bridge.py` to publish simultaneously to **BOTH** `broker.hivemq.com` and `broker.emqx.io` (or standardize the entire project on `broker.hivemq.com` across firmware, bridge, and frontend).
2. **Implement Dynamic Port Scanning**: Enhance `find_esp32_port()` to run inside the reconnect loop, dynamically re-scanning USB descriptors on every attempt.
3. **Hardened Error Handling**: Implement `paho-mqtt` v2.0 callback API compliance and infinite auto-reconnect loops across all forwarders.
4. **Update `requirements.txt`**: Add `pyserial>=3.5` and `paho-mqtt>=2.0.0`.

---

## 5. Verification Method

### 5.1 Programmatic MQTT Routing Verification
Run the verification test probe to confirm packet delivery to both HiveMQ and EMQX:
```powershell
py c:/Users/HP/AirSense-v2/.agents/explorer_2/probe_wss.py
```

### 5.2 Unit and End-to-End Test Suite
Execute the project pytest suite:
```powershell
py -m pytest tests/
```

### 5.3 Files to Inspect for Fix Application
- `c:/Users/HP/AirSense-v2/scripts/airsense_serial_live_bridge.py`
- `c:/Users/HP/AirSense-v2/scripts/airsense_mqtt_live_forwarder.py`
- `c:/Users/HP/AirSense-v2/requirements.txt`
- `c:/Users/HP/AirSense-v2/public/hardware.html`
- `c:/Users/HP/AirSense-v2/public/index.html`
- `c:/Users/HP/AirSense-v2/run_bridge_daemon.bat`

# Handoff Report — Explorer 1 (Firmware & Hardware Communication Specialist)

**Target System**: AirSense-v2 ESP32 Firmware, Sensor Interfaces, Serial Bridges, Cloud MQTT Telemetry, and Web Dashboard Subscribers  
**Author**: Explorer 1  
**Date**: September 2, 2026  
**Reference Analysis**: `c:/Users/HP/AirSense-v2/.agents/explorer_1/analysis.md`

---

## 1. Observation

### Exact File Paths, Line Numbers, and Code Verifications

1. **Broker Inconsistency Between Dashboard and Firmware**:
   - `c:/Users/HP/AirSense-v2/public/hardware.html` (Lines 880–881):
     ```javascript
     const mqttHost = "broker.hivemq.com";
     const mqttPort = isHttps ? 8884 : 8000;
     ```
   - `c:/Users/HP/AirSense-v2/scripts/airsense_mqtt_live_forwarder.py` (Lines 16–17):
     ```python
     BROKER_HOST = "broker.hivemq.com"
     BROKER_PORT = 1883
     ```
   - `c:/Users/HP/AirSense-v2/scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` (Lines 32–34):
     ```cpp
     const char* MQTT_BROKER = "broker.emqx.io";
     const int   MQTT_PORT   = 1883;
     const char* MQTT_TOPIC  = "airsense/karachi/bic_roof/telemetry";
     ```
   - `c:/Users/HP/AirSense-v2/scripts/airsense_serial_live_bridge.py` (Line 69):
     ```python
     client.connect("broker.emqx.io", 1883, 60)
     ```
   - `c:/Users/HP/AirSense-v2/public/index.html` (Lines 872–874):
     ```javascript
     const mqttBroker = "broker.emqx.io"; 
     const isHttps = window.location.protocol === "https:";
     const mqttPort = isHttps ? 8084 : 8083; 
     ```

2. **Missing JSON Output on Serial in ESP32 Firmware**:
   - `c:/Users/HP/AirSense-v2/scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` (Lines 391–415):
     `snprintf(jsonPayload, ...)` formats the JSON string and sends it via `publishMQTT()` and `HTTPClient http; http.POST(jsonPayload);`, but `Serial.println(jsonPayload)` is never called.
   - `c:/Users/HP/AirSense-v2/scripts/airsense_serial_forwarder.py` (Line 49):
     ```python
     if line.startswith("{") and line.endswith("}") and "AIRSENSE-NODE" in line:
     ```
     Because the firmware never prints `{...}` to Serial, this condition is never satisfied.
   - `c:/Users/HP/AirSense-v2/scripts/airsense_serial_live_bridge.py` (Lines 109–120):
     Forces the script to parse raw debug strings via regular expressions:
     ```python
     m_pms = re.search(r"PM1\.0:\s*([\d\.]+)\s*\|\s*PM2\.5:\s*([\d\.]+)\s*\|\s*PM10:\s*([\d\.]+)", line)
     m_bme = re.search(r"Temp:\s*([\d\.]+)\s*C\s*\|\s*Humidity:\s*([\d\.]+)\s*%\s*\|\s*Pressure:\s*([\d\.]+)", line)
     ```

3. **Silent Sensor Failure Masking**:
   - `c:/Users/HP/AirSense-v2/scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` (Lines 349–358):
     ```cpp
     float pm1 = 7.0, pm25 = 9.0, pm10 = 10.0;
     if (readPMS7003(pm1, pm25, pm10)) { ... }
     float temp = 29.5, hum = 65.0, press = 1012.0;
     readBME280(temp, hum, press);
     ```
     If `readPMS7003` returns `false` (lines 253–278), `pm1=7.0, pm25=9.0, pm10=10.0` are preserved.
     If `bme_found` is false (line 205), `temp=29.5, hum=65.0, press=1012.0` are returned.
     These dummy values are then injected into `jsonPayload` and transmitted to the cloud.

4. **Blocking Sockets in Network Handshake**:
   - `c:/Users/HP/AirSense-v2/scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` (Lines 44, 67):
     ```cpp
     if (!mqttClient.connect(MQTT_BROKER, MQTT_PORT, 5000)) { ... }
     while (mqttClient.available() < 4 && millis() - t0 < 3000) delay(10);
     ```
     Blocks the main thread for up to 5000ms + 3000ms = 8000ms during network stalls.

5. **Hardcoded Port & Fatal Exit in Serial Forwarder**:
   - `c:/Users/HP/AirSense-v2/scripts/airsense_serial_forwarder.py` (Lines 20, 33–37):
     ```python
     COM_PORT = "COM11"
     ...
     except Exception as e:
         print(f"[ERROR] Could not open {COM_PORT}: {e}")
         return
     ```
     Exits immediately instead of retrying or scanning ports.

---

## 2. Logic Chain

1. **Step 1 (Root Cause of Dashboard Disconnection)**:
   - The hardware firmware (`airsense_esp32_firmware.ino`) and Python serial bridge (`airsense_serial_live_bridge.py`) publish telemetry packets to `broker.emqx.io:1883` on topic `airsense/karachi/bic_roof/telemetry`.
   - The dedicated hardware dashboard (`public/hardware.html`) and the campus MQTT forwarder (`scripts/airsense_mqtt_live_forwarder.py`) connect to `broker.hivemq.com`.
   - Because EMQX and HiveMQ are separate, independent public MQTT brokers that do not bridge with each other, packets published to EMQX never reach clients connected to HiveMQ.
   - Therefore, `hardware.html` never receives packets over its WebSocket and permanently displays `🔴 ESP32 DISCONNECTED`.

2. **Step 2 (Root Cause of Serial Ingestion Incompatibility)**:
   - `airsense_serial_forwarder.py` filters incoming serial lines using `if line.startswith("{") and line.endswith("}")`.
   - `airsense_esp32_firmware.ino` formats `jsonPayload` internally but only sends it via network sockets; it prints only human-readable strings to Serial (`[READING] PMS7003...`).
   - Consequently, `airsense_serial_forwarder.py` never detects a JSON line, forwarding zero records.
   - `airsense_serial_live_bridge.py` had to be created as a workaround using regex scraping on the human-readable text.

3. **Step 3 (Root Cause of Silent Sensor Outages)**:
   - When the physical PMS7003 or BME280 sensor experiences a wire disconnect or framing error, the driver functions fail.
   - Rather than propagating `null` or setting an error state, default initialization values (`7.0, 9.0, 10.0, 29.5, 65.0, 1012.0`) are retained and embedded into `jsonPayload`.
   - The cloud ingestion and UI treat these values as active live readings, hiding physical sensor failure from operators.

4. **Step 4 (Root Cause of Loop Stalls and Jitter)**:
   - When Wi-Fi connectivity is intermittent, `mqttClient.connect()` attempts a 5-second blocking TCP handshake followed by a 3-second busy-wait loop for CONNACK.
   - This causes the ESP32 `loop()` to freeze for up to 8 seconds, delaying sensor polling and causing UART/I2C buffer overruns.

---

## 3. Caveats

1. **Public Broker Rate Limiting & SLA**:
   Both `broker.emqx.io` and `broker.hivemq.com` are free public sandbox brokers. While excellent for testing and demonstrations, they have no uptime SLA and can occasionally rate-limit or disconnect clients under high global traffic.
2. **Physical Sensor Availability in Local Workspace**:
   The current testing environment is a local software workstation. Flashing the physical ESP32 requires the physical USB connection to COM7.
3. **Wokwi Simulation vs Physical Hardware**:
   The Wokwi simulation sketch (`Wokwi Simulation Practice/sketch.ino`) uses DHT22 and potentiometers, while the physical deployment firmware (`airsense_esp32_firmware.ino`) uses direct BME280 I2C registers and PMS7003 UART. The two sketches should be maintained as separate targets (simulation vs physical hardware).

---

## 4. Conclusion

The AirSense-v2 telemetry pipeline requires five targeted, non-destructive fixes:
1. **Unify the MQTT Broker**: Point `public/hardware.html` and `scripts/airsense_mqtt_live_forwarder.py` to `broker.emqx.io` (matching `airsense_esp32_firmware.ino`, `public/index.html`, and `airsense_serial_live_bridge.py`).
2. **Serial JSON Telemetry Output**: Add `Serial.print("[JSON_TELEMETRY] "); Serial.println(jsonPayload);` in `airsense_esp32_firmware.ino`.
3. **Explicit Sensor Status & Null Handling**: Send `null` or negative error codes with health flags in the JSON payload when sensors are disconnected.
4. **Non-Blocking Network Handshakes**: Reduce MQTT connect timeout to 1000ms and eliminate blocking busy-wait loops in the firmware.
5. **Dynamic Serial Port Discovery**: Update Python bridge scripts to auto-detect ESP32 COM ports and retry indefinitely with exponential backoff upon permission errors.

---

## 5. Verification Method

### Test 1: Broker & Topic End-to-End Routing Verification
Run a Python verification test using `paho-mqtt` to publish to `broker.emqx.io:1883` on topic `airsense/karachi/bic_roof/telemetry` and verify instantaneous reception on the WebSocket client subscribing to `wss://broker.emqx.io:8084/mqtt`.

Command:
```powershell
python -c "
import paho.mqtt.client as mqtt, time, json
def on_msg(c, u, m): print('[TEST PASS] Received:', m.payload.decode())
client = mqtt.Client(client_id='test-sub-' + str(int(time.time())))
client.on_message = on_msg
client.connect('broker.emqx.io', 1883, 60)
client.subscribe('airsense/karachi/bic_roof/telemetry')
client.loop_start()
time.sleep(1)
payload = {'test': 'packet', 'timestamp': time.time()}
client.publish('airsense/karachi/bic_roof/telemetry', json.dumps(payload))
time.sleep(2)
client.loop_stop()
"
```

### Test 2: Inspect Unified Broker in Frontend and Scripts
Inspect `public/hardware.html` and verify `mqttHost` is set to `"broker.emqx.io"`, `mqttPort` is `8084` (for HTTPS) / `8083` (for HTTP), and path is `"/mqtt"`.

### Test 3: Firmware Compilation Check
Verify that `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` contains valid C++ syntax and compiles cleanly on Arduino IDE / ESP32 core v2.0+.

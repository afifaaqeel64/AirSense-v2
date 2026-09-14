# AirSense-v2: Firmware, Hardware Telemetry & Communication Architecture Deep-Dive Analysis

**Author**: Explorer 1 (Firmware & Hardware Communication Specialist)  
**Date**: September 2, 2026  
**Target System**: ESP32 Dev Module (WROOM-32 / ESP32-D0WDQ6), Sensor Peripherals, USB Serial Bridges, Cloud MQTT Broker, and Web Dashboard Telemetry

---

## Executive Summary

A comprehensive, end-to-end investigation of all ESP32 firmware implementations, sensor drivers, pin assignments, communication protocols, Python bridge scripts, and frontend WebSocket subscriber code in `c:/Users/HP/AirSense-v2` was conducted.

The investigation uncovered **several critical root causes** explaining why the hardware telemetry pipeline intermittently stalls, goes offline, or shows disconnected states on the cloud dashboard:
1. **MQTT Broker & WebSockets Mismatch**: `airsense_esp32_firmware.ino`, `airsense_serial_live_bridge.py`, and `public/index.html` use `broker.emqx.io`, while `airsense_mqtt_live_forwarder.py` and `public/hardware.html` use `broker.hivemq.com`. Because the hardware and parts of the dashboard/forwarder subscribe to different cloud brokers, telemetry is partitioned and lost.
2. **Missing Serial JSON Telemetry in Firmware**: `airsense_esp32_firmware.ino` only outputs human-readable diagnostic strings over `Serial` (e.g., `[READING] PMS7003 -> ...`) and never emits the structured `jsonPayload` to `Serial`. As a result, standard JSON forwarders (`airsense_serial_forwarder.py`) fail completely, and the live serial bridge had to rely on brittle regex scraping.
3. **Silent Sensor Failure Masking**: When PMS7003 or BME280 fails to respond, `airsense_esp32_firmware.ino` injects hardcoded dummy readings (`7.0, 9.0, 10.0, 29.5, 65.0, 1012.0`) into the transmitted JSON payload rather than sending `null` or setting an error status flag. This masks hardware faults and transmits artificial data.
4. **Blocking Network Delays**: The custom zero-dependency MQTT client in `airsense_esp32_firmware.ino` has blocking socket timeouts of up to 5 seconds during connection and 3 seconds during CONNACK polling, stalling sensor sampling and local operations for up to 8 seconds whenever network conditions fluctuate.
5. **Hardcoded Ports and Permissions Lockouts**: `airsense_serial_forwarder.py` hardcodes `COM11` (which exits immediately on COM7), while `flash_now.py` hardcodes temporary Arduino cache paths.

---

## 1. Hardware Pinout & Sensor Drivers Configuration

The workspace contains two distinct firmware implementations:
- **Production Deployment Firmware**: `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` (Physical ESP32 node targeting PMS7003 laser particulate sensor, Bosch BME280 I2C sensor, analog raindrop sensor, and MicroSD SPI logging).
- **Simulation Practice Firmware**: `Wokwi Simulation Practice/sketch.ino` (Virtual simulation targeting DHT22, MQ135 analog gas potentiometer, PM2.5 potentiometer, SSD1306 OLED, LEDs, Buzzer, and MicroSD).

### Detailed Pin Assignment Matrix

| Peripheral / Sensor | Physical Firmware (`airsense_esp32_firmware.ino`) | Simulation Firmware (`sketch.ino` & `diagram.json`) | Bus / Signal Type | Electrical / Hardware Notes |
|---|---|---|---|---|
| **Plantower PMS7003** (Laser Dust) | **GPIO 16** (ESP32 RX2 -> PMS Pin 4 TX)<br>**GPIO 17** (ESP32 TX2 -> PMS Pin 5 RX) | *N/A* (Simulated via Potentiometer on GPIO 34) | HardwareSerial UART2 (9600 baud, 8N1) | Active laser scattering. Requires 5V VCC, 3.3V UART logic. Continuous 32-byte active frame mode. |
| **Bosch BME280** (Temp, Hum, Press) | **GPIO 21** (SDA)<br>**GPIO 22** (SCL) | *N/A* (DHT22 on GPIO 15 used instead) | I2C (Wire standard mode, default address `0x76`, fallback `0x77`) | Zero-library register driver. Compensation math implemented via 32-bit & 64-bit integer arithmetic. |
| **DHT22 / AM2302** (Temp, Hum) | *Not used in production* | **GPIO 15** (Data) | 1-Wire Digital (Adafruit DHT) | Pull-up resistor required. |
| **Rain Sensor** (Raindrop board) | **GPIO 34** (Analog AO) | **GPIO 32** (Analog AO)<br>**GPIO 13** (Digital DO) | ADC1 Input-only pin (GPIO 34/32) | Multi-sampled 8x with 2ms interval. ADC 0 (heavy rain) to 4095 (bone dry). Wet threshold < 2800. |
| **MQ-135** (Air Quality / Gas) | *Not wired in production* | **GPIO 35** (Analog AO) | ADC1 Input-only pin | Requires 24-48h pre-heating for heater coil. |
| **MicroSD SPI Module** | **GPIO 5** (CS)<br>GPIO 18 (SCK), GPIO 19 (MISO), GPIO 23 (MOSI) | **GPIO 5** (CS)<br>GPIO 18 (SCK), GPIO 19 (MISO), GPIO 23 (MOSI) | Hardware SPI (VSPI) | Formatted FAT32. Appends records to `/telemetry.csv` or `/airsense_log.csv`. |
| **SSD1306 128x64 OLED** | *Not wired in production* | **GPIO 21** (SDA)<br>**GPIO 22** (SCL) | I2C (`0x3C`) | Dual-page rotation every 4 seconds. |
| **Status Indicators & Actuators** | **GPIO 2** (Built-in Blue LED: Wi-Fi status) | **GPIO 25** (Green LED - Normal)<br>**GPIO 26** (Red LED - Alert)<br>**GPIO 27** (Buzzer - PWM tone) | GPIO Digital Output | Built-in LED on GPIO 2 indicates active STA connection. |

---

## 2. Telemetry Data Formats & Serialization

Three data serialization mechanisms exist across the hardware and software layers:

### A. JSON Telemetry Packet (MQTT & HTTP Ingestion)
Generated in `airsense_esp32_firmware.ino` (lines 391–395) and mirrored in Python bridges (`airsense_serial_live_bridge.py`, `airsense_live_hardware_feeder.py`):
```json
{
  "schema_version": "1.0",
  "device_uid": "AIRSENSE-NODE-KHI-01",
  "station_code": "BIC-KHI-ROOF-01",
  "campus_code": "KARACHI",
  "firmware_version": "v3.5.0-MQTT",
  "sequence_number": 142,
  "timestamp_epoch": 1725270546,
  "pm1": 7.0,
  "pm2_5": 9.0,
  "pm10": 10.0,
  "temperature": 29.5,
  "humidity": 65.0,
  "pressure": 1012.0,
  "rain_flag": false
}
```

#### Field Specifications:
- `schema_version` (*string*): `"1.0"`
- `device_uid` (*string*): `"AIRSENSE-NODE-KHI-01"`
- `station_code` (*string*): `"BIC-KHI-ROOF-01"`
- `campus_code` (*string*): `"KARACHI"`
- `firmware_version` (*string*): `"v3.5.0-MQTT"` / `"v3.5.0-HARDWARE-SERIAL"`
- `sequence_number` (*unsigned long / integer*): Monotonically increasing counter per reading cycle.
- `timestamp_epoch` (*unsigned long / integer*): Real-world Unix epoch synchronized via NTP (`time(NULL)`).
- `pm1`, `pm2_5`, `pm10` (*float*): Particulate matter concentrations in $\mu\text{g/m}^3$.
- `temperature` (*float*): Ambient temperature in $^\circ\text{C}$.
- `humidity` (*float*): Relative humidity in $\%$.
- `pressure` (*float*): Atmospheric pressure in $\text{hPa}$.
- `rain_flag` (*boolean*): `true` when precipitation detected ($\text{ADC} < 2800$), `false` otherwise.

### B. MicroSD Card CSV Format
- In `airsense_esp32_firmware.ino` (line 385):
  `packet_seq,pm1,pm25,pm10,temp,hum,press,rain_flag`
  Example line: `142,7.0,9.0,10.0,29.5,65.0,1012.0,0`
- In `sketch.ino` (line 168):
  `Uptime_s,Temp_C,Humidity_pct,PM25_ugm3,Gas_Raw,Rain_Raw,AQI,Category`

### C. Serial Stream Output Format
Currently in `airsense_esp32_firmware.ino` (lines 351, 358, 378, 414):
```text
[READING] PMS7003 -> PM1.0: 7.0 | PM2.5: 9.0 | PM10: 10.0 ug/m3
[READING] BME280  -> Temp: 29.5 C | Humidity: 65.0 % | Pressure: 1012.0 hPa
[READING] Raindrop -> Raw ADC: 3820 | Status: DRY (No Rain) | Rain Flag: NO (Dry)
--------------------------------------------------------
```
*Critical Discrepancy*: The firmware does NOT print the formatted JSON packet to `Serial`. Standard serial consumers expecting JSON receive nothing parsable.

---

## 3. Communication Protocols & Transmission Modes

The firmware implements three concurrent transmission channels:

### 1. Serial UART (115200 Baud)
- Initialized in `setup()` via `Serial.begin(115200)`.
- Used for diagnostic messages and USB bridging to a host PC.

### 2. Autonomous Wi-Fi Station (STA) Mode
- Initialized in `setup()` via `WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASS);`.
- Performs up to 20 connection attempts with 500ms delay (10s total timeout).
- Upon connection, queries NTP servers (`pool.ntp.org`, `time.google.com`) with UTC+5 timezone offset (`configTime(5 * 3600, 0, ...)`).
- Sets GPIO 2 (Status LED) to `HIGH` when connected.

### 3. Custom Zero-Dependency Cloud MQTT Client (MQTT 3.1.1)
- Built directly over `WiFiClient` without third-party library dependencies (e.g. PubSubClient).
- Target Broker: `broker.emqx.io` (Port 1883).
- Target Topic: `airsense/karachi/bic_roof/telemetry`.
- Packet Construction:
  - **CONNECT**: Generates client ID `as-esp32-XXXXXX` from ESP32 MAC eFuse. Variable header sets 120s keep-alive. Awaits 4-byte CONNACK (`0x20 0x02 0x00 0x00`).
  - **PUBLISH**: Emits QoS 0 publish packet with dynamically encoded variable length bytes and UTF-8 JSON payload.
  - Connection Check: Evaluates `mqttClient.connected()`; if disconnected, issues `mqttClient.stop()` and reconnects.

### 4. Direct HTTP POST (Fallback)
- Uses `HTTPClient` with 800ms non-blocking timeout targeting `http://172.20.10.13:8000/api/v1/ingest/reading` with header `X-Device-Token`.

---

## 4. Fault Tolerance & Failure Analysis

### Wi-Fi Dropouts & Network Reconnection
- **Detection**: `WiFi.status() != WL_CONNECTED`.
- **In Loop**: Non-blocking timer evaluates every 30,000ms:
  ```cpp
  if (WiFi.status() != WL_CONNECTED) {
    static unsigned long last_reconn = 0;
    if (now - last_reconn > 30000) {
      last_reconn = now;
      WiFi.reconnect();
    }
  }
  ```
- **Vulnerabilities**:
  1. `publishMQTT` checks `WiFi.status() != WL_CONNECTED` and bails out, which is non-blocking when Wi-Fi is officially disconnected.
  2. However, if Wi-Fi is "connected" to an AP but internet gateway is down, `mqttClient.connect(MQTT_BROKER, MQTT_PORT, 5000)` blocks for **5000 ms** every cycle.
  3. If TCP connects but the broker hangs, `while (mqttClient.available() < 4 && millis() - t0 < 3000) delay(10);` blocks for **3000 ms**.
  4. Cumulative blocking time can reach **8 seconds per cycle**, freezing sensor sampling and serial output.

### Sensor Failures & NaN Handling
- **PMS7003 Timeout**:
  - `readPMS7003()` polls for 1000ms. If no valid frame arrives, returns `false`.
  - **Defect**: In `loop()`, variables `pm1`, `pm25`, `pm10` are initialized to `7.0, 9.0, 10.0`. If `readPMS7003()` returns `false`, these default numbers are retained and published as valid live telemetry.
- **BME280 Disconnect**:
  - `readBME280()` checks `if (!bme_found) { temp = 29.5; hum = 65.0; press = 1012.0; return; }`.
  - If BME280 is missing, hardcoded values `29.5, 65.0, 1012.0` are transmitted indefinitely.
  - If BME280 disconnects after boot, `Wire.requestFrom` reads `0xFF`, resulting in mathematical calculation overflows and garbage numbers.
- **Rain Sensor Floating ADC**:
  - If sensor wires disconnect, GPIO 34 floats, frequently reading `< 2800` and producing false "WET" rain alarms.

---

## 5. Catalog of Code Defects, Mismatches & Vulnerabilities

| # | Severity | Defect Location | Description | Impact |
|---|---|---|---|---|
| **D1** | **CRITICAL** | `public/hardware.html:880`<br>`scripts/airsense_mqtt_live_forwarder.py:16` vs<br>`airsense_esp32_firmware.ino:32`<br>`public/index.html:872` | **Broker Split / Mismatch**: `hardware.html` and `airsense_mqtt_live_forwarder.py` use `broker.hivemq.com`. `airsense_esp32_firmware.ino`, `airsense_serial_live_bridge.py`, and `index.html` use `broker.emqx.io`. | Dashboard on `/hardware` stays permanently at `🔴 ESP32 DISCONNECTED` because it listens to HiveMQ while hardware publishes to EMQX. |
| **D2** | **CRITICAL** | `airsense_esp32_firmware.ino:349-395` | **Silent Sensor Failure Masking**: Hardcoded dummy numbers (`pm1=7.0, pm25=9.0, pm10=10.0, temp=29.5, hum=65.0, press=1012.0`) are transmitted when sensors fail or disconnect. | The cloud system cannot distinguish real sensor data from unplugged/broken hardware. |
| **D3** | **HIGH** | `airsense_esp32_firmware.ino:342-415` | **Missing Serial JSON Output**: The firmware generates `jsonPayload` for MQTT and HTTP, but never calls `Serial.println(jsonPayload)`. | `airsense_serial_forwarder.py` receives no JSON, and `airsense_serial_live_bridge.py` must use fragile regexes on debug text. |
| **D4** | **HIGH** | `airsense_esp32_firmware.ino:44, 67` | **Blocking Sockets in Main Loop**: `mqttClient.connect` has a 5s timeout and CONNACK has a 3s busy-wait loop. | During network drops, loop freezes for 8s, starving sensors and serial throughput. |
| **D5** | **MEDIUM** | `airsense_serial_forwarder.py:20` | **Hardcoded Inactive Port**: `COM_PORT = "COM11"` is hardcoded, and the script exits with `return` if opening fails. | Script fails immediately on standard COM7 or other ports. |
| **D6** | **MEDIUM** | `airsense_esp32_firmware.ino:19, 23` | **Hardcoded Local Network Credentials & IP**: `WIFI_SSID = "Tracks_101"`, `API_ENDPOINT = "http://172.20.10.13:8000/..."`. | Device cannot adapt if SSID or local subnet changes without reflashing. |
| **D7** | **MEDIUM** | `airsense_esp32_firmware.ino:56-83` | **No MQTT PINGREQ / Keep-Alive Handler**: Custom MQTT client advertises 120s keep-alive but never sends PINGREQ (`0xC0 0x00`). | If telemetry interval increases or publishes stall, broker silently drops connection. |
| **D8** | **LOW** | `flash_now.py:9` | **Hardcoded Arduino Build Cache Path**: References `C:\Users\HP\AppData\Local\arduino\sketches\F5084256F8F5400580C13B786BFC4D6A`. | Script fails if Arduino IDE recompiles to a new temporary hash folder. |

---

## 6. Recommended Exact Technical Fixes

### Fix 1: Unified Cloud Broker Standard across All Layers
Standardize all components to the single high-availability public broker:
- **Broker Host**: `broker.emqx.io`
- **TCP Port (Hardware & Python)**: `1883`
- **WebSocket Secure Port (Vercel / HTTPS)**: `8084` (`wss://broker.emqx.io:8084/mqtt`)
- **WebSocket Port (Local HTTP)**: `8083` (`ws://broker.emqx.io:8083/mqtt`)
- **Unified Topic**: `airsense/karachi/bic_roof/telemetry` (subscribers can also listen to `airsense/#`)
*Action*: Update `public/hardware.html` (lines 880–881) and `scripts/airsense_mqtt_live_forwarder.py` (lines 16–17) to match `broker.emqx.io`.

### Fix 2: Emit JSON Over Serial on Every Cycle
In `airsense_esp32_firmware.ino` (after line 395), add:
```cpp
// Emit clean, machine-parsable JSON to USB Serial for bridge scripts and logging
Serial.print("[JSON_TELEMETRY] ");
Serial.println(jsonPayload);
```
This allows both Python bridges and terminal loggers to parse JSON reliably without regex guesswork.

### Fix 3: Transparent Sensor Health & Null Handling
Modify the firmware data structure so that when sensors are disconnected or return errors:
1. PMS7003: Set `pm1 = -1.0`, `pm25 = -1.0`, `pm10 = -1.0` or format JSON with `"pm2_5": null`.
2. BME280: Set `temp = -999.0`, `hum = -1.0`, `press = -1.0` or `"temperature": null`.
3. Add a `sensor_status` field to the payload:
   ```json
   "sensor_health": {
     "pms7003": true,
     "bme280": true,
     "rain_sensor": true,
     "microsd": true
   }
   ```
4. In `applyLiveTelemetryPacket()` in `public/index.html` and `public/hardware.html`, accurately render `OFFLINE` badge for any sensor where the value is `null` or health is `false`.

### Fix 4: Non-Blocking Socket & Watchdog Implementation
1. Reduce `mqttClient.connect()` timeout from 5000ms to 1000ms.
2. Replace the blocking `while (mqttClient.available() < 4)` loop with a non-blocking state machine or `millis()` timer.
3. Integrate the ESP32 Task Watchdog Timer (`esp_task_wdt_init(10, true)`) to trigger an automatic reset if any I2C, SPI, or UART driver hangs indefinitely.

### Fix 5: Dynamic COM Port Auto-Detection in Python Bridge
Enhance `airsense_serial_live_bridge.py` and `airsense_serial_forwarder.py` to scan all available ports (`list(serial.tools.list_ports.comports())`) searching for VID/PID or descriptions matching Silicon Labs CP210x (`10C4:EA60`) or CH340 (`1A86:7523`), falling back to any connected COM port rather than crashing on hardcoded ports.

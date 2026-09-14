# Detailed Architectural Analysis: ESP32 Autonomous IoT Upgrade (WiFiManager & Secure Cloud Ingestion)

**Target File**: `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`  
**Milestone**: M4 / Milestone 5 (ESP32 Physical Telemetry, WiFiManager, Direct Secure Cloud Ingestion)  
**Author**: explorer_m4_1 (teamwork_preview_explorer)  
**Date**: 2026-09-05  

---

## 1. Executive Summary & Problem Formulation

AirSense Pakistan's physical sensor stations are deployed in outdoor university campus rooftop environments (e.g., Karachi BIC Roof). Currently, the ESP32 node requires a tethered PC running `scripts/airsense_serial_live_bridge.py` to read USB serial output and route data to HiveMQ Cloud and local REST backends. Furthermore, Wi-Fi credentials in the ESP32 sketch are hardcoded to local test networks (`Tracks_brand` / `AQeel1234`), preventing end-user deployment without flashing source code.

This specification details the end-to-end architecture to convert the ESP32 into a **100% autonomous, standalone IoT appliance**:
1. **Dynamic Wi-Fi Provisioning via `tzapu/WiFiManager`**: Eliminates hardcoded SSIDs/passwords. Boots into captive portal AP mode (`AirSense-Setup`) on first use or Wi-Fi loss, stores credentials in ESP32 Flash NVS, and includes a 180-second portal timeout to prevent field lockup.
2. **Direct Secure Cloud Ingestion via `WiFiClientSecure`**: Replaces unencrypted local HTTP POST with TLS 1.2/1.3 encrypted HTTPS POST directly to `https://airsense-team.vercel.app/api/v1/ingest/reading`, bypassing the laptop bridge entirely.
3. **Dual Cloud Publishing**: Simultaneously pushes telemetry to the live Vercel Cloud API and HiveMQ Cloud MQTT Broker (`broker.hivemq.com:1883`) directly from the ESP32 over Wi-Fi.
4. **Resilient Local Fallback**: Maintains continuous PMS7003, BME280, Rainplate sensor reading and MicroSD circular logging (`/telemetry.csv`) even during network disconnection.

---

## 2. Comprehensive Firmware Audit (`airsense_esp32_firmware.ino`)

The existing firmware sketch (`v3.5.0-HARDENED`, 659 lines) was inspected line by line:

### 2.1 Wi-Fi Initialization & Credential Management
- **Hardcoded Credentials** (Lines 27-28):
  ```cpp
  const char* WIFI_SSID     = "Tracks_brand";              // Local Wi-Fi / Hotspot SSID
  const char* WIFI_PASS     = "AQeel1234";                // Local Wi-Fi Password
  ```
- **Static Boot Connection** (Lines 483-504 in `setup()`):
  ```cpp
  Serial.print("[WIFI] Connecting to: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 10) {
    delay(500);
    Serial.print(".");
    tries++;
  }
  ```
- **Background Reconnection Loop** (Lines 407-448 in `handleWiFiReconnection()`):
  Calls `WiFi.begin(WIFI_SSID, WIFI_PASS)` every 10-15 seconds if disconnected.
- **Deficiencies**:
  - Requires source code editing and recompilation whenever Wi-Fi credentials change.
  - Exposes plain-text Wi-Fi passwords in version control.
  - Precludes self-service field installation by non-technical campus operators.

### 2.2 Cloud MQTT Connection
- **Broker Configuration** (Lines 44-53):
  ```cpp
  const char* MQTT_BROKERS[] = {"broker.hivemq.com", "broker.emqx.io"};
  const int   NUM_BROKERS    = 2;
  const int   MQTT_PORT      = 1883;
  const char* MQTT_TOPIC     = "airsense/karachi/bic_roof/telemetry";

  WiFiClient    mqttClient;
  int           current_broker_idx = 0;
  unsigned long last_mqtt_attempt  = 0;
  bool          mqtt_is_connected  = false;
  ```
- **Protocol Implementation** (Lines 294-405):
  - Builds raw MQTT 3.1.1 byte packets (`CONNECT` `0x10`, `PUBLISH` `0x30` QoS 0) over unencrypted TCP `WiFiClient`.
  - Generates unique Client ID `as-esp32-%06X` from ESP32 eFuse MAC address.
  - Implements non-blocking connection with 500ms socket timeout and 250ms CONNACK wait.
  - Automatically switches between HiveMQ and EMQX if broker handshake fails.
  - Properly formats variable-length remaining length fields for packets > 127 bytes.

### 2.3 HTTP Ingestion Logic
- **Configuration** (Lines 18, 38-39):
  ```cpp
  #include <HTTPClient.h>
  const char* API_ENDPOINT  = "http://172.20.10.13:8000/api/v1/ingest/reading";
  const char* DEVICE_TOKEN  = "airsense_dev_token_khi_01";
  ```
- **Execution in `loop()`** (Lines 639-650):
  ```cpp
  HTTPClient http;
  http.begin(API_ENDPOINT);
  http.setTimeout(400);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  int code = http.POST(jsonPayload);
  if (code > 0) {
    Serial.printf("[HTTP PUSH] Success (HTTP %d)\n", code);
  }
  http.end();
  ```
- **Deficiencies**:
  - Bound to an ephemeral local development IP (`http://172.20.10.13:8000`), failing when deployed standalone.
  - Uses unencrypted plain HTTP.
  - The 400ms timeout (`http.setTimeout(400)`) causes immediate failure over public Internet WAN where TLS handshakes take 500ms to 2000ms.
  - Lacks `WiFiClientSecure` integration; passing an `https://` URL directly to basic `HTTPClient.begin(url)` fails TLS verification on ESP32.

### 2.4 Sensor Acquisition Loops
- **Plantower PMS7003 Optical Laser Dust Sensor** (Lines 65, 240-270):
  - Hardware UART2 on GPIO 16 (RX) / 17 (TX) at 9600 baud (`HardwareSerial pmsSerial(2)`).
  - 500ms non-blocking frame scanner hunting for preamble `0x42 0x4D`.
  - Verifies 16-bit packet checksum; extracts PM1.0, PM2.5, PM10.
  - Emits `-1.0` if sensor frame is corrupted or disconnected.
- **Bosch BME280 Environmental Sensor** (Lines 68-237):
  - Direct register I2C driver on GPIO 21 (SDA) / 22 (SCL).
  - Probes I2C address `0x76`, then fallback `0x77`.
  - Reads calibration coefficients from ROM, bursts 8 data registers (`0xF7..0xFE`).
  - Implements 64-bit integer compensation for temperature, pressure, and humidity per Bosch datasheet.
  - Flags `-999.0` temp and `-1.0` hum/press on bus error.
- **Resistive Raindrop Moisture Plate** (Lines 273-289):
  - Analog ADC1 on GPIO 34 (`RAIN_ADC_PIN`).
  - 8-sample oversampling with 1ms delay.
  - Categorizes moisture: `< 1500` Heavy Rain, `< 2500` Light Rain, `< 3500` Dew/Moisture, `>= 3500` Dry.
  - Sets boolean `rain_flag = (rain_adc < 2800)`.
- **MicroSD Circular SPI Backup Logging** (Lines 20-21, 61, 475-481, 582-595):
  - Hardware VSPI on GPIO 5 (CS), 18 (SCK), 19 (MISO), 23 (MOSI).
  - Appends raw telemetry line to `/telemetry.csv` on SD card even if network is completely offline.

---

## 3. Specification: Dynamic Wi-Fi Configuration (`tzapu/WiFiManager`)

### 3.1 Header Inclusion & Dependencies
Add the official `tzapu/WiFiManager` library include:
```cpp
#include <WiFiManager.h> // tzapu/WiFiManager v2.0.17+
```
`WiFiManager.h` encapsulates ESP32 `WebServer.h`, `DNSServer.h`, and `WiFi.h`.

### 3.2 Removal of Static Credentials
Remove lines 27-28 entirely:
```cpp
// DELETED:
// const char* WIFI_SSID     = "Tracks_brand";
// const char* WIFI_PASS     = "AQeel1234";
```

### 3.3 Dynamic Onboarding & Captive Portal (`autoConnect`)
Replace static Wi-Fi setup in `setup()` with:
```cpp
// 4. Dynamic Wi-Fi Initialization via WiFiManager
WiFiManager wm;

// Enable serial debug log for WiFiManager state transitions
wm.setDebugOutput(true);

// CRITICAL: Prevent outdoor field bricking if no human interacts
wm.setConfigPortalTimeout(180); // 3 minutes timeout

// Station connection timeout
wm.setConnectTimeout(15);

Serial.println("[WIFI] Initializing WiFiManager autoConnect...");
Serial.println("[WIFI] If unconfigured or offline, captive portal AP 'AirSense-Setup' will broadcast (180s timeout).");

// autoConnect workflow:
// 1. Checks ESP32 NVS flash for previously stored Wi-Fi credentials.
// 2. If credentials exist, attempts to connect to the saved network.
// 3. If no credentials exist or connection fails, automatically configures SoftAP 'AirSense-Setup'
//    (IP: 192.168.4.1) and launches captive portal DNS server redirecting connected clients to setup UI.
// 4. Once credentials are submitted, saves them to NVS and connects to the AP.
// 5. Returns true if connected; returns false if portal timed out.
bool wifiConnected = wm.autoConnect("AirSense-Setup");

if (wifiConnected) {
  Serial.println("\n[WIFI CONNECTED] Successfully authenticated to local AP!");
  Serial.println("[WIFI] IP Address: " + WiFi.localIP().toString());
  digitalWrite(STATUS_LED_PIN, HIGH);
  configTime(5 * 3600, 0, "pool.ntp.org", "time.google.com");
  Serial.println("[NTP] Clock synchronized with global atomic time (PKT UTC+5).");
} else {
  Serial.println("\n[WIFI WARNING] Config portal timed out. Running in autonomous offline sensor mode.");
  digitalWrite(STATUS_LED_PIN, LOW);
}
```

### 3.4 Flash NVS Storage & Auto-Reconnect Mechanics
1. **NVS Partition**: ESP32 stores Wi-Fi configurations in the non-volatile storage partition (`nvs`). `WiFiManager` writes validated SSID and PSK records directly into this partition.
2. **First Boot**: Because NVS is empty, `wm.autoConnect("AirSense-Setup")` activates the AP and DNS server immediately.
3. **Subsequent Boots**: `wm.autoConnect()` loads credentials from NVS and connects in station mode (`WIFI_STA`) within 2-4 seconds without activating the AP.
4. **Relocation / Network Loss**: If credentials become invalid or the router is offline, `autoConnect()` tries connecting, fails after 15s, and re-activates `AirSense-Setup` for 180s before falling back to offline logging.

### 3.5 Bricking Prevention via `setConfigPortalTimeout`
Outdoor deployment requires that sensor reading, MicroSD recording, and serial telemetry NEVER stop if Wi-Fi fails.
- Without a timeout, `autoConnect()` hangs indefinitely in a blocking loop until a user configures it.
- With `wm.setConfigPortalTimeout(180)`, if no user configures the device within 180 seconds, the portal cleanly shuts down, `autoConnect()` returns `false`, and execution continues into `loop()`. Sensors continue sampling, SD logging continues uninterrupted, and background auto-reconnection resumes.

### 3.6 Refactoring Background Wi-Fi Reconnection (`handleWiFiReconnection`)
Because credentials reside in NVS, calling `WiFi.begin(WIFI_SSID, WIFI_PASS)` must be replaced with parameterless `WiFi.begin()`:
```cpp
void handleWiFiReconnection(unsigned long now) {
  static unsigned long last_wifi_check           = 0;
  static unsigned long wifi_reconnect_started_at = 0;
  static bool          wifi_reconnecting         = false;

  if (WiFi.status() == WL_CONNECTED) {
    if (wifi_reconnecting) {
      wifi_reconnecting = false;
      Serial.println("\n[WIFI RESTORED] Connected to AP! IP: " + WiFi.localIP().toString());
      digitalWrite(STATUS_LED_PIN, HIGH);
      configTime(5 * 3600, 0, "pool.ntp.org", "time.google.com");
    }
    return;
  }

  // Wi-Fi is currently disconnected
  digitalWrite(STATUS_LED_PIN, LOW);
  if (mqttClient.connected()) {
    mqttClient.stop();
    mqtt_is_connected = false;
  }

  if (!wifi_reconnecting) {
    if (now - last_wifi_check >= 15000 || last_wifi_check == 0) {
      last_wifi_check = now;
      Serial.println("[WIFI WARNING] Wi-Fi link lost. Initiating non-blocking reconnection to NVS credentials...");
      WiFi.disconnect();
      WiFi.begin(); // Automatically connects using NVS credentials saved by WiFiManager!
      wifi_reconnecting = true;
      wifi_reconnect_started_at = now;
    }
  } else {
    if (now - wifi_reconnect_started_at > 15000) {
      wifi_reconnecting = false;
      last_wifi_check = now;
    }
  }
}
```

---

## 4. Specification: Direct Secure Cloud API Ingestion (`WiFiClientSecure`)

### 4.1 Header Inclusion & Configuration Constants
Include `WiFiClientSecure.h`:
```cpp
#include <WiFiClientSecure.h>

// Live Cloud Production Ingestion Endpoint (Direct Secure HTTPS)
const char* API_ENDPOINT = "https://airsense-team.vercel.app/api/v1/ingest/reading";
const char* DEVICE_TOKEN = "airsense_dev_token_khi_01";
```

### 4.2 TLS Cryptographic Architecture & `client.setInsecure()`
- Vercel and edge CDNs frequently rotate SSL/TLS certificates and root CAs (Let's Encrypt ISRG Root X1, Cloudflare, Google Trust Services).
- Hardcoding static root CAs inside ESP32 flash creates brittle firmware that bricks when cloud certificates rotate.
- Calling `secureClient.setInsecure()` configures the mbedTLS client to bypass CA verification while still performing **full TLS 1.2/1.3 session encryption**.
- All data in transit (including device tokens and sensor telemetry) is encrypted using AES/ChaCha20 over the wire.
- Heap Management: A local `WiFiClientSecure` instance allocates ~30 KB of SRAM during TLS handshake and releases it completely upon `https.end()`, avoiding heap fragmentation.

### 4.3 Network Timeout Tuning
The existing 400ms timeout (`http.setTimeout(400)`) is replaced with 4000ms (`secureClient.setTimeout(4000)` and `https.setTimeout(4000)`). This accommodates TLS certificate exchanges and Vercel edge function spin-up without blocking the main telemetry loop.

### 4.4 Refactored HTTPS Push in `loop()`
```cpp
// Direct Secure Cloud API Ingestion (HTTPS over TLS)
if (WiFi.status() == WL_CONNECTED) {
  // 1. MQTT Cloud Publish (HiveMQ / EMQX Dual Failover)
  publishMQTT(MQTT_TOPIC, jsonPayload);

  // 2. Direct Vercel Cloud HTTPS Ingestion
  WiFiClientSecure secureClient;
  secureClient.setInsecure(); // Skip rigid CA cert pinning for edge cloud resilience
  secureClient.setTimeout(4000);

  HTTPClient https;
  if (https.begin(secureClient, API_ENDPOINT)) {
    https.setTimeout(4000);
    https.addHeader("Content-Type", "application/json");
    https.addHeader("X-Device-Token", DEVICE_TOKEN);

    int httpResponseCode = https.POST(jsonPayload);
    if (httpResponseCode > 0) {
      Serial.printf("[HTTPS CLOUD INGEST] Response: HTTP %d\n", httpResponseCode);
    } else {
      Serial.printf("[HTTPS CLOUD WARNING] POST failed: %s (Code: %d)\n",
        https.errorToString(httpResponseCode).c_str(), httpResponseCode);
    }
    https.end();
  } else {
    Serial.println("[HTTPS CLOUD ERROR] Failed to connect to secure cloud endpoint.");
  }
}
```

### 4.5 Payload Verification & Schema Conformance

#### Backend Target Schema (`apps/api/routers/ingest_router.py`)
The endpoint `/api/v1/ingest/reading` accepts `ESP32IngestPayload`:
- `schema_version`: "1.0"
- `device_uid`: "AIRSENSE-NODE-KHI-01"
- `station_code`: "BIC-KHI-ROOF-01"
- `timestamp_epoch`: Unix epoch seconds (e.g. 1757095130)
- `pm1`, `pm2_5`, `pm10`: float (or `null`)
- `temperature`, `humidity`, `pressure`: float (or `null`)
- `rain_flag`: boolean (`true` / `false`)
- `firmware_version`: string (e.g. "v4.0.0-AUTONOMOUS")
- `sequence_number`: unsigned long integer

#### JSON Wire Format Produced by Firmware
```json
{
  "schema_version": "1.0",
  "device_id": "AIRSENSE-NODE-KHI-01",
  "device_uid": "AIRSENSE-NODE-KHI-01",
  "station_code": "BIC-KHI-ROOF-01",
  "campus_code": "KARACHI",
  "location": "BIC_ROOF_KARACHI",
  "firmware_version": "v4.0.0-AUTONOMOUS",
  "sequence_number": 42,
  "timestamp_epoch": 1757095130,
  "pm1": 14.2, "pm1_0": 14.2,
  "pm2_5": 28.6, "pm25": 28.6,
  "pm10": 45.1,
  "temperature": 29.4, "temperature_c": 29.4,
  "humidity": 62.1, "humidity_pct": 62.1,
  "pressure": 1011.5, "pressure_hpa": 1011.5,
  "rain_flag": false,
  "sensor_health": {
    "pms7003": "OK",
    "bme280": "OK",
    "rain": "OK",
    "microsd": "OK"
  },
  "transmission_mode": "WIFI_DIRECT"
}
```

#### Sensor Error / Disconnect Handling
When any physical sensor fails or is disconnected:
- Numerical values are serialized as literal `null` (not strings, not zeroes).
- FastAPI Pydantic cleanly maps `null` to Python `None`.
- `SensorHealthEngine` automatically identifies the disconnected sensor and marks station health as `DEGRADED` or `OFFLINE` on `/api/v1/ingest/sensors/diagnostic`.

#### ArduinoJson vs. `snprintf` Analysis
The existing firmware formats JSON using `snprintf` into `char jsonPayload[640]`.
- **`snprintf` Pros**: Built into GCC/C++ standard library, 0 bytes library overhead, deterministic stack allocation, ultra-fast.
- **`ArduinoJson` Pros**: Type-safe dynamic object builder, requires installing `ArduinoJson` (v6/v7) library.
- **Verdict**: Retaining `snprintf` maintains the zero-dependency compilation guarantee while generating strictly compliant JSON.

---

## 5. Precise Implementation Strategy & Step-by-Step Changes

1. **Includes Section** (Lines 17-23):
   Add `#include <WiFiClientSecure.h>` and `#include <WiFiManager.h>`.
2. **Configuration Section** (Lines 26-40):
   Delete `WIFI_SSID` and `WIFI_PASS`. Update `FIRMWARE_VER` to `"v4.0.0-AUTONOMOUS"`. Update `API_ENDPOINT` to `"https://airsense-team.vercel.app/api/v1/ingest/reading"`.
3. **Wi-Fi Reconnection Section** (Lines 407-448):
   Change `WiFi.begin(WIFI_SSID, WIFI_PASS)` to `WiFi.begin()`.
4. **Setup Section** (Lines 483-504):
   Replace manual `WiFi.begin` while loop with `WiFiManager wm; wm.setConfigPortalTimeout(180); bool wifiConnected = wm.autoConnect("AirSense-Setup");`.
5. **Main Loop Section** (Lines 639-650):
   Replace plain HTTPClient with `WiFiClientSecure secureClient; secureClient.setInsecure(); secureClient.setTimeout(4000);` and `https.begin(secureClient, API_ENDPOINT);`.
6. **Documentation**:
   Create `scripts/airsense_esp32_firmware/README_FIRMWARE.md` detailing library installation, board configuration, and captive portal setup steps.

---

## 6. Verification and Validation Plan

1. **Payload Schema Conformance**:
   Execute Python schema test verifying that the JSON produced by the firmware validates successfully against `ESP32IngestPayload` in `apps/api/routers/ingest_router.py`.
2. **Live Cloud HTTPS Ingestion Test**:
   Execute programmatic POST against `https://airsense-team.vercel.app/api/v1/ingest/reading` with `X-Device-Token: airsense_dev_token_khi_01` and verify HTTP 200 response.
3. **Non-blocking Reconnect & Timeout Check**:
   Confirm that when Wi-Fi is absent, `wm.autoConnect("AirSense-Setup")` exits after 180 seconds, allowing sensor reading and SD logging to proceed.

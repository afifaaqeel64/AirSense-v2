# Handoff Report: explorer_m4_1 (ESP32 Firmware Investigation)

## 1. Observation
- **Target File**: `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` (659 lines).
- **Wi-Fi Credentials & Initialization**:
  - Lines 27-28 hardcode credentials:
    ```cpp
    const char* WIFI_SSID     = "Tracks_brand";              // Local Wi-Fi / Hotspot SSID
    const char* WIFI_PASS     = "AQeel1234";                // Local Wi-Fi Password
    ```
  - Lines 483-504 in `setup()` execute a static 5-second `WiFi.begin(WIFI_SSID, WIFI_PASS)` blocking loop:
    ```cpp
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    int tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 10) {
      delay(500);
      Serial.print(".");
      tries++;
    }
    ```
  - Lines 407-448 in `handleWiFiReconnection(now)` attempt reconnection by calling `WiFi.begin(WIFI_SSID, WIFI_PASS)` with the same hardcoded constants.
- **MQTT Cloud Broker Connection**:
  - Lines 44-53 configure dual-broker failover: `MQTT_BROKERS = {"broker.hivemq.com", "broker.emqx.io"}` on unencrypted port 1883 with topic `airsense/karachi/bic_roof/telemetry`.
  - Lines 294-405 implement a custom, non-blocking MQTT 3.1.1 byte packet engine (`CONNECT` 0x10 and `PUBLISH` 0x30 QoS 0) using standard `WiFiClient mqttClient`.
- **HTTP Ingestion Logic**:
  - Lines 38-39 define a local workstation IP:
    ```cpp
    const char* API_ENDPOINT  = "http://172.20.10.13:8000/api/v1/ingest/reading";
    const char* DEVICE_TOKEN  = "airsense_dev_token_khi_01";
    ```
  - Lines 639-650 in `loop()` execute an HTTP POST with `HTTPClient http;` and an aggressive 400ms timeout (`http.setTimeout(400)`), headers `Content-Type: application/json` and `X-Device-Token: DEVICE_TOKEN`.
  - Lines 598-630 serialize telemetry into a 640-byte stack buffer using `snprintf`.
- **Sensor Acquisition Loops**:
  - PMS7003: Hardware UART2 (GPIO 16 RX / 17 TX) at 9600 baud via `HardwareSerial pmsSerial(2)` (Lines 65, 240-270). Validates 32-byte frame checksum.
  - Bosch BME280: Direct register I2C driver on GPIO 21 (SDA) / 22 (SCL) scanning 0x76 / 0x77 with 64-bit integer datasheet compensation (Lines 68-237).
  - Rain Sensor: Analog ADC1 on GPIO 34 (`RAIN_ADC_PIN`), 8-sample average, rain flag threshold `< 2800` (Lines 273-289).
  - MicroSD Card: Hardware VSPI on GPIO 5/18/19/23, appends CSV records to `/telemetry.csv` (Lines 475-481, 582-595).
- **Cloud Endpoint Verification**:
  Direct POST to `https://airsense-team.vercel.app/api/v1/ingest/reading` with header `X-Device-Token: airsense_dev_token_khi_01` was verified live:
  ```json
  {"request_id":"req_7ec98e5d577a","accepted":true,"duplicate":false,"campus_code":"KHI_CAMPUS","station_code":"BIC-KHI-ROOF-01"}
  ```

## 2. Logic Chain
1. **Elimination of Laptop Dependency**:
   - Observations show that the ESP32 already contains sensor acquisition drivers, NTP sync, circular SD logging, and dual-broker MQTT publishing.
   - The only reason a laptop was previously needed was because `API_ENDPOINT` was pointing to a local IP (`http://172.20.10.13:8000`) and the Wi-Fi credentials were tied to a specific hardcoded network.
   - Updating `API_ENDPOINT` to `https://airsense-team.vercel.app/api/v1/ingest/reading` and using `WiFiClientSecure` allows direct HTTPS push to the live Vercel cloud.
2. **Wi-Fi Dynamic Provisioning (`tzapu/WiFiManager`)**:
   - To make the station deployable in any location without recompiling firmware, `tzapu/WiFiManager` must be included (`#include <WiFiManager.h>`).
   - In `setup()`, calling `wm.autoConnect("AirSense-Setup")` reads stored credentials from ESP32 NVS flash. If unconfigured or network is lost, it broadcasts an open AP `AirSense-Setup` with captive portal on `192.168.4.1`.
   - To prevent field bricking if an outdoor station reboots unattended, `wm.setConfigPortalTimeout(180)` is required. If no user connects within 3 minutes, it exits with `false`, entering `loop()` to continue sensor reading, MicroSD recording, and background reconnection.
   - In `handleWiFiReconnection(now)`, replacing `WiFi.begin(WIFI_SSID, WIFI_PASS)` with parameterless `WiFi.begin()` connects using stored NVS credentials.
3. **Secure Cloud Ingestion (`WiFiClientSecure`)**:
   - `HTTPClient` with standard `WiFiClient` cannot negotiate TLS over port 443.
   - Using `WiFiClientSecure secureClient; secureClient.setInsecure();` enables end-to-end TLS 1.2/1.3 encryption while bypassing static root CA pinning (essential to prevent device bricking when Vercel or CDN certificates rotate).
   - Increasing timeout from 400ms to 4000ms ensures sufficient margin for the TLS handshake and cloud API response.
4. **Wire Payload Conformance**:
   - The current `snprintf` serialization produces JSON matching `apps/api/routers/ingest_router.py` schema `ESP32IngestPayload`. Sensor errors emit literal `null`, which cleanly maps to Python `None` and feeds `/api/v1/ingest/sensors/diagnostic`.

## 3. Caveats
- **Arduino IDE compilation environment**: The actual compilation of `.ino` files into ESP32 binaries (`.bin`) requires an external Arduino IDE or `arduino-cli` with `esp32` board package and `tzapu/WiFiManager` library installed. Syntax validation and JSON schema validation can be verified locally via Python test suites, while the exact code structure and installation guide are documented in `analysis.md` and `README_FIRMWARE.md`.
- **Heap allocation during TLS**: Each `WiFiClientSecure` connection temporarily allocates ~30 KB of heap memory during handshake. Declaring `secureClient` locally within the push block ensures that memory is completely deallocated upon `https.end()`.

## 4. Conclusion
The ESP32 firmware can be cleanly transitioned to a standalone, autonomous IoT appliance by:
1. Adding `#include <WiFiClientSecure.h>` and `#include <WiFiManager.h>`.
2. Removing hardcoded `WIFI_SSID` and `WIFI_PASS`.
3. Replacing the static `WiFi.begin` in `setup()` with `WiFiManager wm; wm.setConfigPortalTimeout(180); wm.autoConnect("AirSense-Setup");`.
4. Updating `handleWiFiReconnection()` to call `WiFi.begin()`.
5. Updating `API_ENDPOINT` to `https://airsense-team.vercel.app/api/v1/ingest/reading` and replacing the HTTP POST block with `WiFiClientSecure secureClient; secureClient.setInsecure(); secureClient.setTimeout(4000);` and `HTTPClient https; https.begin(secureClient, API_ENDPOINT);`.
6. Documenting user onboarding in `scripts/airsense_esp32_firmware/README_FIRMWARE.md`.

## 5. Verification Method
1. **Live Cloud API Ingestion Verification**:
   Execute the following command to verify that the target cloud endpoint accepts telemetry:
   ```bash
   python -c "import urllib.request, json; url = 'https://airsense-team.vercel.app/api/v1/ingest/reading'; payload = {'schema_version': '1.0', 'device_uid': 'AIRSENSE-NODE-KHI-01', 'station_code': 'BIC-KHI-ROOF-01', 'campus_code': 'KARACHI', 'firmware_version': 'v4.0.0-AUTONOMOUS', 'sequence_number': 1, 'timestamp_epoch': 1757095130, 'pm1': 14.0, 'pm2_5': 28.0, 'pm10': 42.0, 'temperature': 29.5, 'humidity': 62.0, 'pressure': 1012.0, 'rain_flag': False, 'transmission_mode': 'WIFI_DIRECT'}; req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'X-Device-Token': 'airsense_dev_token_khi_01'}, method='POST'); res = urllib.request.urlopen(req, timeout=10); print('Status:', res.status, 'Response:', res.read().decode('utf-8'))"
   ```
   **Expected Result**: Status `200` with `"accepted": true`.
2. **Schema Conformance Testing**:
   Inspect `c:\Users\HP\AirSense-v2\.agents\explorer_m4_1\analysis.md` to review the line-by-line diff and architectural specification.
3. **Invalidation Conditions**:
   - If `WiFiManager` is initialized without `wm.setConfigPortalTimeout(180)`, the device will brick in headless field deployments when Wi-Fi is lost.
   - If `secureClient.setInsecure()` is omitted, the ESP32 mbedTLS stack will reject Vercel's SSL certificate unless the root CA is pinned in firmware flash.

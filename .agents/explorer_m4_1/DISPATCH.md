# Dispatch: explorer_m4_1

Target: Investigate `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`
Objectives:
- Analyze current Wi-Fi connection logic, hardcoded SSID/PASS, and MQTT loop.
- Analyze current HTTP POST telemetry logic and compare with `tzapu/WiFiManager` ESP32 library patterns.
- Detail how `WiFiManager` AP mode ("AirSense-Setup") autoConnect should be initialized without blocking permanently if already configured, and how credentials are stored in NVS.
- Detail how `WiFiClientSecure` with `client.setInsecure()` should replace standard `WiFiClient` for HTTPS ingestion to `https://airsense-team.vercel.app/api/v1/ingest/reading`.

## 2026-09-05T17:58:49Z
Task:
Investigate `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`.
1. Inspect the existing code:
   - Identify how Wi-Fi is currently initialized (hardcoded SSID/PASS).
   - Identify MQTT connection to HiveMQ Cloud.
   - Identify the current HTTP POST logic (what client library is used, URL, headers, payload serialization).
   - Identify sensor acquisition loops (PMS7003 UART, BME280 I2C, Rain sensor ADC, MicroSD SPI).
2. Detail the exact changes required for `tzapu/WiFiManager`:
   - Which header to include (`#include <WiFiManager.h>`).
   - How to replace the static `WiFi.begin(...)` in `setup()` with `WiFiManager wm; bool res = wm.autoConnect("AirSense-Setup");`.
   - How `autoConnect` behaves: tries connecting to saved credentials in NVS; if fails/no credentials, starts captive portal AP `AirSense-Setup`.
   - Any timeout or non-blocking configuration (`wm.setConfigPortalTimeout(180);` etc.) to avoid bricking if no user interacts.
3. Detail the exact changes required for Direct Secure Cloud API Ingestion (`WiFiClientSecure`):
   - Replace standard `WiFiClient` with `WiFiClientSecure client; client.setInsecure();`.
   - Use `HTTPClient https; https.begin(client, API_ENDPOINT);` or direct socket.
   - Endpoint: `https://airsense-team.vercel.app/api/v1/ingest/reading`.
   - Headers: `Content-Type: application/json` and `X-Device-Token: airsense_dev_token_khi_01`.
   - Payload: Verify the JSON structure constructed by ArduinoJson.
4. Document all findings and a precise step-by-step implementation strategy in `c:\Users\HP\AirSense-v2\.agents\explorer_m4_1\analysis.md` and write a clear `handoff.md`.
Communicate back using send_message to your caller.


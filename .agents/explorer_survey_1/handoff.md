# Explorer 1 Handoff Report: AirSense-v2 Codebase Survey

**Date**: 2026-09-01  
**Agent**: Explorer 1 (Codebase Explorer)  
**Target Working Directory**: `c:\Users\HP\AirSense-v2\.agents\explorer_survey_1`  
**Reference Analysis**: `c:\Users\HP\AirSense-v2\.agents\explorer_survey_1\analysis.md`  

---

## 1. Observation

Direct observations from examining the codebase:

### 1.1 Frontend Structure
- `apps/web/hardware_dashboard.html` (lines 1–859):
  - Pure single-file HTML/CSS/JS frontend without build-step requirements.
  - Line 410–414: Heartbeat indicator `#heartbeatPill`, `#pulseDot`, `#livenessText` (`ESP32 DISCONNECTED` / `ESP32 LIVE CONNECTED`), and `#lastSeenText`.
  - Line 421–431: `#disconnectBanner` displaying failover guidance and link to `/opensource`.
  - Line 434–486: Sensor cards for **Plantower PMS7003** (GPIO 16/17), **Bosch BME280** (GPIO 21/22), **Raindrop Moisture Plate** (GPIO 34), and **MicroSD SPI Flash** (GPIO 5/18/19/23).
  - Line 489–527: 10-column live telemetry table (`telemetryTableBody`).
  - Line 733–778: `initCloudMQTT()` configuring Paho MQTT WebSocket client to `broker.hivemq.com` (port 8884 for HTTPS, 8000 for HTTP), path `/mqtt`, subscribing to `airsense/#` and `airsense/karachi/bic_roof/telemetry`.
  - Line 780–808: `fetchHardwareDiagnostics()` fallback polling `/api/v1/ingest/sensors/diagnostic` every 1500ms.
  - Line 810–846: `fetchLatestTelemetry()` fallback polling `/api/v1/ingest/latest?limit=15` every 1500ms.
  - Line 856: `<script src="/static/paho-mqtt.js" ...>` loaded at bottom of document.
- `apps/web/opensource_dashboard.html` (lines 1–454):
  - Fetches Open-Meteo & Copernicus CAMS directly for Karachi (`24.8607, 67.0011`).
- `apps/web/index.html` (lines 1–1892):
  - Master command center with Leaflet maps and Chart.js charts.
- `apps/web_enterprise/index.html` (lines 1–1356):
  - Enterprise logistics/government portal connecting to HiveMQ Cloud TLS MQTT.

### 1.2 Firmware & Data Packet Format
- `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` (lines 1–414):
  - Target: ESP32 Dev Module (WROOM-32 / D0WDQ6).
  - Lines 32–35: `MQTT_BROKER = "broker.hivemq.com"`, `MQTT_PORT = 1883`, `MQTT_TOPIC = "airsense/karachi/bic_roof/telemetry"`.
  - Lines 38–102: Custom zero-dependency MQTT 3.1.1 raw TCP socket publisher over `WiFiClient`.
  - Lines 380–383: Formats payload JSON:
    ```c
    snprintf(jsonPayload, sizeof(jsonPayload),
      "{\"schema_version\":\"1.0\",\"device_uid\":\"%s\",\"station_code\":\"%s\",\"campus_code\":\"%s\",\"firmware_version\":\"v3.5.0-MQTT\",\"sequence_number\":%lu,\"timestamp_epoch\":%lu,\"pm1\":%.1f,\"pm2_5\":%.1f,\"pm10\":%.1f,\"temperature\":%.1f,\"humidity\":%.1f,\"pressure\":%.1f,\"rain_flag\":%s}",
      DEVICE_UID, STATION_CODE, CAMPUS_CODE, packet_seq, (unsigned long)(time(NULL)), pm1, pm25, pm10, temp, hum, press, rain_flag ? "true" : "false"
    );
    ```

### 1.3 Telemetry Field Names & Backend APIs
- Canonical fields in payload: `schema_version`, `device_uid`, `station_code`, `campus_code`, `firmware_version`, `sequence_number`, `timestamp_epoch`, `pm1`, `pm2_5`, `pm10`, `temperature`, `humidity`, `pressure`, `rain_flag`.
- Backend endpoints (`apps/api/routers/ingest_router.py` & `hardware_router.py`):
  - `POST /api/v1/ingest/reading`: Ingestion with device token auth and QC validation.
  - `GET /api/v1/ingest/sensors/diagnostic`: 8s threshold liveness and sensor health status.
  - `GET /api/v1/ingest/latest`: Recent raw readings array.
  - `GET /api/v1/hardware/status`: Hardware liveness snapshot.

### 1.4 Test Infrastructure
- `tests/e2e/test_dual_dashboards_e2e.py` (938 lines) covering Tier 1 through Tier 5.
- `tests/unit/test_challenger_hardware_diagnostics.py` (462 lines) covering state transitions and boundary timing.
- `requirements.txt` includes `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `pytest`, `pytest-asyncio`.

---

## 2. Logic Chain

1. **Premise 1 (Hardware & MQTT Broker)**: The physical ESP32 firmware publishes standard JSON packets every 5 seconds to public broker `broker.hivemq.com:1883` on topic `airsense/karachi/bic_roof/telemetry`.
2. **Premise 2 (Browser WebSockets)**: Modern browsers can establish direct TLS WebSocket connections to `wss://broker.hivemq.com:8884/mqtt` via Paho JavaScript library without requiring intermediate backend servers or tunnels.
3. **Premise 3 (Frontend Capability)**: `apps/web/hardware_dashboard.html` contains the full UI components (cards, gauges, reactive heartbeat, 10-column table) and the `applyLiveTelemetryPacket` parser for all ESP32 fields (`pm1`, `pm2_5`, `pm10`, `temperature`, `humidity`, `pressure`, `rain_flag`).
4. **Premise 4 (Dual-Mode Operation)**:
   - When deployed standalone on Vercel or GitHub Pages, WebSocket connection to HiveMQ functions independently. Any REST fetch calls to `/api/v1/...` catch errors silently without breaking the UI.
   - When run locally alongside FastAPI, the REST polling (`/api/v1/ingest/sensors/diagnostic` and `/api/v1/ingest/latest`) serves as a secondary fallback.
5. **Premise 5 (Heartbeat Liveness)**: An 8-second client-side timer accurately detects packet starvation and switches the UI indicator between `🟢 ESP32 LIVE CONNECTED` and `🔴 ESP32 DISCONNECTED`.
6. **Conclusion**: The codebase is architecturally ready for 24/7 cloud deployment by structuring static assets for Vercel and GitHub Pages with zero laptop dependencies.

---

## 3. Caveats

- **Network Firewalls / WebSockets**: Some institutional campus networks or strict corporate proxies may block WebSocket port `8884` or `8000`. Using standard WSS over port 8884 handles standard SSL inspection, but port 443 proxying is dependent on HiveMQ public broker infrastructure.
- **Paho Script Loading Race Condition**: In `hardware_dashboard.html`, loading `paho-mqtt.js` before `initCloudMQTT()` executes (e.g. in `<head>` via CDN) avoids initialization race conditions.
- **No caveats** regarding backend schemas, sensor pinouts, or field naming compatibility.

---

## 4. Conclusion

- The repository structure, schemas, and frontend UI are fully understood and documented in `analysis.md`.
- Deploying the standalone public hardware dashboard to Vercel and GitHub Pages requires packaging the clean static web assets (`index.html`, `paho-mqtt.js`, `opensource.html`, configuration files) with WSS 8884 enabled by default, ensuring direct HiveMQ connectivity and zero laptop dependencies.

---

## 5. Verification Method

To verify the findings and telemetry pipeline:
1. **Inspect Survey Report**:
   - View `c:\Users\HP\AirSense-v2\.agents\explorer_survey_1\analysis.md`.
2. **Inspect Firmware Source**:
   - View `c:\Users\HP\AirSense-v2\scripts\airsense_esp32_firmware\airsense_esp32_firmware.ino` (lines 30–102 & 380–399).
3. **Inspect Frontend Hardware Dashboard**:
   - View `c:\Users\HP\AirSense-v2\apps\web\hardware_dashboard.html` (lines 663–857).
4. **Inspect Backend Diagnostic Route**:
   - View `c:\Users\HP\AirSense-v2\apps\api\routers\ingest_router.py` (lines 289–323) and `services\quality_control\sensor_health_engine.py` (lines 32–150).
5. **Run Test Suite**:
   - Command: `pytest tests/e2e/test_dual_dashboards_e2e.py` and `pytest tests/unit/test_challenger_hardware_diagnostics.py`.

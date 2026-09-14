# AirSense-v2 Comprehensive Codebase & Architecture Survey Report

**Date**: 2026-09-01  
**Investigator**: Explorer 1 (Codebase Explorer)  
**Target Repository**: `c:\Users\HP\AirSense-v2`  
**Mission**: Investigate existing frontend structures, firmware telemetry schemas, backend API ingest/diagnostic endpoints, test infrastructure, and cloud deployment architecture for a 24/7 standalone public dashboard on Vercel / GitHub Pages.

---

## Executive Summary

AirSense-v2 contains a complete end-to-end IoT, telemetry ingestion, machine learning, and multi-dashboard web system for air quality and meteorological monitoring. 

The physical station comprises an **ESP32 microcontroller** streaming telemetry from:
1. **Plantower PMS7003** (UART2: GPIO 16 RX / 17 TX) — PM1.0, PM2.5, PM10 laser particle count.
2. **Bosch BME280** (I2C: GPIO 21 SDA / 22 SCL, addr 0x76) — Temperature, Humidity, Barometric Pressure.
3. **Raindrop Moisture Plate** (ADC1 CH6: GPIO 34) — Analog rain moisture comparator.
4. **MicroSD SPI Flash** (VSPI: GPIO 5 CS / 18 SCK / 19 MISO / 23 MOSI) — Circular offline CSV logger.

The firmware broadcasts packets over global cloud MQTT (`broker.hivemq.com:1883`, topic `airsense/karachi/bic_roof/telemetry`) using a zero-dependency raw TCP socket implementation. 

Existing frontends include a specialized hardware dashboard (`apps/web/hardware_dashboard.html`), an open-source weather hub (`apps/web/opensource_dashboard.html`), a command center (`apps/web/index.html`), and an enterprise portal (`apps/web_enterprise/index.html`). 

---

## 1. Frontend Architecture Survey

### 1.1 Existing Web Dashboard Files

| File Path | Size | Tech Stack | Primary Function |
|---|---|---|---|
| `apps/web/hardware_dashboard.html` | 31.6 KB (859 lines) | Pure HTML5 / CSS3 / Vanilla JS + Paho MQTT | Dedicated ESP32 Hardware Ground-Truth Dashboard. Displays real-time sensor cards (PMS7003, BME280, Rain, SD), dynamic disconnection banner, reactive heartbeat indicator, and 15-row live telemetry log. |
| `apps/web/opensource_dashboard.html` | 15.5 KB (454 lines) | Pure HTML5 / CSS3 / Vanilla JS | 24/7 Open-Source Meteorological Hub querying Open-Meteo & Copernicus CAMS directly for Karachi coordinates (`24.8607, 67.0011`). |
| `apps/web/index.html` | 74.2 KB (1892 lines) | HTML5 / CSS3 / JS + Leaflet + Chart.js | Central Command Center with GIS map view, 72-hour forecast charts, multi-station telemetry analytics. |
| `apps/web_enterprise/index.html` | 88.1 KB (1356 lines) | HTML5 / CSS3 / JS + Leaflet + Paho MQTT | Dual-profile Enterprise Decision Platform (Business Logistics & Government Policy) with TLS MQTT support. |
| `AirSenseDashboard-try.jsx` | 23.1 KB (357 lines) | React 18 / Recharts / Anthropic Claude API | Experimental React dashboard prototype with AI decision advisor. |
| `apps/web/paho-mqtt.js` | 30.0 KB | JavaScript Library (Eclipse Paho v1.0.1) | Client-side MQTT over WebSockets library for browser execution. |

### 1.2 UI Components & State Management in `hardware_dashboard.html`

- **Visual Design System**: Polar Blue palette (`--blue-50` to `--blue-950`), custom typography (`Plus Jakarta Sans` for UI, `JetBrains Mono` for telemetry values), and light/dark theme toggle via `data-theme` attribute on `<html>`.
- **Topbar & Navigation**:
  - Brand mark `AS` + title "AirSense Hardware Hub (Karachi BIC Rooftop ESP32 Station)".
  - Tab Switcher: `HARDWARE HUB` (`/hardware`), `24/7 OPEN-SOURCE` (`/opensource`), `COMMAND CENTER` (`/`).
  - Liveness Heartbeat Pill: `#heartbeatPill` with `#pulseDot`, `#livenessText` ("ESP32 LIVE CONNECTED" vs "ESP32 DISCONNECTED"), and `#lastSeenText` ("(0s ago)" vs "(Offline)").
- **Disconnection Failover Banner**:
  - `#disconnectBanner` appears when packet recency exceeds 8 seconds.
  - Features quick-action button redirecting to `/opensource`.
- **4 Sensor Cards**:
  1. **PMS7003**: Displays PM2.5 in $\mu\text{g/m}^3$, status badge (`ONLINE` / `OFFLINE`), pins `GPIO 16 (RX) / 17 (TX)`, diagnostic note (`UART2 active` vs `No UART laser frame`).
  2. **BME280**: Displays Temperature in $^\circ\text{C}$, status badge (`ONLINE` / `OFFLINE`), pins `GPIO 21 (SDA) / 22 (SCL)`, diagnostic note (`I2C active` vs `I2C bus probe offline`).
  3. **Rain Moisture Plate**: Displays `DRY` (green) vs `WET (RAIN)` (red), status badge, pins `GPIO 34 (ADC1 CH6)`, diagnostic note (`ADC active` vs `ADC channel unread`).
  4. **MicroSD SPI Flash**: Displays `LOGGING READY` vs `OFFLINE`, status badge, pins `GPIO 5 (CS) / 18 / 19 / 23`.
- **Live Telemetry Table**:
  - 10 columns: `TIMESTAMP (UTC)`, `SOURCE`, `PM1.0`, `PM2.5`, `PM10`, `TEMP`, `HUM`, `PRESS`, `RAIN`, `QC STATE`.
  - Client dynamically prepends newly arrived MQTT packets with high-visibility badge `CLOUD MQTT` and `VERIFIED CLOUD`, capping table history to 15 rows.

### 1.3 Client-Side MQTT WebSocket & Polling Implementation Analysis

In `apps/web/hardware_dashboard.html`:
```javascript
function initCloudMQTT() {
  const isHttps = location.protocol === 'https:';
  const mqttHost = "broker.hivemq.com";
  const mqttPort = isHttps ? 8884 : 8000;
  const mqttPath = "/mqtt";
  const clientId = "airsense-web-" + Math.random().toString(16).substring(2, 10);
  ...
  client.connect({
    useSSL: isHttps,
    timeout: 6,
    cleanSession: true,
    onSuccess: function () {
      client.subscribe("airsense/#");
      client.subscribe("airsense/karachi/bic_roof/telemetry");
    }
  });
}
```
**Identified Improvement Points**:
1. In `hardware_dashboard.html`, `<script src="/static/paho-mqtt.js" ...>` is loaded at the very bottom (line 856), whereas `initCloudMQTT()` is invoked in the script above (line 849). If `Paho` is not yet available at execute time, `initCloudMQTT` exits immediately without retrying on window load.
2. In HTTPS cloud environments (Vercel / GitHub Pages), `Paho.MQTT` must connect with `useSSL: true` on port `8884` with path `/mqtt`. Including the CDN script `<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js"></script>` in `<head>` ensures immediate availability.
3. Fallback polling calls `fetch('/api/v1/ingest/sensors/diagnostic')` and `fetch('/api/v1/ingest/latest')` every 1500ms. In cloud standalone mode where no backend server exists, these network fetches fail gracefully via `catch()`, while MQTT WebSockets receives packets directly from the ESP32.

---

## 2. Backend, Firmware & Telemetry Schema Survey

### 2.1 Firmware Analysis (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`)

The firmware is self-contained and does not require third-party MQTT or BME280 libraries:
- **Target Hardware**: ESP32 Dev Module (WROOM-32 / D0WDQ6)
- **Wi-Fi Connection**: Configured for 2.4 GHz Wi-Fi / Hotspot.
- **BME280 Driver**: Direct bit-level I2C register reader and Bosch compensation arithmetic implementation.
- **PMS7003 Driver**: Reads 32-byte UART2 packet, checks sync bytes `0x42 0x4D`, validates frame checksum, extracts standard particulate metrics `pm1`, `pm25`, `pm10`.
- **Raindrop Driver**: 8-sample smoothed analog read on GPIO 34. `rain_adc < 2800` sets `rain_flag = true`.
- **MicroSD Driver**: Appends CSV row to `/telemetry.csv` via standard SPI.
- **MQTT Transport**: Zero-dependency raw TCP socket connection to `broker.hivemq.com:1883` building MQTT 3.1.1 CONNECT and PUBLISH binary frames directly on `WiFiClient`. Broadcasts every 5000ms to topic `airsense/karachi/bic_roof/telemetry`.
- **Secondary Local HTTP Push**: Optional HTTP POST to `http://172.20.10.13:8000/api/v1/ingest/reading` with header `X-Device-Token`.

### 2.2 Telemetry JSON Schema

The ESP32 broadcasts the following canonical JSON telemetry packet:

```json
{
  "schema_version": "1.0",
  "device_uid": "AIRSENSE-NODE-KHI-01",
  "station_code": "BIC-KHI-ROOF-01",
  "campus_code": "KARACHI",
  "firmware_version": "v3.5.0-MQTT",
  "sequence_number": 1042,
  "timestamp_epoch": 1772467200,
  "pm1": 7.0,
  "pm2_5": 9.0,
  "pm10": 10.0,
  "temperature": 29.5,
  "humidity": 65.0,
  "pressure": 1012.0,
  "rain_flag": false
}
```

### 2.3 Comprehensive Field Name Mapping

| Parameter | ESP32 MQTT Firmware Field | Python Ingest Model (`ingest_router.py`) | Hardware Diagnostic Model (`SensorHealthEngine`) | Legacy / Alternative Aliases |
|---|---|---|---|---|
| **PM1.0** | `pm1` | `pm1` (float) | `pm1` | `pm1_0` |
| **PM2.5** | `pm2_5` | `pm2_5` (float) | `pm2_5` | `pm25`, `pm2.5` |
| **PM10** | `pm10` | `pm10` (float) | `pm10` | `pm10_0` |
| **Temperature** | `temperature` | `temperature_c` / `temperature` | `temperature_c` | `temp`, `temperature_c` |
| **Humidity** | `humidity` | `humidity_pct` / `humidity` | `humidity_pct` | `hum`, `humidity_pct` |
| **Pressure** | `pressure` | `pressure_hpa` / `pressure` | `pressure_hpa` | `press`, `pressure_hpa` |
| **Rain Status** | `rain_flag` | `rain_flag` (bool) | `rain_flag` | `is_raining`, `rain` |
| **Sequence #** | `sequence_number` | `sequence_number` (int) | `sequence_number` | `seq` |
| **Timestamp** | `timestamp_epoch` | `observed_at` / `timestamp_epoch` | `last_packet_received_at` | `timestamp`, `timestamp_utc` |
| **Device ID** | `device_uid` | `device_uid` (str) | `device_uid` | `device_id` |
| **Station ID** | `station_code` | `station_code` (str) | `station_code` | `station_id` |
| **Campus** | `campus_code` | `campus_code` (str) | `campus_code` | `campus` |

---

## 3. Backend API Endpoints & Local Fallback Mechanism

### 3.1 Relevant API Endpoints

1. **`GET /api/v1/ingest/sensors/diagnostic`** (`apps/api/routers/ingest_router.py` lines 289-323):
   - Invokes `SensorHealthEngine.evaluate_sensor_connectivity()`.
   - Uses `OFFLINE_THRESHOLD_SECONDS = 8` (8-second heartbeat window).
   - Returns structured JSON:
     - `station_liveness`: `"LIVE_ACTIVE"`, `"PARTIAL_DEGRADED"`, or `"OFFLINE"`.
     - `seconds_since_last_packet`: integer seconds elapsed since last packet was received.
     - `sensors`: Individual status objects for `pms7003`, `bme280`, `rain_sensor`, and `microsd` (with `is_connected`, `status`, `diagnostic_message`, `last_valid_value`, `troubleshooting_step`).
     - `summary_advisory`: Plain-English summary of station state.

2. **`GET /api/v1/ingest/latest?limit=15`** (`apps/api/routers/ingest_router.py` lines 252-286):
   - Returns the most recent raw sensor telemetry records from the database table `raw_readings`.

3. **`POST /api/v1/ingest/reading`** (`apps/api/routers/ingest_router.py` lines 60-243):
   - Ingestion endpoint used by ESP32 HTTP push and serial/MQTT bridges. Validates token authentication (`X-Device-Token: airsense_dev_token_khi_01`), deduplicates with sha256 content hashing, runs QC engine, records observation, and performs hourly aggregation.

4. **`GET /api/v1/hardware/status`** (`apps/api/routers/hardware_router.py` lines 40-110):
   - Returns consolidated hardware connection state and last-known telemetry values.

---

## 4. Test Infrastructure, Build Scripts & Dependencies

### 4.1 Dependency Ecosystem (`requirements.txt`)

- **Backend**: `fastapi>=0.111.0`, `uvicorn[standard]>=0.29.0`, `pydantic>=2.7.1`, `pydantic-settings>=2.2.1`
- **Database**: `sqlalchemy[asyncio]>=2.0.30`, `aiosqlite>=0.20.0`, `asyncpg>=0.29.0`, `alembic>=1.13.1`
- **Machine Learning**: `numpy>=1.26.4`, `pandas>=2.2.2`, `scikit-learn>=1.4.2`, `xgboost>=2.0.3`, `lightgbm>=4.3.0`, `joblib>=1.4.2`
- **Networking & Testing**: `httpx>=0.27.0`, `python-dotenv>=1.0.1`, `pytest>=8.2.0`, `pytest-asyncio>=0.23.6`

### 4.2 Test Suite Structure

- `tests/e2e/test_dual_dashboards_e2e.py` (938 lines):
  - Tier 1: Feature verification (F1.1 to F4.3).
  - Tier 2: Boundary conditions (119s LIVE vs 121s OFFLINE, sensor range bounds).
  - Tier 3: Cross-feature pairwise interactions.
  - Tier 4: Real-world workflows (hardware boot, streaming, offline failover, open-source fallback).
  - Tier 5: Adversarial hardening (corrupted payloads, SQL injections, rapid polling).
- `tests/unit/test_challenger_hardware_diagnostics.py` (462 lines):
  - State machine transitions, sensor degradation, and GPIO pin troubleshooting guides.
- `tests/unit/test_hardware_and_theme_endpoints.py` (80 lines):
  - Tests hardware status, minute history, CSV export, and GIS open-source mesh.

### 4.3 Scripts & Operational Automation

- `scripts/airsense_mqtt_live_forwarder.py`: Subscribes to `broker.hivemq.com:1883` on `airsense/#` and forwards to local FastAPI backend.
- `scripts/airsense_serial_live_bridge.py`: Reads COM port (e.g. COM7 @ 115200 baud) and POSTs to `/api/v1/ingest/reading`.
- `share_dashboard_publicly.bat`: Exposes port 8000 via localtunnel.
- `start_mqtt_forwarder.bat`: Runs Python MQTT forwarder.
- `run_airsense_all_in_one.bat`: Master batch launcher for backend + serial bridge + MQTT forwarder + localtunnel.

---

## 5. Architectural Synthesis for 24/7 Cloud Deployment (Vercel / GitHub Pages)

### 5.1 The Core Challenge & Resolution

- **Old Mode**: ESP32 $\rightarrow$ Laptop Backend (Port 8000) $\rightarrow$ Localtunnel (`airsense-karachi-live.loca.lt`) $\rightarrow$ Browser.  
  *Limitation*: If the laptop is shut down or goes to sleep, the dashboard dies.
- **New 24/7 Standalone Cloud Mode (Target)**:
  1. **ESP32 Node (at Campus)** $\xrightarrow{\text{Direct MQTT TCP 1883}}$ **Global Cloud MQTT Broker (`broker.hivemq.com`)**
  2. **Client Browser (Worldwide on Mobile/Desktop)** $\xrightarrow{\text{Direct Secure WebSockets WSS:8884}}$ **Global Cloud MQTT Broker (`broker.hivemq.com`)**
  3. **Zero Laptop Dependency**: The dashboard runs purely as static HTML/JS on Vercel or GitHub Pages. When the ESP32 publishes a packet, HiveMQ relays it over WebSockets directly into the viewer's browser in $< 200\text{ms}$.
  4. **Graceful Local Fallback**: If served locally alongside FastAPI, the client polls `/api/v1/ingest/sensors/diagnostic` as a secondary fallback.
  5. **Reactive Heartbeat**: If no packets arrive within 8 seconds from MQTT or REST, the UI instantly switches to `🔴 ESP32 DISCONNECTED` and displays the offline alert banner.

---

## 6. Conclusion & Recommended Action Plan

The codebase has all foundational primitives in place:
- The ESP32 firmware already publishes standard JSON packets to `broker.hivemq.com:1883` on topic `airsense/karachi/bic_roof/telemetry`.
- `apps/web/hardware_dashboard.html` contains the complete UI cards, gauges, tables, and Paho MQTT WebSocket client logic.
- To deploy to Vercel and GitHub Pages:
  - Create a clean static distribution folder (or configure root `index.html` / `vercel.json` / static build) ensuring `Paho.MQTT` CDN is in `<head>`, WSS is enforced over HTTPS, and topic subscriptions include both `airsense/#` and `airsense/karachi/bic_roof/telemetry`.
  - Add single-command deployment configurations and standalone verification checks.

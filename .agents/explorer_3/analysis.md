# Comprehensive Investigation & Telemetry Architecture Report: Vercel Dashboard & Frontend Streaming

**Investigator**: Explorer 3 (Vercel Dashboard & Frontend Telemetry Specialist)  
**Target Repository**: `c:/Users/HP/AirSense-v2`  
**Date**: 2026-09-02  

---

## Executive Summary

An exhaustive investigation of the AirSense-v2 web dashboard codebase, static assets, Vercel configuration, and MQTT WebSocket communication layers was conducted. 

### Key Critical Findings:
1. **Zero-Build Vanilla Architecture**: The frontend is built as zero-build static HTML5/CSS3/ES6 JavaScript, hosted on Vercel and GitHub Pages. No Node.js build process is required.
2. **Critical Multi-Broker Disconnect / Broker Mismatch**: `public/index.html` connects to `broker.emqx.io:8084`, whereas `public/hardware.html`, `public/command.html`, and `public/enterprise.html` connect to `broker.hivemq.com:8884`. Meanwhile, publisher scripts and firmware have split configurations (`airsense_serial_live_bridge.py` and `airsense_esp32_firmware.ino` push to `broker.emqx.io:1883`, but `airsense_mqtt_live_forwarder.py` listens to `broker.hivemq.com:1883`).
3. **Flawed Watchdog & Premature Disconnect Banner**: A rigid 20-second silence timer in `index.html` and `command.html` immediately flags the hardware as `ESP32 DISCONNECTED` upon page load or brief network hiccups.
4. **Half-Open WebSocket Zombie Sockets**: When network switching occurs (Wi-Fi to LTE, or laptop sleep/wake), the Paho WebSocket connection silently hangs without triggering `onConnectionLost`. No application-level heartbeat or socket recreation watchdog exists to recycle zombie clients.
5. **Vercel Standalone REST 404s**: The dashboard makes secondary REST polling requests to `/api/v1/ingest/sensors/diagnostic`, which 404s on Vercel standalone hosting, leaving the dashboard 100% dependent on MQTT WebSockets.
6. **Schema Fragility & `NaN` Rendering**: Telemetry parsing code contains unhandled `Number('--')` or `Number(null)` conversions which evaluate to `NaN`, polluting the UI cards and breaking chart calculations.

---

## 1. Framework, Build Setup, and Vercel Configuration

### 1.1 Architecture & Stack
- **Framework**: Pure Vanilla HTML5, CSS3, ES6+ JavaScript.
- **Build System**: Zero build step (no Webpack, Vite, Next.js, or Rollup).
- **Libraries & CDN Assets**:
  - `public/paho-mqtt.js` (Eclipse Paho JavaScript Client v1.0.1) with fallback CDN `https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js`.
  - Google Fonts: `Plus Jakarta Sans`, `JetBrains Mono`, `Manrope`.
  - Charting & GIS: Leaflet v1.9.4 (`https://unpkg.com/leaflet@1.9.4/dist/leaflet.js`) and Chart.js (`https://cdn.jsdelivr.net/npm/chart.js`).
- **Uncompiled React Artifact**: `AirSenseDashboard-try.jsx` in the root is an uncompiled React mock component using Recharts/Lucide. It is not bundled or served by Vercel.

### 1.2 Deployment Scripts & Hosting Configuration
- **Root `vercel.json`** (`c:/Users/HP/AirSense-v2/vercel.json`):
  ```json
  {
    "version": 2,
    "public": true,
    "name": "airsense-team",
    "cleanUrls": true,
    "trailingSlash": false,
    "routes": [
      { "src": "/hardware", "dest": "/public/hardware.html" },
      { "src": "/opensource", "dest": "/public/opensource.html" },
      { "src": "/command", "dest": "/public/command.html" },
      { "src": "/ops", "dest": "/public/command.html" },
      { "src": "/enterprise", "dest": "/public/enterprise.html" },
      { "src": "/", "dest": "/public/index.html" },
      { "src": "/(.*)", "dest": "/public/$1" }
    ]
  }
  ```
- **Public Directory `public/vercel.json`** (`c:/Users/HP/AirSense-v2/public/vercel.json`):
  Contains equivalent routing rules mapped relative to the `public/` root when deployed via `npx vercel public --prod --yes --name airsense-team` (as executed in `deploy_to_vercel.bat`, line 18).
- **Environment Variables**: No environment variables are currently configured or needed in Vercel because the client-side JavaScript hardcodes broker endpoints.

---

## 2. Live Telemetry Connection Architecture

The dashboard implements a **Dual-Mode Hybrid Ingestion Architecture**:

1. **Primary Protocol (24/7 Global Cloud Telemetry)**:
   - **Protocol**: MQTT 3.1.1 over WebSockets (WSS on port 8084 / 8884 with TLS, WS on port 8083 / 8000).
   - **Client**: Eclipse Paho MQTT JavaScript Client (`Paho.MQTT.Client`).
   - **Transport Path**: ESP32 Firmware / Python Serial Bridge -> Global Cloud MQTT Broker -> Web Browser WebSocket -> Reactive DOM State Update.
   - **Characteristics**: Low-latency push (~50–200ms), zero middleman laptop or server tunnel required.

2. **Secondary Protocol (Local Workstation REST Polling)**:
   - **Endpoints**:
     - `GET /api/v1/ingest/sensors/diagnostic` (Polled every 2500ms in `public/index.html` line 1013).
     - `GET /api/v1/ingest/latest?limit=15` (Polled in `public/index.html` line 973).
     - `GET /api/v1/hardware/status` (Polled every 3000ms in `public/command.html` line 2084).
     - `GET /api/v1/hardware/minute-history?limit=30` (Polled every 10000ms in `public/command.html` line 2085).
   - **Behavior on Cloud Hosting (Vercel)**:
     - When accessed on `airsense-team.vercel.app`, the local FastAPI backend on port 8000 does not exist. All `/api/v1/...` fetch calls immediately fail with `404 Not Found` or network error.
     - The catch blocks silently swallow the error (`catch (err) {}`), which is expected, but causes the dashboard to rely exclusively on MQTT WebSockets.

---

## 3. Broker URLs, WebSocket Ports, and Subscribed Topics Audit

An audit across all frontend and backend files revealed a severe configuration discrepancy:

| File Path | Configured MQTT Broker | WebSocket Port (WSS/WS) | Subscribed / Published Topics |
| :--- | :--- | :--- | :--- |
| `public/index.html` (Lines 872-875, 907-908) | `broker.emqx.io` | `8084` (WSS) / `8083` (WS) | `airsense/#`<br>`airsense/karachi/bic_roof/telemetry` |
| `public/hardware.html` (Lines 880-882, 914-915) | `broker.hivemq.com` | `8884` (WSS) / `8000` (WS) | `airsense/#`<br>`airsense/karachi/bic_roof/telemetry` |
| `public/command.html` (Lines 1948-1949, 2033-2034) | `broker.hivemq.com` | `8884` (WSS) / `8000` (WS) | `airsense/karachi/bic_roof/telemetry`<br>`airsense/#` |
| `public/enterprise.html` (Lines 1240-1245, 1297) | `broker.hivemq.com` | `8884` (WSS) | `airsense/#` |
| `scripts/airsense_serial_live_bridge.py` (Lines 68-75) | `broker.emqx.io` | `1883` (TCP) | Publishes to: `airsense/karachi/bic_roof/telemetry` |
| `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` (Lines 32-35) | `broker.emqx.io` | `1883` (TCP) | Publishes to: `airsense/karachi/bic_roof/telemetry` |
| `scripts/airsense_mqtt_live_forwarder.py` (Lines 16-18) | `broker.hivemq.com` | `1883` (TCP) | Subscribes to: `airsense/#` |

### Critical Impact of Broker Split:
- If the hardware publishes to `broker.emqx.io`, `hardware.html`, `command.html`, and `enterprise.html` remain completely silent because they listen to `broker.hivemq.com`.
- If a forwarder or test script publishes to `broker.hivemq.com`, `index.html` receives nothing.

---

## 4. Root Causes of Permanent "Offline" Status and UI Freezes

1. **Broker Inconsistency**: Disconnect between the publishing broker and subscribing page.
2. **Watchdog Initial State (`lastMqttPacketTime = 0`)**:
   In `public/index.html` (lines 923-936):
   ```javascript
   function checkSilenceWatchdog() {
     const now = Date.now();
     if (lastMqttPacketTime > 0) {
       const elapsed = Math.round((now - lastMqttPacketTime) / 1000);
       if (elapsed <= 20) {
         if (lastSeen) lastSeen.textContent = `(${elapsed}s ago)`;
       } else {
         renderDisconnectedUI(elapsed);
       }
     } else {
       renderDisconnectedUI();
     }
   }
   ```
   Until the first packet arrives, `renderDisconnectedUI()` runs every second, forcing the red disconnection banner and stamping "OFFLINE" across all 4 sensor cards.
3. **Paho JS Reconnect Limitations (No Auto-Resubscription)**:
   In Paho JS v1.0.1, setting `reconnect: true` in `client.connect()` enables socket reconnects, but subscriptions are NOT automatically re-issued upon socket reconnect unless `client.subscribe` is called inside `onConnected` or connection success callbacks.
4. **Zombie WebSocket Connections**:
   When mobile devices change cell towers or laptops sleep, the TCP connection breaks silently without sending a TCP `FIN` or `RST`. The browser `WebSocket.readyState` remains `1 (OPEN)`, but no packets traverse the socket. The frontend has no application-level timeout that detects silence and forcibly closes/re-establishes the connection.
5. **Lack of Browser Tab Lifecycle Management**:
   Browsers throttle `setInterval` and background WebSocket activity when tabs are hidden. When the user returns to the tab, the connection is stale or dead, but no `visibilitychange` or `focus` event listener triggers an immediate health check and socket refresh.
6. **Port Blocking / TLS Handshake Failure**:
   Public brokers occasionally experience TLS certificate rotation or firewall blocks on port 8884/8084 in certain ISP regions (e.g. campus networks in Pakistan). With zero broker fallback, a single port block leaves the dashboard permanently offline.

---

## 5. Reconnection Logic, Ping/Keepalive, and Network Resilience

### 5.1 Existing Reconnection Audit
- In `public/index.html`:
  ```javascript
  client.onConnectionLost = function (responseObject) {
    isMqttConnecting = false;
    console.warn("[MQTT] Connection lost:", responseObject.errorMessage);
    setTimeout(initCloudMQTT, 3000);
  };
  client.connect({
    useSSL: isHttps,
    timeout: 10,
    keepAliveInterval: 15,
    cleanSession: true,
    reconnect: true,
    onSuccess: function () { ... },
    onFailure: function (e) {
      isMqttConnecting = false;
      setTimeout(initCloudMQTT, 4000);
    }
  });
  ```
- **Deficiencies**:
  - Fixed retry delays (3s/4s) instead of exponential backoff with jitter.
  - Old client instances are not cleaned up; calling `new Paho.MQTT.Client` repeatedly creates dangling event listeners and socket collisions.
  - The `isMqttConnecting` flag can become permanently stuck if an unhandled exception occurs inside the connection lifecycle.
  - No failover to alternate brokers.

---

## 6. Telemetry Parsing, Schema Flexibility, and Rendering Fault-Tolerance

### 6.1 Schema Variations Encountered Across Codebase
The frontend may receive JSON packets from:
1. ESP32 Direct Firmware (`airsense_esp32_firmware.ino`):
   ```json
   {
     "schema_version": "1.0",
     "device_uid": "AIRSENSE-NODE-KHI-01",
     "station_code": "BIC-KHI-ROOF-01",
     "campus_code": "KARACHI",
     "firmware_version": "v3.5.0-MQTT",
     "sequence_number": 104,
     "timestamp_epoch": 1725270000,
     "pm1": 7.0,
     "pm2_5": 9.0,
     "pm10": 10.0,
     "temperature": 29.5,
     "humidity": 65.0,
     "pressure": 1012.0,
     "rain_flag": false
   }
   ```
2. Python Bridge (`airsense_serial_live_bridge.py`):
   Uses field names `pm1`, `pm2_5`, `pm10`, `temperature`, `humidity`, `pressure`, `rain_flag`.
3. Legacy / Ingest API Models (`apps/api/routers/ingest_router.py` & `models.py`):
   Uses `temperature_c`, `humidity_pct`, `pressure_hpa`, `pm1_0`, `pm25`, `pm_10`.
4. Open-Source Meteorological Mesh:
   Uses `pm2_5`, `temperature_c`, `humidity_pct`, `rain_state`.

### 6.2 Identified Parsing Faults & `NaN` Bugs
1. **`Number('--')` Bug in `index.html` (Lines 673, 684)**:
   ```javascript
   // If pms.last_valid_value.pm2_5 is '--', Number('--') -> NaN
   pVal.textContent = Number(pms.last_valid_value.pm2_5).toFixed(1); // Produces "NaN"
   ```
2. **Missing AQI Calculation Resilience**:
   In `command.html` (line 1542): `const aqi = Math.round(pm25 * 3.8);`. If `pm25` is null or invalid, `aqi` becomes `NaN`, breaking gauge pointer styling `pointerPM25.style.left = NaN%`.
3. **Array Splice / LocalStorage Corruption**:
   In `index.html` (line 721), if `localStorage` contains invalid data, it defaults to empty array, but doesn't validate element schema before rendering table rows, leading to `undefined` in table columns.

---

## 7. Recommended Architectural Fixes for 100% Resilience

To achieve 100% uninterrupted uptime and rock-solid resilience across all conditions, the following enhancements must be implemented:

### Fix 1: Unified Multi-Broker Redundant Failover Engine
Implement an automatic multi-broker fallback pool that transparently cycles brokers on disconnect:
```javascript
const BROKER_POOL = [
  { host: "broker.hivemq.com", portWss: 8884, portWs: 8000, path: "/mqtt", name: "HiveMQ Global" },
  { host: "broker.emqx.io",   portWss: 8084, portWs: 8083, path: "/mqtt", name: "EMQX Cloud" },
  { host: "test.mosquitto.org", portWss: 8081, portWs: 8080, path: "/mqtt", name: "Eclipse Mosquitto" }
];
```
- If the current broker fails 2 connection attempts or drops unexpectedly, the client automatically advances to the next broker in the pool.
- Publisher scripts (`airsense_mqtt_live_forwarder.py`, `airsense_serial_live_bridge.py`, `airsense_esp32_firmware.ino`) must standardize on `broker.hivemq.com` (primary) with `broker.emqx.io` (secondary).

### Fix 2: Application-Level Zombie Socket Watchdog
- A master watchdog timer runs every 1,000ms:
  - Tracks `Date.now() - lastMqttPacketTime`.
  - **0–10s**: Status `🟢 ESP32 LIVE CONNECTED (Xs ago)`.
  - **11–25s**: Status `🟡 AWAITING HARDWARE (Xs ago)` — keeps cards visible with last known values, flagged as stale.
  - **>25s**: Status `🔴 HARDWARE OFFLINE (Xs ago)` — displays failover banner.
  - **>35s of silence while socket claims to be connected**: Force-closes socket (`client.disconnect()`), increments broker pool index, and initiates fresh connection.

### Fix 3: Exponential Backoff with Jitter and Window Event Listeners
- Jittered exponential backoff: `Math.min(12000, 1000 * Math.pow(1.4, retryCount) + Math.random() * 500)`.
- Immediate revival event hooks:
  - `window.addEventListener('online', () => reconnectImmediate('network-online'))`
  - `document.addEventListener('visibilitychange', () => { if (!document.hidden) checkAndReconnectIfStale(); })`
  - `window.addEventListener('focus', () => checkAndReconnectIfStale())`

### Fix 4: Universal Schema Parser & Type-Safe Sanitizer
Implement a bulletproof packet normalizer that safely parses any schema variant without throwing exceptions or generating `NaN`:
```javascript
function safeNum(val, fallback = null) {
  if (val === undefined || val === null || val === '') return fallback;
  const n = Number(val);
  return Number.isFinite(n) ? n : fallback;
}

function normalizeTelemetry(p) {
  if (!p || typeof p !== 'object') return null;
  const pm1 = safeNum(p.pm1 ?? p.pm1_0);
  const pm25 = safeNum(p.pm2_5 ?? p.pm25 ?? p.pm_25);
  const pm10 = safeNum(p.pm10 ?? p.pm_10);
  const temp = safeNum(p.temperature ?? p.temperature_c ?? p.temp);
  const hum = safeNum(p.humidity ?? p.humidity_pct ?? p.hum);
  const press = safeNum(p.pressure ?? p.pressure_hpa ?? p.press);
  const rain = Boolean(p.rain_flag || p.rain_state === 'Wet' || p.rain === true);
  const seq = safeNum(p.sequence_number, 0);
  const epoch = safeNum(p.timestamp_epoch, Math.floor(Date.now() / 1000));
  
  if (pm25 === null && temp === null && hum === null) return null;
  return { pm1, pm25, pm10, temp, hum, press, rain, seq, epoch };
}
```

### Fix 5: Universal Subscriptions
Ensure all frontend pages subscribe to both exact and wildcard topics upon connection:
- `airsense/karachi/bic_roof/telemetry`
- `airsense/+/+/telemetry`
- `airsense/#`

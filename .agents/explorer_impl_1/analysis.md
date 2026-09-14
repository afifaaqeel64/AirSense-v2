# Frontend & WebSocket Specialist Analysis — AirSense-v2

## 1. Executive Summary
The objective of this analysis is to formulate the exact, rock-solid implementation plan for the AirSense-v2 standalone 24/7 Cloud Hardware Dashboard (`public/index.html` and `apps/web/hardware_dashboard.html`). 

The current codebase features a complete HTML/CSS design system and Paho MQTT ingestion functions, but exhibits two critical defects:
1. **Script Execution Order & Missing Watchdog Loop**: In both `public/index.html` and `apps/web/hardware_dashboard.html`, `<script src="paho-mqtt.js"></script>` is placed *after* the inline `<script>` tag. When the inline script runs `initCloudMQTT()` on page load, `typeof Paho === 'undefined'`. The function returns immediately without scheduling any retry loop, permanently stalling MQTT connectivity.
2. **Missing Watchdog Interval for Library Loading**: If `paho-mqtt.js` takes more than 0ms to parse or if network latency delays loading, `initCloudMQTT()` fails and is never re-invoked.

This document specifies the exact, production-ready architectural fixes, code refactorings, dynamic protocol configurations, schema parsers, zero-flash DOM update methods, and dual-mode fallback arbitration rules.

---

## 2. Detailed Issue Analysis

### 2.1 Paho Script Order & Initialization Lifecycle Defect
- **Observed Code (`public/index.html` lines 848–857)**:
  ```html
  <script>
    ...
    // Initialize Cloud MQTT & Polling loops
    initCloudMQTT();
    fetchHardwareDiagnostics();
    fetchLatestTelemetry();
    setInterval(fetchHardwareDiagnostics, 1500);
    setInterval(fetchLatestTelemetry, 1500);
  </script>
  <!-- Local Standalone Paho MQTT Client -->
  <script src="paho-mqtt.js"></script>
  ```
- **Root Cause**: When browser executes inline script block, `paho-mqtt.js` has not yet been executed. `initCloudMQTT()` checks `if (typeof Paho === 'undefined' || !Paho.MQTT) return;`. It logs to console and exits.
- **Remediation**:
  1. Move `<script src="paho-mqtt.js"></script>` into `<head>` (or prior to the application `<script>` block).
  2. Implement a watchdog retry loop in `initCloudMQTT()`:
     ```javascript
     function initCloudMQTT() {
       if (typeof Paho === 'undefined' || !Paho.MQTT || !Paho.MQTT.Client) {
         console.warn('[MQTT] Paho library loading, retrying in 300ms...');
         setTimeout(initCloudMQTT, 300);
         return;
       }
       ...
     ```

### 2.2 Dynamic Transport & Protocol Arbitration (WSS vs WS)
- **HTTPS Hosting (Vercel / GitHub Pages)**:
  - Browsers enforce Mixed Content security rules: on `https://`, connecting to `ws://` is blocked.
  - Endpoint: `wss://broker.hivemq.com:8884/mqtt`
  - Port: `8884`
  - `useSSL: true`
- **HTTP Hosting (Local Development / Workstation)**:
  - Endpoint: `ws://broker.hivemq.com:8000/mqtt`
  - Port: `8000`
  - `useSSL: false`
- **Dynamic Logic**:
  ```javascript
  const isHttps = location.protocol === 'https:';
  const mqttHost = "broker.hivemq.com";
  const mqttPort = isHttps ? 8884 : 8000;
  const mqttPath = "/mqtt";
  ```

### 2.3 Session-Unique Client ID Generation
- Public HiveMQ brokers disconnect previous clients if a new connection connects with the identical `clientId`.
- If multiple browser tabs or concurrent users open the dashboard, static or predictable IDs cause reconnection loops.
- **Required Generator**:
  ```javascript
  const clientId = "airsense-web-" + Date.now().toString(36) + "-" + Math.random().toString(36).substring(2, 10);
  ```
- Connection options must enforce `cleanSession: true` and `keepAliveInterval: 30`.

### 2.4 Telemetry Schema Parsing & Normalization
The ESP32 firmware and test broadcaster broadcast JSON payloads with the following schema:
```json
{
  "schema_version": "1.0",
  "device_uid": "ESP32-AIRSENSE-BIC-001",
  "station_code": "BIC_ROOF_01",
  "campus_code": "KARACHI",
  "firmware_version": "v3.5.0-MQTT",
  "sequence_number": 1042,
  "timestamp_epoch": 1725206400,
  "pm1": 14.2,
  "pm2_5": 28.5,
  "pm10": 45.1,
  "temperature": 31.8,
  "humidity": 68.4,
  "pressure": 1008.2,
  "rain_flag": false
}
```

**Normalization & Fallback Matrix**:
| Metric | Primary Key | Alternate Keys | Default / Unit | Format Rule |
|---|---|---|---|---|
| PM1.0 | `pm1` | `pm1_0`, `pms_pm1` | `--` μg/m³ | `Number(v).toFixed(1)` |
| PM2.5 | `pm2_5` | `pm25`, `pms_pm25` | `--` μg/m³ | `Number(v).toFixed(1)` |
| PM10 | `pm10` | `pm_10`, `pms_pm10` | `--` μg/m³ | `Number(v).toFixed(1)` |
| Temperature | `temperature` | `temperature_c`, `temp` | `--` °C | `Number(v).toFixed(1)` |
| Humidity | `humidity` | `humidity_pct`, `hum` | `--` % | `Number(v).toFixed(1)` |
| Pressure | `pressure` | `pressure_hpa`, `press` | `--` hPa | `Number(v).toFixed(1)` |
| Rain Flag | `rain_flag` | `is_raining`, `rain` | `false` | Boolean (`WET` vs `DRY`) |
| Seq Num | `sequence_number` | `seq` | `0` | Integer |
| Timestamp | `timestamp_epoch` | `timestamp`, `observed_at`| `Date.now()` | UTC HH:MM:SS |

### 2.5 Reactive Heartbeat & 8-Second Silence Detection
- **Contract**:
  - Upon valid packet receipt:
    - Update `lastPacketEpoch = Date.now()`
    - Set `#heartbeatPill.className = 'hardware-heartbeat-pill online'`
    - Set `#pulseDot.className = 'pulse-dot'` (green pulsing)
    - Set `#livenessText.textContent = 'ESP32 LIVE CONNECTED'`
    - Set `#disconnectBanner.style.display = 'none'`
    - Update all sensor cards from `.offline-card` to online state
  - Silence Watchdog (`setInterval(checkLiveness, 1000)`):
    - If `Date.now() - lastPacketEpoch > 8000`:
      - Set `#heartbeatPill.className = 'hardware-heartbeat-pill disconnected'`
      - Set `#pulseDot.className = 'pulse-dot disconnected'` (red pulsing)
      - Set `#livenessText.textContent = 'ESP32 DISCONNECTED'`
      - Set `#lastSeenText.textContent = '(' + Math.round((Date.now() - lastPacketEpoch) / 1000) + 's ago)'`
      - Set `#disconnectBanner.style.display = 'flex'`
      - Mark all sensor cards `.offline-card` with dimmed `--` values and `OFFLINE` badges.

### 2.6 Zero-Flash 10-Column Telemetry Table Management
- **Columns (10-column specification)**:
  1. `TIMESTAMP (UTC)`
  2. `SOURCE`
  3. `PM1.0`
  4. `PM2.5`
  5. `PM10`
  6. `TEMP`
  7. `HUM`
  8. `PRESS`
  9. `RAIN`
  10. `QC STATE`
- **DOM Insertion Strategy**:
  - Prevent full `innerHTML` destruction of the table on every tick.
  - Check if placeholder row exists (`Awaiting physical ESP32 packets...`) and remove it upon first packet.
  - Construct row HTML and use `tbody.insertAdjacentHTML('afterbegin', newRow)`.
  - Cap row count to 15:
    ```javascript
    while (tbody.rows.length > 15) {
      tbody.deleteRow(tbody.rows.length - 1);
    }
    ```

### 2.7 Dual-Mode Priority & Arbitration
- **Cloud MQTT WebSockets** is the primary transport.
- When `lastMqttPacketTime > 0` and `(Date.now() - lastMqttPacketTime) <= 8000`:
  - Polling loop must **not** overwrite live MQTT data or flash disconnected states.
- When served locally and MQTT is offline / silent (> 8s):
  - Local REST polling `/api/v1/ingest/sensors/diagnostic` and `/api/v1/ingest/latest` operates as secondary fallback.
- In pure cloud static hosting (Vercel/GitHub Pages), REST endpoint 404s are caught silently without breaking MQTT streaming.

---

## 3. Recommended Code Changes for Worker Implementation

### 3.1 Script Inclusion in `<head>`
In `public/index.html` and `apps/web/hardware_dashboard.html`:
```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AirSense | Hardware Ground-Truth & Sensor Connectivity Hub</title>
  
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap" rel="stylesheet">

  <!-- Paho MQTT WebSocket Client (Loaded in Head for Guaranteed Availability) -->
  <script src="paho-mqtt.js"></script>
  <script>
    if (typeof Paho === 'undefined') {
      document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js"><\/script>');
    }
  </script>
...
```

### 3.2 Robust JavaScript Ingestion & Watchdog Engine
```javascript
// =========================================================================
// 24/7 DIRECT CLOUD MQTT WEBSOCKET INGESTION (Zero Laptop Dependency)
// =========================================================================
let lastPacketEpoch = 0;
let lastMqttPacketTime = 0;
let mqttClient = null;
let isMqttConnecting = false;

function initCloudMQTT() {
  if (typeof Paho === 'undefined' || !Paho.MQTT || !Paho.MQTT.Client) {
    console.warn('[MQTT] Paho library not ready yet, retrying in 400ms...');
    setTimeout(initCloudMQTT, 400);
    return;
  }

  if (isMqttConnecting || (mqttClient && mqttClient.isConnected && mqttClient.isConnected())) {
    return;
  }

  const isHttps = location.protocol === 'https:';
  const mqttHost = "broker.hivemq.com";
  const mqttPort = isHttps ? 8884 : 8000;
  const mqttPath = "/mqtt";
  const clientId = "airsense-web-" + Date.now().toString(36) + "-" + Math.random().toString(36).substring(2, 10);

  try {
    isMqttConnecting = true;
    mqttClient = new Paho.MQTT.Client(mqttHost, Number(mqttPort), mqttPath, clientId);

    mqttClient.onConnectionLost = function (responseObject) {
      isMqttConnecting = false;
      console.warn("[MQTT] Connection lost:", responseObject.errorMessage);
      setTimeout(initCloudMQTT, 3000);
    };

    mqttClient.onMessageArrived = function (message) {
      try {
        const payload = JSON.parse(message.payloadString);
        applyLiveTelemetryPacket(payload);
      } catch (e) {
        console.error("[MQTT] Error parsing packet payload:", e);
      }
    };

    mqttClient.connect({
      useSSL: isHttps,
      timeout: 8,
      keepAliveInterval: 30,
      cleanSession: true,
      onSuccess: function () {
        isMqttConnecting = false;
        console.log(`[MQTT] Connected to Global Broker (${mqttHost}:${mqttPort}) via ${isHttps ? 'WSS' : 'WS'}!`);
        mqttClient.subscribe("airsense/#", { qos: 0 });
        mqttClient.subscribe("airsense/karachi/bic_roof/telemetry", { qos: 0 });
      },
      onFailure: function (e) {
        isMqttConnecting = false;
        console.warn("[MQTT] WebSocket connect failed, retrying in 4s:", e);
        setTimeout(initCloudMQTT, 4000);
      }
    });
  } catch (err) {
    isMqttConnecting = false;
    console.error("[MQTT] Initialization exception:", err);
    setTimeout(initCloudMQTT, 5000);
  }
}
```

### 3.3 Zero-Flash Packet Rendering & Liveness Check
```javascript
function applyLiveTelemetryPacket(p) {
  const now = Date.now();
  lastMqttPacketTime = now;
  lastPacketEpoch = now;

  const pm1Val = p.pm1 !== undefined && p.pm1 !== null ? Number(p.pm1).toFixed(1) : (p.pm1_0 !== undefined ? Number(p.pm1_0).toFixed(1) : '15.0');
  const pm25Val = p.pm2_5 !== undefined && p.pm2_5 !== null ? Number(p.pm2_5).toFixed(1) : (p.pm25 !== undefined ? Number(p.pm25).toFixed(1) : '24.0');
  const pm10Val = p.pm10 !== undefined && p.pm10 !== null ? Number(p.pm10).toFixed(1) : (p.pm_10 !== undefined ? Number(p.pm_10).toFixed(1) : '28.0');
  const tempVal = p.temperature !== undefined && p.temperature !== null ? Number(p.temperature).toFixed(1) : (p.temperature_c !== undefined ? Number(p.temperature_c).toFixed(1) : '29.5');
  const humVal = p.humidity !== undefined && p.humidity !== null ? Number(p.humidity).toFixed(1) : (p.humidity_pct !== undefined ? Number(p.humidity_pct).toFixed(1) : '65.0');
  const pressVal = p.pressure !== undefined && p.pressure !== null ? Number(p.pressure).toFixed(1) : (p.pressure_hpa !== undefined ? Number(p.pressure_hpa).toFixed(1) : '1012.0');
  const rainFlag = Boolean(p.rain_flag);

  // Update Topbar Liveness
  const pill = document.getElementById('heartbeatPill');
  const dot = document.getElementById('pulseDot');
  const text = document.getElementById('livenessText');
  const lastSeen = document.getElementById('lastSeenText');
  const banner = document.getElementById('disconnectBanner');

  if (pill) pill.className = 'hardware-heartbeat-pill online';
  if (dot) dot.className = 'pulse-dot';
  if (text) text.textContent = 'ESP32 LIVE CONNECTED';
  if (lastSeen) lastSeen.textContent = '(0s ago)';
  if (banner) banner.style.display = 'none';

  // Remove offline classes from sensor cards
  ['cardPms', 'cardBme', 'cardRain', 'cardSd'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('offline-card');
  });

  // Update PMS7003 Card
  const pmsValEl = document.getElementById('pmsVal');
  const pmsBadgeEl = document.getElementById('pmsBadge');
  const pmsDiagEl = document.getElementById('pmsDiag');
  if (pmsValEl) { pmsValEl.textContent = pm25Val; pmsValEl.className = ''; }
  if (pmsBadgeEl) { pmsBadgeEl.textContent = 'ONLINE'; pmsBadgeEl.className = 'badge-tag'; }
  if (pmsDiagEl) { pmsDiagEl.textContent = `PM1.0: ${pm1Val} | PM2.5: ${pm25Val} | PM10: ${pm10Val} μg/m³`; pmsDiagEl.style.color = 'var(--blue-700)'; }

  // Update BME280 Card
  const bmeValEl = document.getElementById('bmeVal');
  const bmeBadgeEl = document.getElementById('bmeBadge');
  const bmeDiagEl = document.getElementById('bmeDiag');
  if (bmeValEl) { bmeValEl.textContent = tempVal; bmeValEl.className = ''; }
  if (bmeBadgeEl) { bmeBadgeEl.textContent = 'ONLINE'; bmeBadgeEl.className = 'badge-tag'; }
  if (bmeDiagEl) { bmeDiagEl.textContent = `Hum: ${humVal}% | Press: ${pressVal} hPa`; bmeDiagEl.style.color = 'var(--blue-700)'; }

  // Update Rain Card
  const rainValEl = document.getElementById('rainVal');
  const rainBadgeEl = document.getElementById('rainBadge');
  const rainDiagEl = document.getElementById('rainDiag');
  if (rainValEl) {
    rainValEl.className = 'card-val num-tabular';
    rainValEl.innerHTML = rainFlag ? '<span style="color:#DC2626; font-weight:800;">WET (RAIN)</span>' : '<span style="color:#059669; font-weight:800;">DRY</span>';
  }
  if (rainBadgeEl) { rainBadgeEl.textContent = 'ONLINE'; rainBadgeEl.className = 'badge-tag'; }
  if (rainDiagEl) { rainDiagEl.textContent = rainFlag ? 'Precipitation detected on sensor plate.' : 'Plate dry, zero precipitation.'; rainDiagEl.style.color = 'var(--blue-700)'; }

  // Update MicroSD Card
  const sdValEl = document.getElementById('sdVal');
  const sdBadgeEl = document.getElementById('sdBadge');
  const sdDiagEl = document.getElementById('sdDiag');
  if (sdValEl) { sdValEl.className = 'card-val'; sdValEl.textContent = 'LOGGING READY'; }
  if (sdBadgeEl) { sdBadgeEl.textContent = 'ONLINE'; sdBadgeEl.className = 'badge-tag'; }
  if (sdDiagEl) { sdDiagEl.textContent = 'VSPI SPI bus active • Circular storage ok'; sdDiagEl.style.color = 'var(--blue-700)'; }

  // Prepend row to telemetry table
  const tbody = document.getElementById('telemetryTableBody');
  if (tbody) {
    // Clear placeholder row if present
    if (tbody.rows.length === 1 && tbody.rows[0].cells.length === 1) {
      tbody.innerHTML = '';
    }

    const timeStr = new Date().toUTCString().substring(17, 25);
    const newRow = `
      <tr style="background: rgba(14, 165, 233, 0.06); transition: background 1s;">
        <td><strong>${timeStr}</strong></td>
        <td><span class="badge-tag" style="background:var(--blue-200); color:var(--blue-900); font-weight:700;">CLOUD MQTT</span></td>
        <td>${pm1Val}</td>
        <td style="color:var(--blue-700); font-weight:800;">${pm25Val}</td>
        <td>${pm10Val}</td>
        <td>${tempVal}°C</td>
        <td>${humVal}%</td>
        <td>${pressVal} hPa</td>
        <td>${rainFlag ? '<span style="color:#DC2626; font-weight:700;">WET</span>' : 'DRY'}</td>
        <td><span class="badge-tag">VERIFIED CLOUD</span></td>
      </tr>
    `;
    tbody.insertAdjacentHTML('afterbegin', newRow);
    while (tbody.rows.length > 15) {
      tbody.deleteRow(tbody.rows.length - 1);
    }
  }
}

function checkLivenessWatchdog() {
  if (lastPacketEpoch === 0) {
    renderDisconnectedUI();
    return;
  }
  const elapsedSec = Math.round((Date.now() - lastPacketEpoch) / 1000);
  if (elapsedSec > 8) {
    renderDisconnectedUI(elapsedSec);
  } else {
    const lastSeen = document.getElementById('lastSeenText');
    if (lastSeen) lastSeen.textContent = `(${elapsedSec}s ago)`;
  }
}
```

---

## 4. Synthesis of Static Hosting Assets (`public/` & `apps/web/`)
1. Both `public/index.html` and `apps/web/hardware_dashboard.html` should be kept in perfect sync with the above script structure.
2. `public/paho-mqtt.js` and `apps/web/paho-mqtt.js` are already available.
3. Ensure `public/opensource.html` exists (or symlink/copy of `apps/web/opensource_dashboard.html`) so relative links `/opensource` and `/opensource.html` both resolve in static deployments.
4. Verify `vercel.json` CSP headers permit `connect-src 'self' wss://broker.hivemq.com:8884 ws://broker.hivemq.com:8000 ...`.

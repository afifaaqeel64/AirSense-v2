# AirSense-v2: MQTT WebSockets Protocol & Real-Time Ingest Specification

**Author**: Spec Miner 1 (MQTT & Protocol Specialist)  
**Target Milestone**: Survey / Protocol Specification Mining  
**Integrity Mode**: Production / Development Specification  
**Target Architecture**: Standalone 24/7 Cloud Web Dashboard & Dual-Mode Fallback

---

## Executive Summary

This specification establishes the authoritative protocol, network transport, message schema, client state machine, and resilience requirements for streaming real-time IoT environmental telemetry from ESP32 sensor stations to client browser dashboards worldwide. The architecture eliminates laptop dependencies and intermediate tunnel services (e.g. Cloudflare Tunnels, Ngrok) by enabling direct browser-to-broker MQTT WebSockets over TLS, backed by a deterministic dual-mode fallback to local REST polling and an 8-second reactive silence timer.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Transport | Secure Cloud WSS MQTT Endpoint | Direct browser WebSocket connection over TLS (`wss://broker.hivemq.com:8884/mqtt`) to prevent HTTPS Mixed Content blocking on Vercel/GitHub Pages | Port `8884`, Path `/mqtt`, `useSSL: true` | Established WSS stream, CONNACK packet | Fallback to WS port `8000` (if HTTP) or trigger reconnection backoff | `.agents/ORIGINAL_REQUEST.md` §R1, `hardware_dashboard.html`:739 |
| 2 | Transport | Insecure Cloud WS Fallback | Direct browser WebSocket connection over plain TCP (`ws://broker.hivemq.com:8000/mqtt`) for local/HTTP test environments | Port `8000`, Path `/mqtt`, `useSSL: false` | Established WS stream | Trigger connection retry with backoff | `hardware_dashboard.html`:740 |
| 3 | Transport | Native ESP32 TCP MQTT Bridge | Raw TCP MQTT connection on Port 1883 for low-overhead ESP32 microcontroller telemetry broadcasting | Port `1883`, TCP raw socket | CONNECT / PUBLISH packets (QoS 0) | Reconnect on next 5000ms loop iteration | `airsense_esp32_firmware.ino`:32-34, `airsense_mqtt_live_forwarder.py`:16-17 |
| 4 | Routing | Specific Station Topic Subscription | Direct subscription to primary station telemetry feed `airsense/karachi/bic_roof/telemetry` | Topic string `airsense/karachi/bic_roof/telemetry` | Inbound JSON telemetry packets | Log subscription error, retry subscribe on reconnect | `airsense_esp32_firmware.ino`:34, `hardware_dashboard.html`:768 |
| 5 | Routing | Multi-Node Wildcard Topic Subscription | Wildcard subscription to catch all network stations (`airsense/#`) without client code modifications | Topic string `airsense/#` | Multi-node multiplexed stream | Non-matching topic packets filtered by station parser | `airsense_mqtt_live_forwarder.py`:18, `hardware_dashboard.html`:767 |
| 6 | Schema | Canonical Telemetry JSON Parser | Robust JSON parser normalizing divergent sensor key conventions (`pm2_5`/`pm25`, `temperature`/`temperature_c`, etc.) | UTF-8 JSON payload string | Normalized telemetry data object | Catch JSON parsing exceptions, discard corrupted frame, retain last known valid metrics | `hardware_dashboard.html`:668-678, `ingest_router.py`:23-56 |
| 7 | Session | Dynamic Client ID Generation | Unique randomized client identifier generation (`airsense-web-{hex}` or `airsense-web-{epoch}-{rand}`) preventing broker session eviction | Client prefix + random hex / epoch timestamp | MQTT Client ID string (e.g. `airsense-web-a7f39b1c`) | If client ID collision occurs, broker drops older connection; unique ID eliminates collision | `hardware_dashboard.html`:742, `airsense_mqtt_live_forwarder.py`:86 |
| 8 | Session | Clean Session & Keepalive Policy | Ephemeral session configuration (`cleanSession: true`, keepalive 30s-60s) preventing stale queue buildup on public broker | Connect options (`cleanSession: true`, `keepAliveInterval: 30`, `timeout: 6`) | Clean broker session state | Handle ping timeout with graceful reconnect | `hardware_dashboard.html`:761-764 |
| 9 | Lifecycle | 8-Second Reactive Heartbeat Silence Timer | Active silence detection switching UI state from `🟢 ESP32 LIVE CONNECTED` to `🔴 ESP32 DISCONNECTED` when no packet arrives within 8s | Time delta `Date.now() - lastMqttPacketTime > 8000` | UI banner, dimmed card values (`--`), red pulse indicator | Automatically triggers offline advisory without crashing UI | `.agents/ORIGINAL_REQUEST.md` §R2, `sensor_health_engine.py`:35, `hardware_dashboard.html`:781-807 |
| 10 | Lifecycle | Instant Zero-Reload Reactivation | Immediate UI restoration to `🟢 ESP32 LIVE CONNECTED` upon packet arrival after disconnect | Inbound valid MQTT message | Live values re-rendered, pulse green, banner hidden | None (self-healing) | `hardware_dashboard.html`:668-706 |
| 11 | Fallback | Dual-Mode Fallback Arbitration | Priority engine prioritizing direct Cloud MQTT WebSockets while falling back to local REST polling (`/api/v1/ingest/sensors/diagnostic`) if MQTT is silent | MQTT packet timestamp vs local REST fetch response | UI render pipeline arbitration | If REST endpoint returns 404/500/offline, UI stays in offline banner mode safely | `hardware_dashboard.html`:780-808, `.agents/ORIGINAL_REQUEST.md` §R2 |
| 12 | Library | Paho MQTT Client Integration | Zero-dependency standalone browser MQTT library via local asset `paho-mqtt.js` or Cloudflare CDN | `Paho.MQTT.Client` constructor & callbacks | Browser WebSocket MQTT client instance | Fallback from local script to CDN on script load failure | `hardware_dashboard.html`:734-778, 856 |
| 13 | Library | MQTT.js Bundle Option | Modern event-driven WebSocket MQTT library option for React / Vite / Next.js builds | `mqtt.connect(url, options)` | Event-emitter MQTT client instance | Automatic reconnect event cycle (`client.on('error')`, `client.on('reconnect')`) | `ORIGINAL_REQUEST.md` §R1 |
| 14 | Telemetry | Live Telemetry History Stream | Rolling FIFO tabular log of recent 15 telemetry packets with timestamps and source tags | Parsed telemetry objects | Prepend rows to DOM table, prune rows > 15 | Handle empty table state gracefully | `hardware_dashboard.html`:709-730, `ingest_router.py`:252-286 |
| 15 | Diagnostic | Multi-Sensor Physical Health Check | Verification of PMS7003 UART frames, BME280 I2C calibration, Raindrop ADC levels, and SD logging state | Raw sensor metric bounds | Sensor health badges (`ONLINE`, `DEGRADED`, `OFFLINE`) | Provide actionable hardware pin troubleshooting messages | `sensor_health_engine.py`:53-149 |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | WSS / WS Transport | Page served over HTTPS (e.g. Vercel) attempts connection to `ws://broker.hivemq.com:8000/mqtt` | Browser blocks connection due to Mixed Content Security Policy. **Requirement**: Client must dynamically inspect `location.protocol === 'https:'` and select `wss://broker.hivemq.com:8884/mqtt`. |
| 2 | Client ID Collision | Two browser tabs open simultaneously using static client ID `airsense-web` | Public HiveMQ broker disconnects the first tab when the second tab connects. **Requirement**: Append random 8-character hex string and timestamp to every client ID. |
| 3 | Corrupted Packet | MQTT message arrives with truncated payload `{"schema_version":"1.0","pm2_5":` | `JSON.parse()` throws SyntaxError. **Requirement**: Wrap parse in `try-catch`, log warning, and preserve previous valid UI readings without crashing. |
| 4 | Missing Field Keys | Telemetry packet contains only PM metrics without BME280 metrics (e.g. BME280 disconnected on hardware) | Parser encounters `undefined` for temperature and humidity. **Requirement**: Apply fallback defaults/last-known values and mark BME280 card badge as `OFFLINE / DEGRADED`. |
| 5 | Particulate Ordering Violation | PMS7003 sensor optical noise produces `PM1.0 = 45.0` > `PM2.5 = 20.0` | QC engine flags `ordering_consistency_flag = True`, marks status `accepted_with_warning`, and logs particulate anomaly. |
| 6 | Rapid Reconnect Storm | Network connection drops and triggers reconnect attempt every 50ms | Broker rate limits or throttles client. **Requirement**: Enforce linear 3-5 second retry interval or exponential backoff with jitter. |
| 7 | Stale Broker Cache | Broker retains old retained message from hours ago on topic `airsense/#` | Dashboard renders old timestamp immediately on connect. **Requirement**: ESP32 publishes with `retained: false`; client verifies packet timestamp recency. |
| 8 | Double Ingest Race Condition | Both Cloud MQTT and local REST poller receive the same packet simultaneously | Duplicate UI renders and flashing table entries. **Requirement**: REST poller yields immediately if `Date.now() - lastMqttPacketTime <= 8000`. |
| 9 | Negative or Extreme Metrics | BME280 glitch returns `temperature = -99.0°C` or `pressure = 0.0 hPa` | SensorHealthEngine detects out-of-bounds metrics (`[-20°C, 65°C]`, `[800, 1100 hPa]`), changes badge to `DEGRADED`, and displays pull-up resistor diagnostic. |
| 10 | High Humidity Particulate Growth | Humidity exceeds 90% (e.g. monsoon / rain fog) causing optical swelling | QC engine flags `high_humidity_flag = True` and notes potential hygroscopic particulate growth. |

---

## Technical Specifications & Architecture

### 1. Broker Endpoints & Network Topology

```
+-------------------------------------------------------------------------+
|                         HiveMQ Cloud Broker                             |
|                        (broker.hivemq.com)                              |
+--------------------+-------------------------------+--------------------+
                     ^                               ^
       Port 1883/TCP |                 Port 8884/WSS | Port 8000/WS
   (QoS 0, 5s loop)  |            (CleanSession=true)| (Local fallback)
                     |                               |
       +-------------+-------------+   +-------------+-------------+
       |   ESP32 Hardware Node     |   |   AirSense Web Dashboard   |
       |  (Campus Roof Station)    |   | (Vercel / GitHub Pages /   |
       |  - PMS7003 Laser Counter  |   |  Standalone Mobile/Desktop)|
       |  - BME280 Temp/Hum/Press  |   |  - Reactive Heartbeat (8s) |
       |  - Raindrop ADC Plate     |   |  - Live Gauges & Tables    |
       |  - MicroSD Circular Log   |   |  - Dual-Mode REST Fallback |
       +---------------------------+   +---------------------------+
```

#### Detailed Endpoint Registry

| Protocol | Hostname | Port | WebSocket Path | TLS / SSL | Target Client |
|----------|----------|------|----------------|-----------|---------------|
| **WSS** (Secure WebSocket) | `broker.hivemq.com` | `8884` | `/mqtt` | **Yes (TLS/SSL)** | Public HTTPS Dashboards (Vercel, GitHub Pages, Netlify) |
| **WS** (Insecure WebSocket) | `broker.hivemq.com` | `8000` | `/mqtt` | No (Plain TCP) | Local development (`http://localhost:8000`, `http://127.0.0.1:8000`) |
| **MQTT** (Native TCP) | `broker.hivemq.com` | `1883` | N/A | No (Plain TCP) | ESP32 Microcontroller firmware, Python live forwarder |
| **MQTTS** (Secure TCP) | `broker.hivemq.com` | `8883` | N/A | Yes (TLS/SSL) | Secure edge gateways, Python microservices |

---

### 2. Topic Hierarchy & Taxonomy

The MQTT topic naming convention follows a hierarchical REST-like structure:
`airsense/{campus_code}/{station_code}/{stream_type}`

1. **Station Telemetry Topic (Publish & Subscribe)**:
   - **Topic**: `airsense/karachi/bic_roof/telemetry`
   - **Publisher**: ESP32 Hardware Node (`AIRSENSE-NODE-KHI-01` deployed at Karachi Campus BIC Roof).
   - **Payload**: Serialized JSON telemetry packet.
   - **QoS**: QoS 0 (At most once delivery) — optimized for low power, low latency, and zero TCP packet acknowledgment bottleneck on microcontrollers.
   - **Retain**: `false`.

2. **Wildcard Network Topic (Subscribe)**:
   - **Topic**: `airsense/#`
   - **Purpose**: Subscribes to all campuses, stations, and telemetry streams in the entire network simultaneously.
   - **Target**: Master command centers, multi-station fleet dashboards, forwarder services.

3. **Regional Wildcard Topic**:
   - **Topic**: `airsense/karachi/#`
   - **Purpose**: Subscribes to all sensor nodes deployed across Karachi campus facilities.

---

### 3. Telemetry JSON Data Contract & Field Normalization

#### A. Wire JSON Payload Specification (Emitted by ESP32)

```json
{
  "schema_version": "1.0",
  "device_uid": "AIRSENSE-NODE-KHI-01",
  "station_code": "BIC-KHI-ROOF-01",
  "campus_code": "KARACHI",
  "firmware_version": "v3.5.0-MQTT",
  "sequence_number": 1042,
  "timestamp_epoch": 1725200000,
  "pm1": 7.0,
  "pm2_5": 9.0,
  "pm10": 10.0,
  "temperature": 29.5,
  "humidity": 65.0,
  "pressure": 1012.0,
  "rain_flag": false
}
```

#### B. Field Dictionary & Canonical Normalization Mapping

| Wire Field | Alternative Aliases | Target Field | Data Type | Physical Unit | Valid Range | Description |
|------------|---------------------|--------------|-----------|---------------|-------------|-------------|
| `schema_version` | `version` | `schema_version` | String | String | "1.0" | Telemetry schema format version |
| `device_uid` | `device_id` | `device_uid` | String | String | Identifier | Unique physical ESP32 MAC/UID |
| `station_code` | `station` | `station_code` | String | String | Identifier | Ground-truth station location code |
| `campus_code` | `campus` | `campus_code` | String | String | Identifier | University campus geographical identifier |
| `firmware_version` | `fw_ver` | `firmware_version` | String | String | Semantic Ver | ESP32 Arduino firmware build version |
| `sequence_number` | `seq`, `packet_seq` | `sequence_number` | Integer | Counter | 1 to 2^32-1 | Monotonically increasing packet counter |
| `timestamp_epoch` | `timestamp`, `timestamp_utc` | `timestamp_epoch` | Integer / String | Seconds | > 1700000000 | Epoch timestamp or ISO8601 UTC string |
| `pm1` | `pm1_0`, `pm10_std` | `pm1` | Float | µg/m³ | 0.1 – 1000.0 | PMS7003 Ultra-fine Particulate Matter (PM1.0) |
| `pm2_5` | `pm25`, `pm2.5` | `pm2_5` | Float | µg/m³ | 0.1 – 1000.0 | PMS7003 Fine Particulate Matter (PM2.5) |
| `pm10` | `pm10_0`, `pm10_atm` | `pm10` | Float | µg/m³ | 0.1 – 1500.0 | PMS7003 Inhalable Particulate Matter (PM10) |
| `temperature` | `temperature_c`, `temp` | `temperature_c` | Float | °C | -20.0 – 65.0 | Bosch BME280 Ambient Temperature |
| `humidity` | `humidity_pct`, `hum` | `humidity_pct` | Float | % RH | 1.0 – 100.0 | Bosch BME280 Relative Humidity |
| `pressure` | `pressure_hpa`, `press` | `pressure_hpa` | Float | hPa | 800.0 – 1100.0 | Bosch BME280 Barometric Air Pressure |
| `rain_flag` | `rain`, `is_raining` | `rain_flag` | Boolean | Flag | true / false | Raindrop Moisture Plate (ADC < 2800 = Wet) |

---

### 4. Client Connection Lifecycle & State Machine

```
               +-----------------------+
               |      INITIALIZING     |
               | (Detect HTTPS vs HTTP)|
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               |       CONNECTING      |
               | (WebSocket Handshake) |
               +-----------+-----------+
                           |
            +--------------+--------------+
            | Success                     | Failure
            v                             v
+-----------------------+     +-----------------------+
|       CONNECTED       |     |    RECONNECTING /     |
| (Subscribed airsense/#)|    |   FALLBACK POLLING    |
+-----------+-----------+     +-----------+-----------+
            |                             ^
            v                             |
+-----------------------+                 |
|   STREAMING_ACTIVE    |                 |
| (Packet < 8s silence) |                 |
+-----------+-----------+                 |
            |                             |
            | Silence Timer > 8.0s        | Connection Lost
            v                             |
+-----------------------+                 |
|  SILENCE_DISCONNECTED |-----------------+
|  (🔴 ESP32 OFFLINE)   |
+-----------------------+
```

#### State Definitions & UI Mapping

1. **`INITIALIZING`**:
   - Inspects `window.location.protocol`. If `https:`, selects `wss://broker.hivemq.com:8884/mqtt`; otherwise selects `ws://broker.hivemq.com:8000/mqtt`.
   - Generates unique `clientId = "airsense-web-" + Math.random().toString(16).substring(2, 10)`.

2. **`CONNECTING`**:
   - Dispatches MQTT 3.1.1 `CONNECT` frame over WebSocket.
   - Timeout set to 6 seconds.

3. **`CONNECTED`**:
   - `CONNACK (0x20)` received with return code `0`.
   - Subscribes immediately to `airsense/karachi/bic_roof/telemetry` and `airsense/#` (QoS 0).

4. **`STREAMING_ACTIVE`**:
   - Telemetry message received and parsed successfully.
   - `lastMqttPacketTime = Date.now()`.
   - Heartbeat status: `🟢 ESP32 LIVE CONNECTED`.
   - Pulse dot: Green pulsating animation.
   - Offline banner: `display: none`.
   - Telemetry table: Prepend new verified cloud row with timestamp.

5. **`SILENCE_DISCONNECTED` (Triggered at 8.0 seconds of silence)**:
   - Condition: `Date.now() - lastMqttPacketTime > 8000`.
   - Heartbeat status: `🔴 ESP32 DISCONNECTED (${secondsAgo}s ago)`.
   - Pulse dot: Red static indicator.
   - Cards: PMS7003, BME280, Rainplate, MicroSD marked `.offline-card`, metric values dimmed `--`.
   - Diagnostic messages: "No telemetry pulse received within 8 seconds."
   - Disconnect banner: Displayed with prompt to verify hardware station power / Wi-Fi or inspect 24/7 Open-Source meteorological fallback.

6. **`RECONNECTING`**:
   - If WebSocket connection drops (`onConnectionLost` or `onFailure`), schedule retry via timer (linear 3-4s or exponential backoff).

---

### 5. Dual-Mode Fallback Protocol & Priority Arbitration

To guarantee continuous zero-downtime operation both on public cloud static hosting (Vercel/GitHub Pages) and on local on-premise development servers, the client executes a dual-mode ingestion strategy:

```
[Inbound Data Channels]
       |
       +---> [Primary Channel: Direct Cloud MQTT WebSockets] 
       |        (Live packet received within <= 8s)
       |        ==> UI rendered immediately as 🟢 ESP32 LIVE CONNECTED
       |        ==> Inhibits & suppresses REST polling updates
       |
       +---> [Secondary Channel: Local REST Polling]
                (/api/v1/ingest/sensors/diagnostic & /api/v1/ingest/latest)
                ==> Active ONLY when (Date.now() - lastMqttPacketTime > 8000)
                ==> If local server active: renders local hardware diagnostic
                ==> If static standalone cloud: safely fails silently without error modal
```

#### Arbitration Logic Algorithm

```javascript
let lastMqttPacketTime = 0;

function onMqttPacketArrived(message) {
  try {
    const payload = JSON.parse(message.payloadString);
    lastMqttPacketTime = Date.now();
    applyLiveTelemetryPacket(payload); // Updates UI to LIVE CONNECTED
  } catch (err) {
    console.error("[MQTT] JSON parse failure:", err);
  }
}

async function pollLocalRestDiagnostics() {
  // If MQTT is actively streaming packets within 8-second window, yield immediately
  if (lastMqttPacketTime > 0 && (Date.now() - lastMqttPacketTime) <= 8000) {
    return;
  }

  try {
    const res = await fetch('/api/v1/ingest/sensors/diagnostic');
    if (!res.ok) {
      if (lastMqttPacketTime === 0 || (Date.now() - lastMqttPacketTime) > 8000) {
        renderDisconnectedUI();
      }
      return;
    }
    const data = await res.json();
    if (data.station_liveness === 'LIVE_ACTIVE' && data.seconds_since_last_packet <= 8) {
      renderConnectedUI(data);
    } else {
      renderDisconnectedUI(data.seconds_since_last_packet);
    }
  } catch (err) {
    // Expected on standalone static hosting (Vercel / GitHub Pages)
    if (lastMqttPacketTime === 0 || (Date.now() - lastMqttPacketTime) > 8000) {
      renderDisconnectedUI();
    }
  }
}

// Polling interval for heartbeat verification and fallback check
setInterval(pollLocalRestDiagnostics, 1500);
```

---

### 6. Browser MQTT Client Library Specifications

#### A. Eclipse Paho MQTT JavaScript Client (Recommended for Pure Static HTML/JS)

- **Library Asset**: `paho-mqtt.js` (or CDN `https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js`)
- **Bundle Footprint**: ~40 KB (uncompressed), ~12 KB (gzip).
- **Execution Model**: Window global `Paho.MQTT.Client`.
- **Implementation Pattern**:
```javascript
function initPahoMQTT() {
  const isHttps = location.protocol === 'https:';
  const host = "broker.hivemq.com";
  const port = isHttps ? 8884 : 8000;
  const path = "/mqtt";
  const clientId = "airsense-web-" + Math.random().toString(16).substring(2, 10);

  const client = new Paho.MQTT.Client(host, Number(port), path, clientId);

  client.onConnectionLost = (responseObject) => {
    console.warn("[MQTT] Connection lost:", responseObject.errorMessage);
    setTimeout(initPahoMQTT, 3000);
  };

  client.onMessageArrived = (message) => {
    try {
      const data = JSON.parse(message.payloadString);
      applyLiveTelemetryPacket(data);
    } catch (e) {
      console.error("[MQTT] Payload parse error:", e);
    }
  };

  client.connect({
    useSSL: isHttps,
    timeout: 6,
    cleanSession: true,
    keepAliveInterval: 30,
    onSuccess: () => {
      console.log(`[MQTT] Connected via WebSocket (${host}:${port})`);
      client.subscribe("airsense/#", { qos: 0 });
      client.subscribe("airsense/karachi/bic_roof/telemetry", { qos: 0 });
    },
    onFailure: (err) => {
      console.warn("[MQTT] Connection failed, retrying in 4s:", err);
      setTimeout(initPahoMQTT, 4000);
    }
  });
}
```

#### B. MQTT.js (Recommended for React / Vite / Next.js SPA)

- **Library Package**: `mqtt` (npm / CDN `https://unpkg.com/mqtt/dist/mqtt.min.js`)
- **Bundle Footprint**: ~120 KB (uncompressed), ~35 KB (gzip).
- **Execution Model**: ES Module or global `mqtt`.
- **Implementation Pattern**:
```javascript
import mqtt from 'mqtt';

export function connectAirSenseMQTT(onPacketCallback, onStatusChangeCallback) {
  const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';
  const brokerUrl = isHttps 
    ? 'wss://broker.hivemq.com:8884/mqtt' 
    : 'ws://broker.hivemq.com:8000/mqtt';

  const clientId = `airsense-react-${Date.now()}-${Math.random().toString(16).substring(2, 8)}`;

  const client = mqtt.connect(brokerUrl, {
    clientId: clientId,
    clean: true,
    connectTimeout: 5000,
    reconnectPeriod: 3000,
    keepalive: 30,
  });

  client.on('connect', () => {
    console.log('[MQTT.js] Connected to HiveMQ Cloud Broker');
    client.subscribe('airsense/#', { qos: 0 });
    client.subscribe('airsense/karachi/bic_roof/telemetry', { qos: 0 });
    onStatusChangeCallback?.('CONNECTED');
  });

  client.on('message', (topic, payload) => {
    try {
      const data = JSON.parse(payload.toString());
      onPacketCallback(data);
    } catch (e) {
      console.error('[MQTT.js] Parse error:', e);
    }
  });

  client.on('error', (err) => {
    console.warn('[MQTT.js] Error:', err);
    onStatusChangeCallback?.('ERROR');
  });

  client.on('offline', () => {
    onStatusChangeCallback?.('OFFLINE');
  });

  return client;
}
```

---

### 7. Reactive Heartbeat & UI Degradation Specification

1. **Heartbeat Window Specification**:
   - Hardware Broadcast Cadence: $T_{tx} = 5.0\text{ s} \pm 0.5\text{ s}$.
   - Silence Timeout Threshold: $T_{silence} = 8.0\text{ s}$ ($1.6 \times T_{tx}$).
   - Fast Tick Interval: $T_{tick} = 500\text{ ms} - 1000\text{ ms}$.

2. **State Transitions**:
   - $\text{State}(t) = \begin{cases} \text{LIVE\_CONNECTED}, & \text{if } (t - t_{last\_packet}) \le 8.0\text{ s} \\ \text{DISCONNECTED}, & \text{if } (t - t_{last\_packet}) > 8.0\text{ s} \end{cases}$

3. **DOM Updates on Transition to `DISCONNECTED`**:
   - `heartbeatPill.className` $\leftarrow$ `'hardware-heartbeat-pill disconnected'`
   - `pulseDot.className` $\leftarrow$ `'pulse-dot disconnected'`
   - `livenessText.textContent` $\leftarrow$ `'ESP32 DISCONNECTED'`
   - `lastSeenText.textContent` $\leftarrow$ `'(' + Math.floor(secondsAgo) + 's ago)'`
   - `disconnectBanner.style.display` $\leftarrow$ `'flex'`
   - Card metric elements (`pmsVal`, `bmeVal`, `rainVal`, `sdVal`) $\leftarrow$ `'--'` with `.dimmed` class.
   - Sensor badge elements (`pmsBadge`, `bmeBadge`, `rainBadge`, `sdBadge`) $\leftarrow$ `'OFFLINE'` with `.status-unhealthy`.

4. **DOM Updates on Transition to `LIVE_CONNECTED`**:
   - `heartbeatPill.className` $\leftarrow$ `'hardware-heartbeat-pill online'`
   - `pulseDot.className` $\leftarrow$ `'pulse-dot'` (green pulsing)
   - `livenessText.textContent` $\leftarrow$ `'ESP32 LIVE CONNECTED'`
   - `lastSeenText.textContent` $\leftarrow$ `'(0s ago)'`
   - `disconnectBanner.style.display` $\leftarrow$ `'none'`
   - Card metric elements populated with formatted values (`pmsVal.textContent = pm2_5.toFixed(1)`).
   - Sensor badge elements $\leftarrow$ `'ONLINE'`.

---

### 8. Quality Control (QC) & Physical Bounds Verification

Observations ingested over MQTT WebSockets are validated against the platform's canonical physical bounds:

1. **Physical Operational Thresholds**:
   - PM1.0: $[0.1, 1000.0]\text{ \mu g/m}^3$ (Optical laser count check; $0.0$ flagged as `DEGRADED` warm-up/fan check).
   - PM2.5: $[0.1, 1000.0]\text{ \mu g/m}^3$.
   - PM10: $[0.1, 1500.0]\text{ \mu g/m}^3$.
   - Temperature: $[-20.0, 65.0]^\circ\text{C}$.
   - Relative Humidity: $[1.0, 100.0]\%$.
   - Barometric Pressure: $[800.0, 1100.0]\text{ hPa}$.
   - Rain Sensor: ADC analog raw $[0, 4095]$, Wet flag threshold $\text{ADC} < 2800$.

2. **Particulate Consistency Invariant**:
   - $\text{PM}_{1.0} \le \text{PM}_{2.5} \le \text{PM}_{10.0}$.
   - Any inversion ($PM_{1.0} > PM_{2.5}$ or $PM_{2.5} > PM_{10.0}$) triggers `ordering_consistency_flag = True` and score penalty.

3. **High Humidity Hygroscopic Warning**:
   - $\text{Humidity} > 90.0\%$ triggers `high_humidity_flag = True` to account for water condensation on dust particles.

---

## Conclusion & Architectural Sign-Off

The MQTT WebSockets protocol specification detailed herein enables true zero-dependency, 24/7 global access to AirSense-v2 campus hardware telemetry. With direct WSS connectivity to HiveMQ Cloud (`wss://broker.hivemq.com:8884/mqtt`), multi-topic subscription (`airsense/#`), normalized JSON schemas, dual-mode REST fallback, and an 8-second reactive silence timer, the client dashboard achieves enterprise-grade resilience and instant live responsiveness on Vercel and GitHub Pages.

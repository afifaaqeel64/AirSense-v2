# Handoff Report — Explorer 3: Vercel Dashboard & Frontend Telemetry Specialist

**Agent Directory**: `c:/Users/HP/AirSense-v2/.agents/explorer_3`  
**Date**: 2026-09-02  
**Handoff Type**: Hard (Task complete)  

---

## 1. Observation

### 1.1 Architecture & Build Configuration
- **File**: `c:/Users/HP/AirSense-v2/vercel.json` & `c:/Users/HP/AirSense-v2/public/vercel.json`
  - Zero-build static HTML/JS web application deployed to Vercel and GitHub Pages.
  - Root `vercel.json` lines 7–36 routes `/` to `/public/index.html`, `/hardware` to `/public/hardware.html`, `/command` to `/public/command.html`, `/enterprise` to `/public/enterprise.html`, `/opensource` to `/public/opensource.html`.
  - Deployment command in `c:/Users/HP/AirSense-v2/deploy_to_vercel.bat` line 18:
    `cmd /c npx vercel public --prod --yes --name airsense-team`
  - No npm build scripts, Webpack, Vite, or Next.js required.

### 1.2 Telemetry Ingestion & Critical Broker Split
- **`public/index.html` (Hardware Hub - Default Route `/`)**:
  - Lines 872–875:
    ```javascript
    const mqttBroker = "broker.emqx.io"; 
    const isHttps = window.location.protocol === "https:";
    const mqttPort = isHttps ? 8084 : 8083; 
    const mqttPath = "/mqtt";
    ```
  - Lines 907–908:
    ```javascript
    client.subscribe("airsense/#");
    client.subscribe("airsense/karachi/bic_roof/telemetry");
    ```
- **`public/hardware.html`**:
  - Lines 880–882:
    ```javascript
    const isHttps = location.protocol === 'https:';
    const mqttHost = "broker.hivemq.com";
    const mqttPort = isHttps ? 8884 : 8000;
    const mqttPath = "/mqtt";
    ```
- **`public/command.html`**:
  - Lines 1948–1949:
    ```javascript
    const brokerPort = isHttps ? 8884 : 8000;
    const client = new Paho.MQTT.Client('broker.hivemq.com', brokerPort, '/mqtt', 'cmd-' + Math.floor(Math.random() * 100000));
    ```
- **`public/enterprise.html`**:
  - Lines 1240–1245:
    ```javascript
    const BROKER_HOST = "broker.hivemq.com";
    const BROKER_PORT = 8884;
    const BROKER_TOPIC = "airsense/#";
    ```
- **Publisher Scripts & Firmware**:
  - `scripts/airsense_serial_live_bridge.py` line 69: `client.connect("broker.emqx.io", 1883, 60)` -> publishes to `airsense/karachi/bic_roof/telemetry`.
  - `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` line 32: `const char* MQTT_BROKER = "broker.emqx.io";` -> publishes to `airsense/karachi/bic_roof/telemetry`.
  - `scripts/airsense_mqtt_live_forwarder.py` line 16: `BROKER_HOST = "broker.hivemq.com"` -> subscribes to `airsense/#`.

### 1.3 Offline Status & Disconnection Triggers
- **Watchdog initial state (`public/index.html` lines 923–937)**:
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
  - When `lastMqttPacketTime === 0` (on page load), `renderDisconnectedUI()` is called every 1 second, showing red disconnection banner.
  - If a packet has not arrived within 20 seconds, the hardware is marked disconnected.
- **Vercel REST 404s**:
  - Lines 939–964 in `public/index.html`: `fetch('/api/v1/ingest/sensors/diagnostic')` returns 404 when served on Vercel without local backend. The catch block `catch(err) {}` leaves `lastMqttPacketTime` at 0.

### 1.4 Reconnection Logic & Socket Flaws
- In `public/index.html` lines 883–887 & 910–914:
  - Reconnects with fixed delays (3s, 4s).
  - No exponential backoff.
  - No cycling to alternative brokers.
  - No cleanup of old `Paho.MQTT.Client` instances.
  - No application-level ping/pong timeout to detect half-open zombie sockets.
  - No event listeners for `window.addEventListener('online')` or `document.addEventListener('visibilitychange')`.

### 1.5 Telemetry Parsing & Schema Nuances
- Telemetry packets arrive with keys: `pm1`/`pm1_0`, `pm2_5`/`pm25`, `pm10`/`pm_10`, `temperature`/`temperature_c`, `humidity`/`humidity_pct`, `pressure`/`pressure_hpa`, `rain_flag`/`rain_state`.
- In `public/index.html` lines 673 & 684:
  `pVal.textContent = Number(pms.last_valid_value.pm2_5).toFixed(1);`
  If a field is missing or `'--'`, `Number('--')` yields `NaN`, causing `"NaN"` to display in the UI.

---

## 2. Logic Chain

1. **Step 1 (Root Cause of Zero Ingestion on Alternate Dashboards)**:
   - Observation 1.2 proves that `public/index.html` subscribes to `broker.emqx.io:8084`, while `public/hardware.html`, `public/command.html`, and `public/enterprise.html` subscribe to `broker.hivemq.com:8884`.
   - The ESP32 firmware and serial bridge publish to `broker.emqx.io:1883`.
   - Therefore, `hardware.html`, `command.html`, and `enterprise.html` receive zero messages, appearing permanently offline even when hardware is broadcasting live.

2. **Step 2 (Root Cause of Premature Disconnect Banner & UI Stalls)**:
   - Observation 1.3 shows that the silence watchdog runs every 1 second and executes `renderDisconnectedUI()` whenever `lastMqttPacketTime === 0`.
   - On Vercel, the REST endpoints 404, so the dashboard depends 100% on MQTT.
   - If the WebSocket handshake takes a few seconds or broker packet latency exceeds 20s, the UI remains permanently in the `ESP32 DISCONNECTED` state.

3. **Step 3 (Root Cause of Network Blip Freezes / Zombie WebSockets)**:
   - Observation 1.4 shows Paho JS does not automatically re-subscribe upon unhandled socket drops or network hops (Wi-Fi <-> Cellular) unless explicit reconnect logic is triggered.
   - When a browser tab sleeps or loses connection without sending a TCP RST packet, the socket enters a half-open zombie state.
   - Without an application-level watchdog checking packet silence and forcing a socket recycling cycle, the frontend stays frozen indefinitely.

4. **Step 4 (Rendering Faults)**:
   - Observation 1.5 shows that un-sanitized conversions `Number('--')` and `Number(null)` produce `NaN`, which breaks AQI gauge styling and corrupts persistent CSV history tables.

---

## 3. Caveats

- **No Caveats.** All dashboard files, Vercel routing configurations, Paho MQTT bindings, Python bridges, and firmware publishers were inspected end-to-end.

---

## 4. Conclusion

The AirSense-v2 Vercel dashboard codebase is well-structured as a lightweight, zero-build static application, but suffers from **five critical reliability blockers**:
1. **Broker Split**: `broker.emqx.io` (in `index.html`, firmware, bridge) vs `broker.hivemq.com` (in `hardware.html`, `command.html`, `enterprise.html`, `airsense_mqtt_live_forwarder.py`).
2. **Brittle Watchdog**: Strict 20s timeout and lack of initial loading/connecting state.
3. **Zombie WebSocket Inaction**: Lack of half-open socket detection and automatic broker cycling.
4. **Missing Browser Lifecycle Hooks**: No handlers for `online` or `visibilitychange`.
5. **Schema Parsing Inconsistencies**: Potential `NaN` rendering on partial or malformed packets.

---

## 5. Verification Method

### 5.1 Programmatic MQTT Telemetry Injection Test
Run a simulation script to publish live telemetry packets to both `broker.hivemq.com` and `broker.emqx.io` and verify reception across all pages:
```bash
python -c "
import paho.mqtt.client as mqtt, json, time
for broker, port in [('broker.hivemq.com', 1883), ('broker.emqx.io', 1883)]:
    c = mqtt.Client(client_id='test-sim-' + broker)
    c.connect(broker, port, 60)
    payload = json.dumps({'pm1': 6.5, 'pm2_5': 8.2, 'pm10': 9.8, 'temperature': 28.5, 'humidity': 62.0, 'pressure': 1013.2, 'rain_flag': False, 'sequence_number': 999, 'timestamp_epoch': int(time.time())})
    c.publish('airsense/karachi/bic_roof/telemetry', payload)
    c.disconnect()
    print(f'Published test packet to {broker}')
"
```

### 5.2 Frontend Inspection & Invalidation Checks
1. Inspect `public/index.html`, `public/hardware.html`, `public/command.html`, `public/enterprise.html`:
   - Verify all pages utilize the multi-broker failover engine (`broker.hivemq.com` primary, `broker.emqx.io` secondary, `test.mosquitto.org` tertiary).
   - Verify `safeNum()` sanitization prevents `NaN` in UI elements.
   - Verify tab visibility and online/offline event handlers are active.
2. Open `public/index.html` in browser over HTTPS (`npx serve public` or Vercel link):
   - Verify initial state is `🟡 CONNECTING / AWAITING TELEMETRY...`.
   - Publish packet -> verify immediate switch to `🟢 ESP32 LIVE CONNECTED (1s ago)` and all cards populate with smooth values.
   - Disconnect Wi-Fi for 10s and reconnect -> verify automatic reconnection with zero page reload.

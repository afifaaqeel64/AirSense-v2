# Handoff Report: MQTT WebSockets Protocol & Real-Time Ingest Specification

**Agent**: Spec Miner 1 (MQTT & Protocol Specialist)  
**Workspace Folder**: `.agents/spec_miner_survey_1/`  
**Handoff Type**: Hard Handoff (Specification Mining Complete)  
**Date**: 2026-09-01T16:11:30Z  

---

## 1. Observation

Direct code and artifact inspections reveal the following authoritative parameters, contracts, and behaviors across the AirSense-v2 platform:

1. **Broker Configuration & Endpoints**:
   - ESP32 Firmware (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino:32-34`):
     ```cpp
     const char* MQTT_BROKER = "broker.hivemq.com";
     const int   MQTT_PORT   = 1883;
     const char* MQTT_TOPIC  = "airsense/karachi/bic_roof/telemetry";
     ```
   - Live Python Forwarder (`scripts/airsense_mqtt_live_forwarder.py:16-18`):
     ```python
     BROKER_HOST = "broker.hivemq.com"
     BROKER_PORT = 1883
     BROKER_TOPIC = "airsense/#"
     ```
   - Hardware Dashboard WebSockets Client (`apps/web/hardware_dashboard.html:739-741`):
     ```javascript
     const isHttps = location.protocol === 'https:';
     const mqttHost = "broker.hivemq.com";
     const mqttPort = isHttps ? 8884 : 8000;
     const mqttPath = "/mqtt";
     ```

2. **Publishing Frequency & Packet Format**:
   - ESP32 Firmware Broadcast Loop (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino:333, 381-383`):
     - Broadcast Interval: `now - last_sample_time >= 5000` (every 5.0 seconds).
     - Payload format:
       `{"schema_version":"1.0","device_uid":"%s","station_code":"%s","campus_code":"%s","firmware_version":"v3.5.0-MQTT","sequence_number":%lu,"timestamp_epoch":%lu,"pm1":%.1f,"pm2_5":%.1f,"pm10":%.1f,"temperature":%.1f,"humidity":%.1f,"pressure":%.1f,"rain_flag":%s}`

3. **Liveness & Silence Heartbeat Threshold**:
   - Sensor Health Engine (`services/quality_control/sensor_health_engine.py:35`):
     ```python
     OFFLINE_THRESHOLD_SECONDS = 8  # Fast 8s live heartbeat timeout for immediate disconnection feedback
     ```
   - Dashboard Silence Evaluation (`apps/web/hardware_dashboard.html:782, 790, 796`):
     - Evaluates `(Date.now() - lastMqttPacketTime) <= 8000` to maintain `🟢 ESP32 LIVE CONNECTED`.
     - Switches to `🔴 ESP32 DISCONNECTED` when elapsed silence exceeds 8000 ms.

4. **Dual-Mode Ingestion & Local REST Endpoint**:
   - Local Ingest Diagnostic Endpoint (`apps/api/routers/ingest_router.py:289-323`):
     `GET /api/v1/ingest/sensors/diagnostic` returning `StationDiagnosticReport` with `station_liveness` (`LIVE_ACTIVE`, `PARTIAL_DEGRADED`, `OFFLINE`).
   - Dashboard Polling Arbitration (`apps/web/hardware_dashboard.html:780-808`):
     Suppresses REST polling updates while MQTT packets arrive within the 8s window; activates fallback polling only when MQTT stream is silent or disconnected.

5. **Client Library Assets**:
   - `apps/web/paho-mqtt.js` exists locally (size: 38,727 bytes) with fallback script loader (`apps/web/hardware_dashboard.html:856`):
     `<script src="/static/paho-mqtt.js" onerror="this.onerror=null;this.src='paho-mqtt.js';"></script>`.

---

## 2. Logic Chain

1. **Premise 1**: When the AirSense web dashboard is deployed publicly to static hosts such as Vercel or GitHub Pages, browsers enforce HTTPS Mixed Content restrictions. Standard TCP sockets (`1883`) and insecure WebSockets (`ws://`) will be blocked by modern browsers on HTTPS origins.
2. **Premise 2**: HiveMQ's public cloud broker exposes Secure WebSockets on port `8884` with path `/mqtt` (`wss://broker.hivemq.com:8884/mqtt`).
3. **Inference 1**: The client dashboard must dynamically check `window.location.protocol === 'https:'` and bind to `wss://broker.hivemq.com:8884/mqtt` over TLS, while allowing `ws://broker.hivemq.com:8000/mqtt` for local HTTP testing.
4. **Premise 3**: Multiple users and browsers worldwide will concurrently access the public dashboard. HiveMQ brokers evict existing connections if a new client connects with an identical Client ID.
5. **Inference 2**: Every dashboard instance must generate a cryptographically unique or pseudo-random Client ID (e.g. `airsense-web-${randomHex}-${timestamp}`) and connect with `cleanSession: true`.
6. **Premise 4**: The ESP32 station broadcasts packets every 5.0 seconds. If hardware is turned off or loses Wi-Fi, no TCP FIN or MQTT DISCONNECT is emitted.
7. **Inference 3**: Client-side reactive silence detection with an 8.0-second threshold ($1.6 \times 5\text{s}$) provides instantaneous, deterministic visual feedback of hardware disconnection (`🔴 ESP32 DISCONNECTED`) without polling lag.
8. **Premise 5**: On local workstations where the FastAPI server is running, MQTT WebSockets and REST diagnostic endpoints (`/api/v1/ingest/sensors/diagnostic`) may run simultaneously.
9. **Inference 4**: A priority arbitration filter in the dashboard ensures that live MQTT packets always take precedence, while REST polling runs as a transparent fallback if MQTT packets cease.

---

## 3. Caveats

1. **Public Broker Shared Namespace**: `broker.hivemq.com` is a public sandbox broker. Anyone can publish to unauthenticated topics. For enterprise production deployments, an authenticated broker (e.g. HiveMQ Cloud Dedicated Cluster, AWS IoT Core, or EMQX with mutual TLS/tokens) should be provisioned.
2. **QoS 0 Packet Drops on Unstable Wi-Fi**: QoS 0 delivery does not retransmit dropped UDP/TCP segments at the application layer. Occasional 1-packet drop can occur if campus Wi-Fi fluctuates; the 8-second silence window allows 1 packet drop before tripping disconnection, but consecutive dropped packets will trigger a brief offline badge until the next packet arrives.
3. **Paho MQTT vs MQTT.js in Bundled Environments**: Paho MQTT relies on `window.Paho` global namespace. In modern React / Vite frameworks, `npm install mqtt` is cleaner and easier to manage with ES modules and standard React hooks (`useEffect`).

---

## 4. Conclusion

The MQTT WebSockets protocol and Dual-Mode ingestion specification is complete, robust, and verified against all reference implementations in the AirSense-v2 repository.

Key Architectural Specs:
- **Broker**: `broker.hivemq.com`
- **WSS Port (HTTPS/Vercel/GitHub Pages)**: `8884` (Path: `/mqtt`)
- **WS Port (HTTP/Localhost)**: `8000` (Path: `/mqtt`)
- **Native TCP Port (ESP32 / Python)**: `1883`
- **Topic Subscriptions**: `airsense/karachi/bic_roof/telemetry`, `airsense/#`
- **Silence Heartbeat Window**: $8.0\text{ seconds}$
- **Primary Transport**: Direct Browser Cloud MQTT WebSockets (Zero laptop dependency)
- **Secondary Fallback**: Local REST API Polling (`/api/v1/ingest/sensors/diagnostic`)
- **Normalized Schema**: Support for `pm2_5`/`pm25`, `temperature`/`temperature_c`, `humidity`/`humidity_pct`, `pressure`/`pressure_hpa`, `rain_flag`.

Detailed feature matrix, edge cases, state machine, and data dictionary have been written to `.agents/spec_miner_survey_1/analysis.md`.

---

## 5. Verification Method

To independently verify the specifications documented in this report:

1. **Verify Sensor Health Engine 8-Second Threshold**:
   Inspect `services/quality_control/sensor_health_engine.py` line 35 to confirm `OFFLINE_THRESHOLD_SECONDS = 8`.
   Run unit tests:
   ```powershell
   pytest tests/unit/test_sensor_health.py -v
   ```

2. **Verify Hardware Diagnostic & Status API Endpoints**:
   Run hardware and ingest unit tests:
   ```powershell
   pytest tests/unit/test_hardware_and_theme_endpoints.py tests/integration/test_ingestion_api.py -v
   ```

3. **Verify ESP32 Firmware Publication Topic & Payload**:
   Inspect `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` lines 32-34 and 380-384.

4. **Verify Frontend WebSockets Logic & Dual-Mode Fallback**:
   Inspect `apps/web/hardware_dashboard.html` lines 664-856 to verify `initCloudMQTT()`, Paho WebSocket connection to ports 8884/8000, topic subscriptions, `applyLiveTelemetryPacket()`, and `fetchHardwareDiagnostics()` 8-second arbitration.

5. **Verify Full E2E Test Suite**:
   Run the comprehensive E2E test suite:
   ```powershell
   pytest tests/e2e/test_dual_dashboards_e2e.py -v
   ```

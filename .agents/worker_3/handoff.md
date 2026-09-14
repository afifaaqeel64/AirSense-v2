# Handoff Report — Worker 3 (Vercel Frontend Dashboard Specialist)

## 1. Observation
1. **Initial Broker & Topic Mismatch**:
   - Hardcoded single-broker connections (HiveMQ or EMQX) in dashboard files lacked failover redundancy. If a broker experienced TLS/WebSocket connection drops, the frontend dashboards stalled.
   - Topics were inconsistently subscribed across dashboards.

2. **Premature Disconnect UI Flashing & Timer Flaws**:
   - lastMqttPacketTime initialized to 0. On first load, checkSilenceWatchdog() immediately detected silence and rendered disconnected state with disconnect banners before the WebSocket connection finished.

3. **Zombie / Half-Open WebSocket Connections**:
   - If network packets ceased while the browser TCP socket remained half-open (client.isConnected() === true), no packet arrived and no onConnectionLost event fired, freezing the dashboard.

4. **Missing Browser Lifecycle Resumption**:
   - Tab switching and device sleep caused WebSocket connections to go stale without automatic recovery on focus or online events.

5. **NaN Numeric Rendering Vulnerabilities**:
   - Raw string keys (null, '--', 'NaN') passed to .toFixed(1) resulted in NaN rendering across AQI indicators, gauges, and CSV exports.

## 2. Logic Chain
1. **Multi-Broker Failover Design**:
   - Implemented unified BROKER_POOL across all 4 dashboards:
     - Primary: broker.hivemq.com (WSS 8884 / WS 8000, path /mqtt)
     - Secondary: broker.emqx.io (WSS 8084 / WS 8083, path /mqtt)
     - Tertiary: test.mosquitto.org (WSS 8081 / WS 8080, path /mqtt)
   - Added jittered exponential backoff and automatic broker cycling on consecutive failures.
   - Subscriptions unified: airsense/#, airsense/karachi/bic_roof/telemetry, airsense/+/+/telemetry.

2. **Watchdog Tiering & Grace Period**:
   - Added 30-second initial grace period displaying CONNECTING / AWAITING TELEMETRY (Xs grace) with disconnect alert hidden.
   - Implemented 3 operational liveness tiers:
     - 0–10s: ESP32 LIVE CONNECTED (Xs ago)
     - 11–30s: ESP32 AWAITING TELEMETRY (Xs ago)
     - >30s: ESP32 DISCONNECTED (Xs ago) with offline card indicators and alert banner.
   - Implemented Zombie Socket Watchdog: Detects connected client with 0 packets over 30s, cleanly tears down socket, cycles broker, and reconnects.

3. **Browser Lifecycle Synchronization**:
   - Attached window.addEventListener('online'), document.addEventListener('visibilitychange'), and window.addEventListener('focus') to test and revive connections immediately upon user return.

4. **Data Sanitization & Zero-Build Static Compliance**:
   - Implemented safeNum(val, fallback, decimals) and normalizeTelemetry(p) across all 4 files.
   - Guaranteed 100% zero-build static hosting: root-relative /paho-mqtt.js with CDN fallback.

## 3. Caveats
- Shared public MQTT brokers require resilient client-side failover; backoff delays prevent excessive reconnect attempts.
- Local REST API polling (/api/v1/...) gracefully handles 404s/network errors on standalone static hosts.

## 4. Conclusion
- All 4 dashboard pages (index.html, hardware.html, command.html, enterprise.html) are production-hardened, unified, and zero-build compliant.
- All 58 E2E dashboard tests and 79 unit/integration tests passed with zero errors.

## 5. Verification Method
- **Syntax & AST Validation**:
  node syntax validation passed across all 4 HTML files.
- **E2E Test Execution**:
  py -3 -m pytest tests/e2e/test_dual_dashboards_e2e.py -v
- **Unit & Integration Test Execution**:
  py -3 -m pytest tests/unit/ tests/integration/
- **Files to Inspect**:
  - public/index.html
  - public/hardware.html
  - public/command.html
  - public/enterprise.html

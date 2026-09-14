## 2026-09-01T16:31:54Z
You are Worker 1 for AirSense-v2.
Working directory: c:\Users\HP\AirSense-v2\.agents\worker_impl_1
Original request path: c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md
Scope document: c:\Users\HP\AirSense-v2\PROJECT.md

Reference Analysis & Handoffs:
- c:\Users\HP\AirSense-v2\.agents\explorer_impl_1\analysis.md
- C:\Users\HP\.gemini\antigravity\brain\eb7d52d3-24b5-407b-8cbc-442732dd6443\handoff.md
- c:\Users\HP\AirSense-v2\.agents\explorer_impl_3\analysis.md
- c:\Users\HP\AirSense-v2\TEST_READY.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You have exclusive write ownership of:
- public/index.html
- public/opensource.html
- public/paho-mqtt.js
- apps/web/hardware_dashboard.html
- apps/web/opensource_dashboard.html
- vercel.json
- .github/workflows/deploy.yml

Your Tasks:
1. Implement and refine public/index.html and apps/web/hardware_dashboard.html:
   - Ensure <script src="paho-mqtt.js"></script> loads cleanly before initialization.
   - Configure initCloudMQTT() to connect to broker.hivemq.com (WSS port 8884 on HTTPS, WS port 8000 on HTTP), subscribing to airsense/karachi/bic_roof/telemetry and airsense/# with random client ID and cleanSession: true.
   - Implement complete telemetry parsing in applyLiveTelemetryPacket for pm1, pm2_5/pm25, pm10, temperature/temperature_c, humidity/humidity_pct, pressure/pressure_hpa, rain_flag, sequence_number, timestamp_epoch.
   - Implement autonomous 8.0s silence watchdog (setInterval at 500ms checking Date.now() - lastMqttPacketTime > 8000) switching reactive UI between 🟢 ESP32 LIVE CONNECTED and 🔴 ESP32 DISCONNECTED.
   - Display disconnect banner when offline with link to opensource.html / /opensource.
   - Priority arbitration: suppress REST polling table overwrites while MQTT stream is actively flowing.
   - Ensure all links and script tags are relative (e.g. opensource.html, paho-mqtt.js) for GitHub Pages subpath compatibility.
2. Ensure public/opensource.html is synchronized with apps/web/opensource_dashboard.html and has relative links.
3. Ensure vercel.json is configured with outputDirectory: "public", cleanUrls: true, and CSP headers authorizing wss://broker.hivemq.com:8884 and Open-Meteo APIs.
4. Ensure .github/workflows/deploy.yml is created for GitHub Actions Pages deployment targeting ./public.
5. Run full test verification using pytest:
   py -3.13 -m pytest tests/e2e/test_dual_dashboards_e2e.py tests/unit/test_challenger_hardware_diagnostics.py -v
6. Document changes, test execution commands, and results in c:\Users\HP\AirSense-v2\.agents\worker_impl_1\handoff.md.
7. Send a concise completion message back with the handoff path.

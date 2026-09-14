## 2026-09-01T16:14:44Z
Task:
You are Explorer Impl 1 (Frontend & WebSocket Specialist) for AirSense-v2.
Working directory: c:\Users\HP\AirSense-v2\.agents\explorer_impl_1
Original request path: c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md
Scope document: c:\Users\HP\AirSense-v2\PROJECT.md

Your Task:
1. Read c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md and c:\Users\HP\AirSense-v2\PROJECT.md.
2. Inspect public/index.html and apps/web/hardware_dashboard.html.
3. Formulate the exact implementation plan for the Worker:
   - Fix Paho MQTT script loading order & watchdog retry loop (ensure Paho is defined before init, retry if needed).
   - Dynamic protocol selection: wss://broker.hivemq.com:8884/mqtt for HTTPS, ws://broker.hivemq.com:8000/mqtt for HTTP.
   - Unique Client ID generation per session.
   - Ingest & parse all telemetry fields: pm1, pm2_5, pm10, temperature, humidity, pressure, rain_flag, sequence_number, timestamp_epoch.
   - Smooth zero-flash DOM update for all sensor cards and 10-column table.
4. Write your implementation recommendations to c:\Users\HP\AirSense-v2\.agents\explorer_impl_1\analysis.md and c:\Users\HP\AirSense-v2\.agents\explorer_impl_1\handoff.md.
5. Send a concise completion message back with the handoff path.

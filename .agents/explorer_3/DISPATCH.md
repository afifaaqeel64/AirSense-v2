## 2026-09-02T09:49:06Z
User Request / Dispatch:
Investigate the web dashboard codebase (HTML/JS/CSS, React/Next.js, Vercel config, etc.) in c:/Users/HP/AirSense-v2.
Analyze:
1. What framework and build setup is used (static HTML/JS, Next.js, Vite, etc.) and what Vercel configuration exists (vercel.json, env vars)?
2. How does the dashboard connect to live telemetry (MQTT over WebSockets WSS/WS, REST polling, Server-Sent Events, etc.)?
3. What broker URL, WebSocket port, and topic(s) does the dashboard subscribe to?
4. What causes the dashboard to go permanently offline or show "Offline" status?
5. What reconnection logic exists for dropped WebSockets / network blips? (e.g. exponential backoff, reconnect timers, ping/keepalive).
6. How does the dashboard parse and render incoming telemetry packets (AQI, PM2.5, CO2, Temp, Humidity, Timestamp)? Does malformed data or unexpected JSON schema break UI?
7. Recommend exact fixes to make the dashboard 100% resilient with rock-solid auto-reconnect and clear online/offline telemetry status.

Write a detailed handoff report to: c:/Users/HP/AirSense-v2/.agents/explorer_3/analysis.md and c:/Users/HP/AirSense-v2/.agents/explorer_3/handoff.md.
When finished, send a message to parent with your summary.

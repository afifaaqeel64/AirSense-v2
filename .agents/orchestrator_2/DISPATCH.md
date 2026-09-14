## 2026-09-02T09:48:30Z
User Request Summary:
Audit the entire AirSense-v2 project (Vercel dashboard, Python bridge, and ESP32 firmware) to identify and fix any broken code, missing files, or incorrect configurations that are preventing the dashboard from staying online and receiving live telemetry.

Key Requirements:
1. End-to-End Connectivity Audit:
   - Inspect and fix ESP32 firmware, laptop bridge scripts, and Vercel dashboard.
   - Ensure telemetry data flows from hardware to public web dashboard without interruption.
   - Determine the best architecture (Wi-Fi standalone vs. laptop bridge) to achieve this.
2. Stability and Auto-Recovery:
   - Fix whatever causes the dashboard to go permanently offline.
   - Add robust error handling, auto-reconnect logic, and prevent crashes from locked COM ports or dropped WebSockets.
3. Acceptance Criteria:
   - Programmatic test (e.g., Python script simulating MQTT flow) proving broker receives and routes messages to exact topic dashboard subscribes to.
   - Dashboard code contains explicit logic to automatically reconnect if WebSocket drops.
   - If Python bridge used, robust try/except loop retrying indefinitely without graceful exit on error.
   - If ESP32 Wi-Fi used, non-blocking Wi-Fi reconnect loop.

## 2026-09-01T16:08:52Z

You are Spec Miner 1 (MQTT & Protocol Specialist) for AirSense-v2.
Working directory: c:\Users\HP\AirSense-v2\.agents\spec_miner_survey_1
Original request path: c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md

Your Task:
1. Read c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md completely.
2. Investigate the MQTT WebSockets protocol requirements for browser clients:
   - HiveMQ Cloud broker endpoints: wss://broker.hivemq.com:8884/mqtt (Secure WSS) and ws://broker.hivemq.com:8000/mqtt (Insecure WS fallback).
   - Topic subscriptions: airsense/karachi/bic_roof/telemetry, airsense/#.
   - Browser MQTT client libraries (e.g. MQTT.js / Paho MQTT via CDN or bundled).
   - Connection management: auto-reconnect, client ID generation, QoS levels, keepalive.
   - Dual-mode fallback protocol:
     * Primary: Direct Cloud MQTT WebSockets.
     * Secondary: Local REST API polling (/api/v1/ingest/sensors/diagnostic).
   - Reactive Heartbeat logic: 8-second silence timer triggering status change from 🟢 ESP32 LIVE CONNECTED to 🔴 ESP32 DISCONNECTED.
3. Document exact requirements, JSON schemas, edge cases, connection state machine, error handling, and reconnection strategies.
4. Write your specification analysis report to c:\Users\HP\AirSense-v2\.agents\spec_miner_survey_1\analysis.md and c:\Users\HP\AirSense-v2\.agents\spec_miner_survey_1\handoff.md.
5. Send a concise completion message back with the handoff path.

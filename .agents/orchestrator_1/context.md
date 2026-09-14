# Context Log

## 2026-09-01T16:08:20Z - Initialization
- Orchestrator initialized for AirSense-v2.
- User request: Deploy 24/7 standalone public AirSense hardware dashboard to Vercel / GitHub Pages connecting directly to Cloud MQTT WebSockets (broker.hivemq.com) subscribing to `airsense/karachi/bic_roof/telemetry` (or `airsense/#`).
- Dual-mode support: Cloud MQTT WebSockets primary, local REST API fallback.
- Reactive heartbeat indicator (8s timeout).
- Target zero laptop dependency.

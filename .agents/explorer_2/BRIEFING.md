# BRIEFING — 2026-09-02T09:56:40Z

## Mission
Deep read-only investigation of Python bridge scripts, serial communication, MQTT broker configuration, topic/payload alignment, error resilience, and 24/7 daemon architecture.

## 🔒 My Identity
- Archetype: Explorer
- Roles: Python Bridge & MQTT Specialist
- Working directory: c:/Users/HP/AirSense-v2/.agents/explorer_2
- Original parent: 9be8d85f-f111-4a0e-bd21-983f3317c697
- Milestone: M1 - Deep Investigation

## 🔒 Key Constraints
- Read-only investigation — do NOT implement changes directly into codebase yet
- Follow 5-Component Handoff format
- Verify findings with exact line numbers and paths
- Produce analysis.md and handoff.md, communicate back via send_message to parent

## Current Parent
- Conversation ID: 9be8d85f-f111-4a0e-bd21-983f3317c697
- Updated: 2026-09-02T09:49:35Z

## Investigation State
- **Explored paths**:
  - `scripts/airsense_serial_live_bridge.py`
  - `scripts/airsense_serial_forwarder.py`
  - `scripts/airsense_mqtt_live_forwarder.py`
  - `scripts/airsense_live_hardware_feeder.py`
  - `scripts/stop_serial_bridge.py`
  - `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`
  - `apps/api/routers/ingest_router.py`
  - `apps/api/routers/hardware_router.py`
  - `public/hardware.html`, `public/index.html`
  - `apps/web/hardware_dashboard.html`, `apps/web/index.html`
  - `requirements.txt`, batch runner scripts
- **Key findings**:
  1. Critical split-brain broker mismatch (`broker.emqx.io` used by ESP32/serial bridge vs `broker.hivemq.com` used by Vercel dashboard and forwarder).
  2. Hardcoded `COM7` in batch scripts and single-pass port discovery in serial bridge causing failure on port re-enumeration.
  3. Missing `pyserial` and `paho-mqtt` in `requirements.txt`.
  4. Paho-MQTT 2.0 API deprecation warnings in `airsense_serial_live_bridge.py`.
  5. Fatal exit on startup failure in `airsense_mqtt_live_forwarder.py` and `airsense_serial_forwarder.py`.
- **Unexplored areas**: None for Python Bridge & MQTT scope.

## Key Decisions Made
- Completed empirical socket probe tests verifying both HiveMQ (TCP 1883, WSS 8884) and EMQX (TCP 1883, WSS 8084).
- Recommended multi-broker dual-publishing architecture and dynamic hot-plug COM port scanner.
- Produced detailed `analysis.md` and `handoff.md`.

## Artifact Index
- `c:/Users/HP/AirSense-v2/.agents/explorer_2/analysis.md` — Detailed technical analysis report
- `c:/Users/HP/AirSense-v2/.agents/explorer_2/handoff.md` — 5-component handoff report
- `c:/Users/HP/AirSense-v2/.agents/explorer_2/probe_wss.py` — Empirical WSS test probe script

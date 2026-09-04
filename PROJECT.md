# Project: AirSense-v2 End-to-End Resilience & 24/7 Telemetry Pipeline

## Architecture
AirSense-v2 is an industrial/academic IoT telemetry platform collecting particulate (PMS7003), environmental (BME280), and gas metrics via an ESP32 hardware node, routing packets to cloud MQTT brokers (`broker.hivemq.com` & `broker.emqx.io`), and visualizing live air quality in a zero-build static web dashboard hosted on Vercel and GitHub Pages.

```
+-------------------------------------------------------------+
|                     ESP32 Hardware Node                     |
|  - Physical UART (PMS7003 PM1.0/2.5/10)                     |
|  - Physical I2C (BME280 Temp/Humidity/Pressure)             |
|  - Firmware outputs structured JSON over Serial & Wi-Fi     |
+------------------------------+------------------------------+
                               |
            +------------------+------------------+
            | (USB Serial UART)                   | (Direct Wi-Fi)
            v                                     v
+-----------------------------+       +-----------------------------+
| Python Serial Bridge Daemon |       | ESP32 Standalone MQTT Pub   |
| - Dynamic USB/COM Scanner   |       | - Non-blocking Wi-Fi loop   |
| - Infinite Auto-Reconnect   |       | - Fast broker failover      |
| - Dual-Broker MQTT Pub      |       | - Direct TCP 1883 Pub       |
+--------------+--------------+       +--------------+--------------+
               |                                     |
               +------------------+------------------+
                                  |
                                  v
+-------------------------------------------------------------+
|                Cloud MQTT Broker Infrastructure             |
|  Primary: broker.hivemq.com (TCP: 1883, WSS: 8884 /mqtt)    |
|  Secondary: broker.emqx.io (TCP: 1883, WSS: 8084 /mqtt)     |
|  Topic: airsense/karachi/bic_roof/telemetry & airsense/#    |
+------------------------------+------------------------------+
                               |
                               v (WSS over WebSockets)
+-------------------------------------------------------------+
|                  Vercel Frontend Dashboard                  |
|  - Multi-Broker Failover Engine (HiveMQ <-> EMQX)           |
|  - Zombie WebSocket Watchdog & Reconnection Engine          |
|  - Lifecycle Event Listeners ('online', 'visibilitychange') |
|  - Safe Schema Normalizer (Zero NaN / Zero Crash)           |
|  - Zero-build static SPA (index.html, hardware.html, etc.)  |
+-------------------------------------------------------------+
```

## Feature Inventory
| # | Feature | Description | Milestone | Status | Source |
|---|---|---|---|---|---|
| 1 | Multi-Broker Synchronization | Unify & dual-publish to HiveMQ and EMQX to resolve split-brain disconnection | M1 | DONE | Survey |
| 2 | Python Bridge Resilient Daemon | Implement dynamic COM scanning, infinite retry loop, Paho v2 API, and dual-publish | M2 | DONE | Survey |
| 3 | Requirements & Dependencies | Add `pyserial>=3.5` and `paho-mqtt>=2.0.0` to requirements.txt | M1 | DONE | Survey |
| 4 | ESP32 Firmware Telemetry Hardening | Add Serial JSON output, non-blocking Wi-Fi reconnect, and explicit sensor error/null reporting | M3 | DONE | Survey |
| 5 | Vercel Dashboard Multi-Broker Failover | Implement active broker failover across all HTML dashboard pages (`index.html`, `hardware.html`, etc.) | M4 | DONE | Survey |
| 6 | Dashboard Watchdog & Zombie Socket Recycling | Graceful connection states (`🟡 CONNECTING`), exponential backoff, and zombie socket recycling | M4 | DONE | Survey |
| 7 | UI Schema Normalizer & NaN Sanitization | Safe value parsers preventing `NaN` leakage in UI cards, gauges, and tables | M4 | DONE | Survey |
| 8 | Programmatic E2E MQTT Test Harness | Python test suite verifying broker message routing, topic exact matches, and payload delivery | M0 | DONE | User Req / Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | E2E Testing Suite & MQTT Simulators | Create programmatic verification tests simulating end-to-end MQTT telemetry, broker routing, and socket reconnects | none | DONE |
| M1 | Dependencies & MQTT Core Unification | Update `requirements.txt` and standardize MQTT connection configs | none | DONE |
| M2 | Python Bridge Resilient Daemon | Rewrite/harden `airsense_serial_live_bridge.py`, `airsense_mqtt_live_forwarder.py`, and `airsense_serial_forwarder.py` with dynamic COM discovery, Paho v2, infinite reconnects | M1 | DONE |
| M3 | ESP32 Firmware Telemetry Hardening | Update `airsense_esp32_firmware.ino` with Serial JSON output, explicit sensor error status, non-blocking Wi-Fi loop | M1 | DONE |
| M4 | Vercel Dashboard Auto-Reconnect & Failover | Update `public/index.html`, `public/hardware.html`, `public/command.html`, `public/enterprise.html` with failover engine, watchdog, safe parsing | M1, M2 | DONE |
| M5 | Final E2E Validation & Gate Verification | Execute 100% test suite, review, challenge, and forensic integrity audit | M0, M2, M3, M4 | DONE |

## Interface Contracts

### Telemetry Packet JSON Schema (MQTT Topic: `airsense/karachi/bic_roof/telemetry`)
```json
{
  "device_id": "AIRSENSE-NODE-01",
  "node_id": "AIRSENSE-NODE-01",
  "location": "BIC_ROOF_KARACHI",
  "sequence_number": 1234,
  "timestamp_epoch": 1725270000,
  "pm1_0": 6.5,
  "pm2_5": 8.2,
  "pm10": 10.1,
  "temperature_c": 28.5,
  "humidity_pct": 62.0,
  "pressure_hpa": 1013.2,
  "gas_resistance_kohm": 45.2,
  "rain_flag": false,
  "sensor_health": {
    "pms7003": "OK",
    "bme280": "OK",
    "rain": "OK"
  },
  "transmission_mode": "SERIAL_BRIDGE"
}
```

### Serial Output Contract from ESP32 to Python Bridge
- JSON lines prefixed by `[JSON_TELEMETRY] ` or raw valid JSON string `{...}` containing `"AIRSENSE-NODE"`.
- Human readable logs prefixed by `[LOG]` or `[DEBUG]` for serial terminal debugging.

### MQTT Broker Endpoints
- **HiveMQ Public Broker**:
  - TCP Port: `1883`
  - WebSockets (WSS): `broker.hivemq.com:8884/mqtt`
- **EMQX Public Broker**:
  - TCP Port: `1883`
  - WebSockets (WSS): `broker.emqx.io:8084/mqtt`

## Code Layout
- `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` — ESP32 physical deployment firmware
- `scripts/airsense_serial_live_bridge.py` — Primary Python serial-to-MQTT bridge daemon
- `scripts/airsense_mqtt_live_forwarder.py` — MQTT live forwarder service
- `scripts/airsense_serial_forwarder.py` — Fallback serial forwarder
- `requirements.txt` — Project python dependencies
- `public/index.html` — Main Hardware Hub & telemetry dashboard
- `public/hardware.html` — Hardware diagnostics & node monitor
- `public/command.html` — Command & control console
- `public/enterprise.html` — Enterprise analytics view
- `tests/` — Automated test suite and simulators

# AirSense Pakistan: Comprehensive Python Bridge & MQTT Deep Investigation Report

**Author**: Explorer 2 (Python Bridge & MQTT Specialist)  
**Date**: September 2, 2026  
**Scope**: Full codebase audit of Python bridge scripts, serial communication, MQTT broker configuration, topic/payload alignment, error resilience, and 24/7 daemon architecture.

---

## 1. Executive Summary

A comprehensive investigation of the Python bridge scripts, MQTT messaging pipelines, hardware serial communication, and backend ingestion services within `c:/Users/HP/AirSense-v2` revealed an operational architecture with strong foundational components but **critical split-brain broker mismatches, static COM port locking issues, and missing top-level package dependencies**.

### Key Findings:
1. **Critical Broker Split-Brain**:
   - **Producers**: The ESP32 firmware (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino:32`) and the primary serial bridge (`scripts/airsense_serial_live_bridge.py:69`) publish exclusively to `broker.emqx.io:1883`.
   - **Consumers**: The primary web dashboards (`public/hardware.html:880`, `apps/web/hardware_dashboard.html:880`, `apps/web/index.html:880`) and the MQTT forwarder (`scripts/airsense_mqtt_live_forwarder.py:16`) subscribe exclusively to `broker.hivemq.com:8884/1883`.
   - **Direct Impact**: The standalone cloud dashboard deployed on Vercel / GitHub Pages NEVER receives packets directly from the ESP32 Wi-Fi broadcast or the Python serial bridge over MQTT. Packets only reach HiveMQ if the local FastAPI backend is active and relays them.
2. **Stale / Hardcoded COM Port Locking**:
   - Batch launchers (`start_serial_bridge.bat:10`, `run_bridge_daemon.bat:3`, `run_airsense_all_in_one.bat:13`) hardcode `COM7`, bypassing dynamic port autodetection.
   - If the ESP32 is plugged into another port (e.g. `COM3`, `COM4`, `COM8`, `COM11`) or re-enumerates upon USB re-plug, the bridge remains stuck in an infinite retry loop on the wrong port.
3. **Missing Critical Dependencies in `requirements.txt`**:
   - Neither `pyserial` nor `paho-mqtt` is listed in `c:/Users/HP/AirSense-v2/requirements.txt`, leading to immediate import failure in fresh environments.
4. **Paho-MQTT 2.0 API Deprecation Flaw**:
   - `airsense_serial_live_bridge.py:68` invokes `mqtt.Client(client_id=...)` without passing `CallbackAPIVersion.VERSION2`, triggering deprecation warnings or compatibility failures on `paho-mqtt>=2.0.0`.
5. **Incomplete Error Handling in Forwarders**:
   - `scripts/airsense_mqtt_live_forwarder.py:101-108` exits immediately if the initial broker connection fails during startup.
   - `scripts/airsense_serial_forwarder.py:33-37` exits immediately if `COM11` cannot be opened on boot.

---

## 2. Catalog of Python Bridge Scripts & Backend Services

| Script / Module | Purpose | Ingestion Source | Output Destination | Broker / Target | Status & Health |
|---|---|---|---|---|---|
| `scripts/airsense_serial_live_bridge.py` | Primary live serial bridge & MQTT streamer | ESP32 USB Serial (Regex ASCII parser) | Local REST API + Cloud MQTT | REST: `127.0.0.1:8000`<br>MQTT: `broker.emqx.io:1883` | Functional but has Broker Mismatch (`broker.emqx.io` instead of `broker.hivemq.com`) and static port binding |
| `scripts/airsense_serial_forwarder.py` | Legacy Serial-to-REST JSON forwarder | ESP32 USB Serial (Strict JSON line parser) | Local REST API | REST: `127.0.0.1:8000` | Deprecated/Flawed: Hardcodes `COM11`, no MQTT support, exits on start failure |
| `scripts/airsense_mqtt_live_forwarder.py` | Campus-to-Home MQTT subscriber & REST forwarder | Cloud MQTT Broker (`airsense/#`) | Local REST API | Sub: `broker.hivemq.com:1883`<br>REST: `127.0.0.1:8000` | Flawed: Listens on HiveMQ (misses EMQX packets), exits on initial network failure |
| `scripts/airsense_live_hardware_feeder.py` | Synthetic live hardware streaming simulator | Generated random telemetry readings | Local REST API | REST: `127.0.0.1:8000` | Functional test utility |
| `scripts/stop_serial_bridge.py` | Process supervisor / cleanup utility | PID file & Windows WMIC process tree | OS `taskkill` | Local OS | Functional |
| `apps/api/routers/ingest_router.py` | FastAPI Ingestion & Dual Broadcast Router | HTTP POST (`/api/v1/ingest/reading`) | Database + Cloud MQTT Broadcast | SQLite/PostgreSQL + `broker.hivemq.com:1883` | Functional; relays to HiveMQ via `paho.mqtt.publish.single` |

---

## 3. Detailed COM Port Handling & Hot-Plug Behavior

### 3.1 Port Autodetection Mechanism
In `scripts/airsense_serial_live_bridge.py:21-30`:
```python
def find_esp32_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = p.description.lower()
        if "cp210" in desc or "ch340" in desc or "uart" in desc or "serial" in desc:
            return p.device
    if ports:
        return ports[0].device
    return "COM7"
```

### 3.2 Key COM Port Failure Modes Identified:
1. **CLI Argument Override Locks Port**:
   - `run_bridge(port_name=None)` uses `port = port_name or find_esp32_port()`.
   - `run_bridge_daemon.bat`, `start_serial_bridge.bat`, and `run_airsense_all_in_one.bat` execute `py -u scripts\airsense_serial_live_bridge.py COM7`.
   - Result: `port_name` is always `"COM7"`, so `find_esp32_port()` is never called. If the ESP32 is attached to `COM3`, `COM4`, or `COM8`, the bridge fails indefinitely.
2. **Single-Shot Port Evaluation**:
   - `port` is resolved once prior to entering `while True:`.
   - If the user unplugs the ESP32 and reconnects it to a different USB port, the outer loop continues retrying the old port string and never scans for the new device.
3. **Port Busy / Arduino IDE Serial Monitor Conflict**:
   - Handled cleanly in `airsense_serial_live_bridge.py:140-146`: catches `serial.SerialException`, checks for `"PermissionError"` or `"Access is denied"`, outputs an advisory message to close Arduino IDE, and sleeps 2 seconds before retrying.
4. **Physical USB Unplug / Power Drop**:
   - `ser.readline()` raises `serial.SerialException` or `OSError`.
   - The inner loop breaks to the outer exception handler, `finally:` safely invokes `ser.close()`, and the outer loop sleeps 2s before retrying.

---

## 4. MQTT Broker Topology, Protocol, Topics & Schemas

### 4.1 Topology & Broker Matrix

| Node | Broker Host | Port | Transport | Client ID Pattern | Published / Subscribed Topic | QoS |
|---|---|---|---|---|---|---|
| ESP32 Firmware | `broker.emqx.io` | 1883 | TCP (Raw Socket) | `as-esp32-<EFuseMAC>` | Pub: `airsense/karachi/bic_roof/telemetry` | 0 |
| Serial Live Bridge | `broker.emqx.io` | 1883 | TCP (Paho) | `airsense-bridge-<epoch>` | Pub: `airsense/karachi/bic_roof/telemetry` | 0 |
| FastAPI Ingest Router | `broker.hivemq.com` | 1883 | TCP (Paho single) | Ephemeral | Pub: `airsense/karachi/bic_roof/telemetry` | 0 |
| MQTT Live Forwarder | `broker.hivemq.com` | 1883 | TCP (Paho) | `airsense-home-receiver-<epoch>` | Sub: `airsense/#` | 0 |
| `public/hardware.html` | `broker.hivemq.com` | 8884 (WSS) / 8000 (WS) | WebSocket `/mqtt` | `airsense-web-<random>` | Sub: `airsense/#`, `airsense/karachi/bic_roof/telemetry` | 0 |
| `public/index.html` | `broker.emqx.io` | 8084 (WSS) / 8083 (WS) | WebSocket `/mqtt` | `airsense-web-<random>` | Sub: `airsense/#`, `airsense/karachi/bic_roof/telemetry` | 0 |
| `apps/web/hardware_dashboard.html` | `broker.hivemq.com` | 8884 (WSS) / 8000 (WS) | WebSocket `/mqtt` | `airsense-web-<random>` | Sub: `airsense/#`, `airsense/karachi/bic_roof/telemetry` | 0 |
| `apps/web/index.html` | `broker.hivemq.com` | 8884 (WSS) / 8000 (WS) | WebSocket `/mqtt` | `airsense-web-<random>` | Sub: `airsense/#`, `airsense/karachi/bic_roof/telemetry` | 0 |

### 4.2 Empirical Network Verification
Empirical tests performed with active TCP and WSS sockets confirmed:
- `broker.hivemq.com:1883` (TCP) is active and responsive.
- `broker.hivemq.com:8884` (WSS with TLS) is fully operational with low latency.
- `broker.emqx.io:1883` (TCP) is active and responsive.
- `broker.emqx.io:8084` (WSS with TLS) and `8083` (WS) are fully operational.

### 4.3 Payload Compatibility Analysis
The payload produced by the ESP32 firmware and the Python serial bridge conforms to:
```json
{
  "schema_version": "1.0",
  "device_uid": "AIRSENSE-NODE-KHI-01",
  "station_code": "BIC-KHI-ROOF-01",
  "campus_code": "KARACHI",
  "firmware_version": "v3.5.0-HARDWARE-SERIAL",
  "sequence_number": 12,
  "timestamp_epoch": 1788342831,
  "pm1": 7.0,
  "pm2_5": 9.0,
  "pm10": 10.0,
  "temperature": 29.5,
  "humidity": 65.0,
  "pressure": 1012.0,
  "rain_flag": false
}
```
All frontend dashboards (`applyLiveTelemetryPacket(p)`) support both primary and aliased parameter names (`pm2_5` / `pm25`, `temperature` / `temperature_c`, `humidity` / `humidity_pct`, `pressure` / `pressure_hpa`). Schema alignment is 100% compatible.

---

## 5. Process Lifecycle, Error Handling & 24/7 Daemon Health

### 5.1 Daemon & Watchdog Review
- **`run_bridge_daemon.bat`**:
  - Implements a basic loop supervisor (`:loop ... goto loop`).
  - Resilient against unhandled process crashes, but locks the port to `COM7`.
- **`run_airsense_all_in_one.bat`**:
  - Spawns background tasks via `cmd /c` without process health monitoring or auto-restart.

### 5.2 Failure & Recovery Matrix

| Scenario | `airsense_serial_live_bridge.py` | `airsense_mqtt_live_forwarder.py` | `airsense_serial_forwarder.py` |
|---|---|---|---|
| Serial cable unplugged during stream | Catches `SerialException`, closes handle, sleeps 2s, retries | N/A | Infinite loop with dead handle |
| COM port locked by Arduino IDE | Detects `PermissionError`, advises user, retries every 2s | N/A | Immediate script crash / exit |
| Device assigned new COM port on re-plug | Fails indefinitely (stale port) | N/A | Fails indefinitely (hardcoded COM11) |
| Local FastAPI server offline / HTTP 500 | Suppresses error silently, keeps streaming to MQTT | Drops packet, continues loop | Catches error, continues loop |
| MQTT broker network timeout | Catches error, retries publish on next reading | **Exits completely on startup connect failure** | N/A |

---

## 6. Comprehensive Bug & Vulnerability Registry

| ID | Severity | Component | Location | Description & Impact |
|---|---|---|---|---|
| **BUG-01** | **CRITICAL** | MQTT / Architecture | `airsense_esp32_firmware.ino:32`, `airsense_serial_live_bridge.py:69`, `public/hardware.html:880` | **Broker Split-Brain**: Firmware and bridge publish to `broker.emqx.io`, while web dashboard and forwarder subscribe to `broker.hivemq.com`. 24/7 cloud telemetry fails. |
| **BUG-02** | **HIGH** | Dependencies | `requirements.txt` | Missing `pyserial>=3.5` and `paho-mqtt>=2.0.0` in root requirements file. |
| **BUG-03** | **HIGH** | Serial Bridge | `airsense_serial_live_bridge.py:86`, `.bat` files | Hardcoded `COM7` in batch scripts and single-pass port autodetection prevents recovery when port changes. |
| **BUG-04** | **MEDIUM** | Serial Bridge | `airsense_serial_live_bridge.py:68` | `mqtt.Client()` initialized without `CallbackAPIVersion.VERSION2`, triggering deprecation warnings under `paho-mqtt>=2.0.0`. |
| **BUG-05** | **MEDIUM** | MQTT Forwarder | `airsense_mqtt_live_forwarder.py:101-108` | `client.connect()` not enclosed in a retry loop; exits on startup network glitch. |
| **BUG-06** | **LOW** | Serial Forwarder | `airsense_serial_forwarder.py:33-37` | Immediate process exit on port open error; dead loop on serial disconnect. |

---

## 7. Recommended Production Architecture & Fixes

### 7.1 Multi-Broker Dual-Publishing Engine
To achieve 100% resilience across all cloud platforms (Vercel, GitHub Pages, Localhost) regardless of which broker the frontend is configured for, the bridge daemon should publish to **BOTH** `broker.hivemq.com` and `broker.emqx.io` simultaneously.

```python
BROKERS = [
    {"host": "broker.hivemq.com", "port": 1883},
    {"host": "broker.emqx.io", "port": 1883}
]
```

### 7.2 Dynamic Hot-Plug COM Scanner with Auto-Recovery
The bridge daemon must re-scan available COM ports on every reconnection attempt rather than caching a stale port:
1. Scan for CP210x, CH340, USB-UART, and FTDI descriptors.
2. If none match, iterate through available COM ports.
3. Automatically recover when the ESP32 is unplugged and moved to any USB socket.

### 7.3 Dual Parsing Engine (ASCII Debug + Raw JSON)
Support both ESP32 debug line formats (`PM1.0: ... | PM2.5: ...`) and direct JSON strings (`{"device_uid":"AIRSENSE-NODE-KHI-01", ...}`).

### 7.4 Production Bridge Daemon Specification
A unified, hardened Python bridge script (`scripts/airsense_serial_live_bridge.py`) should incorporate:
- `paho.mqtt.client.CallbackAPIVersion.VERSION2` support
- Non-blocking dual MQTT broker publishing
- Resilient local REST ingestion with 2.0s timeout
- Continuous background watchdog loop with exponential backoff
- PID file management for clean process termination

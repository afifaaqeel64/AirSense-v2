# Forensic Integrity Audit & Handoff Report

**Auditor**: Forensic Auditor 1 (AirSense-v2)  
**Date**: 2026-09-02  
**Working Directory**: c:/Users/HP/AirSense-v2/.agents/auditor_1  
**Integrity Mode**: Development (per ORIGINAL_REQUEST.md line 41)  

---

## Forensic Audit Report

**Work Product**: AirSense-v2 Full Telemetry & Resilience Pipeline (Python Serial Bridge Daemon, ESP32 Physical Firmware, Multi-Broker Cloud MQTT Infrastructure, Vercel/GitHub Pages Static Dashboards, and Automated Test Suite)  
**Profile**: General Project  
**Verdict**: **CLEAN**

### Phase Results
- **Phase 1: Source Code Analysis & Prohibited Pattern Detection**: PASS — No hardcoded test responses, fake mock returns in production files, dummy pass-throughs, or bypasses.
- **Phase 2: Python Serial Bridge Verification (`scripts/airsense_serial_live_bridge.py`)**: PASS — Genuinely scans and prioritizes CP210x/CH340/UART chips; implements non-crashing infinite auto-recovery retry loop with exponential backoff & jitter; dual-publishes to HiveMQ and EMQX using Paho v2 API (`CallbackAPIVersion.VERSION2`); robustly parses `[JSON_TELEMETRY]` lines and regex fallback for ASCII streams.
- **Phase 3: ESP32 Physical Firmware Verification (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`)**: PASS — Genuine UART2 driver on GPIO 16/17 for PMS7003 with checksum verification; genuine Bosch BME280 direct register I2C driver on GPIO 21/22 with compensation formulas; genuine 8-sample ADC averaging for rainplate on GPIO 34; binary MQTT 3.1.1 packet generation; transparent error reporting emitting `null` and `ERROR` rather than masking with fake numbers.
- **Phase 4: Frontend Dashboards & Auto-Reconnect Engine (`public/*.html`)**: PASS — Authentic Paho MQTT WebSocket client connections to `wss://broker.hivemq.com:8884/mqtt`, `wss://broker.emqx.io:8084/mqtt`, and `wss://test.mosquitto.org:8081/mqtt`; active multi-broker failover pool; 30s silence watchdog and zombie socket recycler; browser lifecycle event handlers (`online`, `visibilitychange`, `focus`); zero-NaN safe schema normalization; real-time DOM card/table updates.
- **Phase 5: Test Suite Integrity & Assertion Audit (`tests/`)**: PASS — All 221 tests genuinely exercise functionality with substantive, non-trivial assertions. Zero `assert True` trivialities.
- **Phase 6: Full Pytest Execution**: PASS — 221 passed in 217.61s (100% pass rate) with exit code 0.

---

## 1. Observation

Direct empirical observations gathered across source files, firmware, static distribution assets, and automated test executions:

1. **Python Serial Live Bridge Daemon (`scripts/airsense_serial_live_bridge.py`)**:
   - **Dynamic COM Scanning (lines 114-147)**: Scans available COM ports using `serial.tools.list_ports.comports()`, searches descriptions and HWIDs for keywords (`cp210`, `ch340`, `ch9102`, `ftdi`, `uart`, `usb serial`, `silicon labs`, `wch`, `arduino`, `espressif`), prioritizes matches, and cleanly respects or falls back from user-specified preferred ports.
   - **Dual-Broker MQTT Publisher Engine (lines 49-112)**: Initializes background MQTT clients for both HiveMQ (`broker.hivemq.com:1883`) and EMQX (`broker.emqx.io:1883`) supporting Paho v2 (`CallbackAPIVersion.VERSION2`) with isolated error handling per broker. Dual-publishes to primary topic `airsense/karachi/bic_roof/telemetry` and fallback topic `airsense/telemetry`.
   - **Infinite Auto-Recovery Loop (lines 293-378)**: Wraps serial connection and packet streaming in an infinite `while True:` loop. Catches `serial.SerialException`, detects `PermissionError`/`Access is denied` (e.g. Arduino IDE conflict) and gives user guidance, applies exponential backoff with random jitter (`min(backoff * 1.5, max_backoff)`), and guarantees port teardown via `finally: ser.close()`.
   - **Dual Stream Parser (lines 192-267)**: Detects structured JSON lines starting with `[JSON_TELEMETRY]` or raw JSON `{...}`, and falls back to regex matching for PMS7003 (`PM1.0: ... | PM2.5: ... | PM10: ...`), BME280 (`Temp: ... | Hum: ... | Press: ...`), Gas resistance, and Rain flags.

2. **ESP32 Hardened Physical Firmware (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`)**:
   - **PMS7003 UART Driver (lines 242-270)**: Configures hardware UART2 on GPIO 16 (RX) / 17 (TX) at 9600 baud. Verifies 32-byte frame header `0x42 0x4D` and computes 16-bit frame checksum. Returns explicit failure (`pm1 = -1.0, pm25 = -1.0, pm10 = -1.0`) on checksum mismatch or timeout.
   - **Bosch BME280 Direct Register Driver (lines 68-237)**: Initializes I2C on GPIO 21 (SDA) / 22 (SCL) at address `0x76` (with `0x77` fallback). Reads 24 calibration registers (`dig_T1..T3`, `dig_P1..P9`, `dig_H1..H6`). Executes standard Bosch integer compensation math for temperature, pressure, and relative humidity. Performs physical boundary sanity checks (-40°C to +85°C, 0-100% RH, 300-1200 hPa).
   - **Raindrop Sensor Driver (lines 275-289)**: Performs 8-sample ADC averaging on GPIO 34 (ADC1 CH6) with 2800 threshold logic.
   - **Non-Masked Error Reporting (lines 553-581, 600-630)**: When sensors fail, formats `null` string representations in JSON payload and `"ERROR"` in `sensor_health` dictionary, strictly avoiding masked fake constants.
   - **Dual-Broker MQTT Publisher (lines 294-406)**: Connects with binary MQTT 3.1.1 CONNECT packet, parses CONNACK, cycles broker index (`current_broker_idx = (current_broker_idx + 1) % NUM_BROKERS`) on timeout, and writes binary MQTT 3.1.1 PUBLISH packets.
   - **Non-Blocking Wi-Fi Reconnection (lines 410-449)**: Implements state machine with 10s reconnection interval without blocking the main telemetry loop.

3. **Frontend Dashboard SPAs (`public/index.html`, `public/hardware.html`, `public/command.html`, `public/enterprise.html`, `public/opensource.html`)**:
   - **Multi-Broker Failover Pool (lines 628-632)**: Configured with HiveMQ (`wss://broker.hivemq.com:8884/mqtt`), EMQX (`wss://broker.emqx.io:8084/mqtt`), and Mosquitto (`wss://test.mosquitto.org:8081/mqtt`).
   - **Active Failover & Reconnect Engine (lines 923-1019)**: Cycles broker on connection drops or after 2 failed retry attempts with exponential backoff and jitter.
   - **Silence Watchdog & Zombie Socket Recycler (lines 1024-1061)**: Evaluates elapsed time since last packet. If socket is connected but no packet has arrived for >30s, marks socket as zombie, forcefully disconnects, cycles broker, and reconnects. Transitions UI between `🟢 ESP32 LIVE CONNECTED` (<=10s), `🟡 ESP32 AWAITING TELEMETRY` (11-30s), and `🔴 ESP32 DISCONNECTED` (>30s with red banner).
   - **Lifecycle Event Handlers (lines 1066-1093)**: Listens for window `'online'`, `'visibilitychange'`, and `'focus'` events to automatically revive stale connections.
   - **Safe Schema Normalizer (lines 642-679)**: Resolves aliases (`pm2_5`, `pm25`, `temperature_c`, `temperature`), strips and sanitizes `NaN`, `null`, `undefined`, and `--` to prevent UI card crashes.
   - **Recorded Telemetry Log & CSV Export (lines 808-900)**: Maintains rolling 30-packet history in localStorage with direct CSV export.

4. **Static Hosting & Deployment Routing (`vercel.json`)**:
   - Valid configuration mapping `/hardware` -> `/public/hardware.html`, `/opensource` -> `/public/opensource.html`, `/command` -> `/public/command.html`, `/enterprise` -> `/public/enterprise.html`, and `/` -> `/public/index.html`.

5. **Empirical Automated Test Suite Execution**:
   - Command: `py -m pytest tests/ -v`
   - Execution Time: 217.61 seconds
   - Outcome: **221 passed / 221 total (100% Pass Rate)**
   - Module breakdown:
     - `tests/test_e2e_mqtt_pipeline.py`: 8 passed (Live HiveMQ & EMQX connection, packet routing, latency benchmark < 6000ms, dual-broker delivery sync)
     - `tests/test_bridge_resilience.py`: 20 passed (Dynamic COM scanning, locked port guidance, infinite reconnect, structured JSON and ASCII parsing)
     - `tests/test_payload_schema_and_safety.py`: 56 passed (Alias resolution, null handling, zero-NaN/Inf safety, float 0.0 preservation)
     - `tests/e2e/test_dual_dashboards_e2e.py`: 58 passed (Tiers 1-5 feature coverage, boundary conditions, cross-feature combinations, real-world operational scenarios, adversarial CSV formula injection hardening)
     - `tests/unit/test_challenger_hardware_diagnostics.py`: 19 passed (8s boundary enforcement, degraded sensor states, UART/I2C/ADC/VSPI pin troubleshooting guidance, concurrent stress)
     - `tests/unit/` & `tests/integration/`: 60 passed (Quality control engine, circular wind math, multi-provider weather consensus, walk-forward ML splitters, CSV imports, ingestion API)

---

## 2. Logic Chain

1. **Observation 1** proves that `scripts/airsense_serial_live_bridge.py` contains genuine serial port scanning and auto-recovery mechanisms with no hardcoded ports or dummy bypasses.
2. **Observation 2** proves that `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` authenticates physical sensor reads from PMS7003 (UART2), Bosch BME280 (I2C), and Rainplate (ADC), calculates legitimate calibrated telemetry, and transparently surfaces `null` and `ERROR` rather than masking failures.
3. **Observation 3** proves that `public/*.html` dashboards implement real WebSocket client connections across a multi-broker failover pool, an active watchdog with zombie socket recycling, browser lifecycle event revival, and robust NaN sanitization.
4. **Observation 4** proves that `vercel.json` correctly routes static SPAs without requiring any middleman backend server or tunnel.
5. **Observation 5** provides empirical validation through the end-to-end execution of 221 automated tests, including live public cloud MQTT broker communication and latency measurements.

---

## 3. Caveats

- Live cloud MQTT streaming requires an active internet connection to reach public brokers (`broker.hivemq.com` / `broker.emqx.io`).
- USB serial operation requires an attached ESP32 or simulated COM port.
- No integrity violations, cheats, regressions, or backdoors exist in the codebase.

---

## 4. Conclusion

The AirSense-v2 codebase adheres strictly to all engineering, architecture, and integrity standards outlined in `ORIGINAL_REQUEST.md` and `PROJECT.md`. All implementations are genuine, functional, and fully verified.

**Verdict: CLEAN**

---

## 5. Verification Method

To independently reproduce this forensic integrity audit:

1. **Execute the complete automated test suite**:
   ```powershell
   py -m pytest tests/ -v
   ```
   *Expected outcome*: `221 passed in ~215s (0:03:35)` with exit code 0.

2. **Run specific component test suites**:
   - *Live MQTT Pipeline*: `py -m pytest tests/test_e2e_mqtt_pipeline.py -v`
   - *Serial Bridge Daemon*: `py -m pytest tests/test_bridge_resilience.py -v`
   - *Payload Safety & Schema*: `py -m pytest tests/test_payload_schema_and_safety.py -v`
   - *Dual Dashboards E2E*: `py -m pytest tests/e2e/test_dual_dashboards_e2e.py -v`
   - *Challenger Hardware Diagnostics*: `py -m pytest tests/unit/test_challenger_hardware_diagnostics.py -v`

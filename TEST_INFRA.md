# E2E Test Infrastructure: Standalone Cloud & Dual Hardware Dashboards

## Test Philosophy
- **Requirement-Driven Verification**: Derived strictly from `ORIGINAL_REQUEST.md` and `PROJECT.md`.
- **Progressive Testability & Zero-Dependency Execution**: Covers both standalone serverless client execution (Cloud MQTT WebSockets over `broker.hivemq.com:8884`) and local REST API fallback arbitration.
- **Systematic 4-Tier Methodology (+ Tier 5 Adversarial Hardening)**:
  - **Tier 1: Feature Coverage (F1.1 – F4.3)**: Complete isolated validation across all functional features.
  - **Tier 2: Boundary & Corner Cases**: Strict time thresholds (8.0s heartbeat starvation), out-of-range sensor metrics, empty/null payloads, and MQTT backoff.
  - **Tier 3: Cross-Feature Combinations**: Pairwise and multi-subsystem coexistence (MQTT stream vs REST fallback priority arbitration, rapid online/offline flapping, and failover direction).
  - **Tier 4: Real-World Application Scenarios**: 5 comprehensive workflows (24/7 continuous streaming rolling buffer, hardware station reboot cycle, campus Wi-Fi drop & recover, public browser access from Vercel/GitHub Pages, and multi-sensor partial degradation).
  - **Tier 5: Adversarial & Stress Hardening**: CSV formula injection sanitization, extreme coordinates, unmapped WMO fallback, and type coercion.

---

## Feature Inventory & Test Mapping

| # | Feature | Requirement | Tier 1 (Coverage) | Tier 2 (Boundary/Corner) | Tier 3 (Cross-Feature) | Tier 4 (Scenario) | Status |
|---|---------|-------------|:-----------------:|:------------------------:|:----------------------:|:-----------------:|:------:|
| F1.1 | Direct Cloud MQTT WebSocket Connection | R1 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F1.2 | Telemetry Packet JSON Schema Ingestion | R1 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F1.3 | Reactive 8-Second Heartbeat Engine | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F1.4 | Plantower PMS7003 Laser UART Validation | R1 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F1.5 | Bosch BME280 I2C Bus Response | R1 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F1.6 | Raindrop ADC & MicroSD SPI Flash | R1 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F1.7 | Diagnostic Endpoint Contract | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F2.1 | Hardware Ground-Truth Route (/hardware) | R1 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F2.2 | Sensor Chip Status Badges & Pin Layout | R1 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F2.3 | Pulsating Green/Red Heartbeat Pill | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F2.4 | Real-Time 10-Column Telemetry Table | R1 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F2.5 | Static Web Packaging (paho-mqtt.js) | R3 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F2.6 | Cloud Deployment Config (Vercel & GH Pages) | R3 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F2.7 | Dynamic Disconnection Failover Banner | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F3.1 | 24/7 Open-Source Weather Hub (/opensource) | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F3.2 | Multi-Provider Meteorological Engine | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F3.3 | Latency Benchmarking Matrix (ms) | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F3.4 | Atmospheric Consensus Computation | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F3.5 | WMO 4501 Code Translation Registry | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F3.6 | 24-Hour AI Trajectory Forecast & CI | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F4.1 | Automated 24/7 Fallback Cascade | R2 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F4.2 | Topbar Navigation Switcher Coherence | R1 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |
| F4.3 | Platform Health, Readiness & Version | R1 / AC | ✓ | ✓ | ✓ | ✓ | **PASSED** |

---

## Test Architecture & Execution

### Test Execution Commands
- **Targeted E2E & Challenger Suite**:
  ```powershell
  py -3.13 -m pytest tests/e2e/test_dual_dashboards_e2e.py tests/unit/test_challenger_hardware_diagnostics.py -v
  ```
- **Execution Output**:
  - Total Tests: **77**
  - Passed: **77** (100% Pass Rate)
  - Failures: **0**
  - Duration: ~50.76s

### Key Test Suites & Directory Layout
- `tests/e2e/test_dual_dashboards_e2e.py`:
  - `TestTier1FeatureCoverage`: 23 feature-level tests validating Cloud MQTT configuration, JSON schema parsing, 8s heartbeat window, sensor chips (PMS7003, BME280, Rain, MicroSD), static packaging, deployment configs, and UI elements.
  - `TestTier2BoundaryAndCornerCases`: 17 boundary tests covering exact 8.0s timeout starvation, null/malformed JSON, reconnect loops, rapid packet bursts, and physical sensor range bounds.
  - `TestTier3CrossFeatureCombinations`: 8 cross-feature interaction tests covering MQTT stream + REST fallback coexistence, rapid online/offline flapping, concurrent topic subscribers, failover banners, and consensus computation.
  - `TestTier4RealWorldScenarios`: 5 end-to-end real-world workflows.
  - `TestTier5AdversarialHardening`: 5 security and stress hardening tests.
- `tests/unit/test_challenger_hardware_diagnostics.py`:
  - Empirical hardware diagnostics, 8s threshold boundaries, degraded states with pin troubleshooting, partial packets, and sequential telemetry stress.

---

## Real-World Application Scenarios (Tier 4)

1. **Scenario 1: 24/7 Continuous Streaming & Rolling Buffer**:
   - Hardware continuously broadcasts packets over WebSockets.
   - Frontend DOM dynamically manages a FIFO rolling buffer retaining the latest 15 telemetry rows (`tbody.rows.length <= 15`) with zero DOM memory leaks or page reflow flashes.

2. **Scenario 2: Hardware Station Reboot Cycle**:
   - Station streams valid telemetry (`LIVE_ACTIVE`).
   - ESP32 reboots (power cycle / OTA), leading to >8s packet silence.
   - Heartbeat engine transitions to `OFFLINE` / `ESP32 DISCONNECTED` and presents the failover banner.
   - ESP32 bootloader finishes and broadcasts first packet -> immediate recovery to `LIVE_ACTIVE` / `ESP32 LIVE CONNECTED`.

3. **Scenario 3: Campus Wi-Fi Drop & Auto-Reconnect**:
   - Simulated network drop severs the WebSocket connection (`client.onConnectionLost`).
   - Paho MQTT client executes exponential retry (`initCloudMQTT`) without requiring manual operator page refresh.

4. **Scenario 4: Public Browser Access from Vercel / GitHub Pages**:
   - Client loads standalone static distribution over HTTPS with `wss://broker.hivemq.com:8884/mqtt` (or `ws://broker.hivemq.com:8000/mqtt` on HTTP).
   - Validates zero runtime server dependencies and strict CSP compliance (`vercel.json`).

5. **Scenario 5: Multi-Sensor Partial Degradation**:
   - BME280 is valid, but PMS7003 reports zero counts (fan obstruction).
   - System enters `PARTIAL_DEGRADED` state and renders precise UART pin guidance (GPIO 16 RX / GPIO 17 TX, 5.0V VIN) while keeping BME280 online.

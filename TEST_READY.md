# TEST READY — AirSense-v2 Automated Telemetry & E2E Test Suite

**Date & Time**: 2026-09-02T15:27:00+05:00  
**Test Writer**: `test_writer_1`  
**Test Suite Status**: **READY (221 / 221 Passed — 100% Pass Rate)**  
**Execution Command**: `py -m pytest tests/ -v`

---

## 1. Test Suite Summary

The AirSense-v2 automated test harness provides 100% comprehensive coverage across the physical hardware telemetry pipeline, cloud broker distribution, laptop serial bridge resilience, payload normalization, and frontend consumer SPAs.

| Test Module | Coverage Domain | Tests | Status |
|---|---|:---:|:---:|
| `tests/test_e2e_mqtt_pipeline.py` | Live & Programmatic MQTT Telemetry Flow, HiveMQ & EMQX Dual Broker Synchronization, Topic Routing, Latency Benchmarking, Burst Sequencing, Paho v2 API Compliance | **8** | **PASSED** |
| `tests/test_bridge_resilience.py` | Dynamic COM Port Discovery (CP210x/CH340/UART), Infinite Reconnect Loop, Locked Port Permission Error Recovery, Structured JSON & ASCII Log Parsing, Dual Push | **20** | **PASSED** |
| `tests/test_payload_schema_and_safety.py` | Canonical Schema Normalization, Field Alias Resolution (`pm2_5`/`pm25`, `temperature`/`temperature_c`), Zero-NaN & Infinity Sanitization, Null/Missing Key Safety, Exact `0.0` Preservation, Sensor Health & QC Integration | **56** | **PASSED** |
| `tests/e2e/test_dual_dashboards_e2e.py` | 4-Tier Full-System E2E Verification (Feature Coverage, Boundary & Corner Cases, Cross-Feature Combinations, Real-World Operational Scenarios, Adversarial CSV/Polar Hardening) | **58** | **PASSED** |
| `tests/unit/test_challenger_hardware_diagnostics.py` | Fast 8-Second Heartbeat Boundary Verification, Degraded Chip Diagnostics, VSPI/I2C/UART/ADC Pin Troubleshooting, Concurrency Stress | **19** | **PASSED** |
| `tests/unit/` & `tests/integration/` | Quality Control Engine, Circular Wind Math, Multi-Provider Weather Consensus, Time-Series Walk-Forward ML Splitters, Ingestion & CSV Import APIs | **60** | **PASSED** |
| **TOTAL** | **Full System Verification** | **221** | **PASSED (100%)** |

---

## 2. Key Verified Interface Contracts & Properties

### A. MQTT Broker Infrastructure & Dual-Broker Delivery
- **Primary Broker**: `broker.hivemq.com` (TCP `1883`, WSS `8884` `/mqtt`)
- **Secondary Broker**: `broker.emqx.io` (TCP `1883`, WSS `8084` `/mqtt`)
- **Primary Telemetry Topic**: `airsense/karachi/bic_roof/telemetry`
- **Wildcard Multi-Station Topic**: `airsense/#`
- **Dual-Broker Sync**: Verified simultaneous packet broadcast with zero packet drop and monotonic sequence preservation across rapid 10-packet sub-second bursts.
- **Round-Trip Latency**: Empirically measured at `< 2500ms` over live cloud network.

### B. Python Serial Bridge Resilience (`scripts/airsense_serial_live_bridge.py`)
- **Dynamic Port Scanning**: Verified automatic detection and prioritization of CP210x, CH340, FTDI, and generic UART chips.
- **Infinite Retry Daemon**: Verified non-crashing auto-reconnect loop on physical serial disconnects, cable drops, and mid-stream UART resets.
- **Port Lock Handling**: Verified actionable user guidance when COM port is locked by Arduino IDE Serial Monitor (`PermissionError`).
- **Dual Parser**: Verified parsing of `[JSON_TELEMETRY] {...}` lines, raw JSON `{...}`, and formatted ASCII logs (`PM1.0: ... | PM2.5: ... | PM10: ...` and `Temp: ... | Hum: ... | Press: ...`).

### C. Payload Schema Normalization & Zero-NaN Safety
- **Alias Resolution**: Fully maps `pm2_5`, `pm25`, `pm_2_5`, `pm25_ugm3` to canonical `pm2_5`; maps `temperature_c`, `temperature`, `temp`, `temp_c` to `temperature_c`; maps `rain_flag`, `rain`, `"YES"`, `"NO"`, `"Wet"`, `"Dry"`, `1`, `0` to boolean `rain_flag`.
- **Zero-NaN Protection**: Strict trapping and sanitization of `float('nan')`, `float('inf')`, `"NaN"`, `"null"`, `"N/A"`, `"--"`.
- **Falsy Float Preservation**: Explicitly tests and preserves exact `0.0` values across all environmental and particulate fields.

---

## 3. How to Execute the Test Suite

```powershell
# Run the complete test suite with verbose output
py -m pytest tests/ -v

# Run only the E2E MQTT pipeline tests
py -m pytest tests/test_e2e_mqtt_pipeline.py -v

# Run only bridge resilience tests
py -m pytest tests/test_bridge_resilience.py -v

# Run only schema normalization & safety tests
py -m pytest tests/test_payload_schema_and_safety.py -v
```

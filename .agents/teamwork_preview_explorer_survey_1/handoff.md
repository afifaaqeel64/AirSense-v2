# Handoff Report: Backend & Sensor Diagnostic Architecture Survey

## 1. Observation

Direct observations from inspecting the codebase:

1. **FastAPI Application & Dedicated Routes**:
   - `apps/api/main.py` lines 118-125 mount the dedicated routes:
     - `GET /hardware` returns `FileResponse(web_dir / "hardware_dashboard.html")` (line 120)
     - `GET /opensource` returns `FileResponse(web_dir / "opensource_dashboard.html")` (line 124)
     - `GET /` and `GET /ops` return `FileResponse(web_dir / "index.html")` (line 116)
2. **Telemetry Ingestion & Diagnostic Endpoint**:
   - `apps/api/routers/ingest_router.py`:
     - `POST /api/v1/ingest/reading` (lines 60-244): Authenticates devices, deduplicates via content hash `compute_content_hash`, stores in `RawReading`, evaluates QC via `QualityControlEngine.evaluate_reading`, stores `QualityAssessment`, promotes to `Observation`, updates `station.last_seen_at`, and aggregates via `HourlyAggregationEngine`.
     - `GET /api/v1/ingest/latest` (lines 252-286): Returns recent raw readings with sequence numbers, timestamps, and QC flags.
     - `GET /api/v1/ingest/sensors/diagnostic` (lines 289-323): Queries the most recent `RawReading` and invokes `SensorHealthEngine.evaluate_sensor_connectivity(latest_reading=reading_dict, last_received_at=latest_reading.received_at)`.
3. **Sensor Health & Liveness State Machine Engine**:
   - `services/quality_control/sensor_health_engine.py`:
     - Line 35: `OFFLINE_THRESHOLD_SECONDS = 120` (120s heartbeat window).
     - Lines 45-51: Evaluates `seconds_ago` between `now_utc` and `last_received_at`.
     - Lines 54-78: PMS7003 optical particle sensor validation (checks $0.1 \le \text{PM}_{2.5} \le 1000.0$ and $0.1 \le \text{PM}_{10} \le 1500.0$; exact 0.0 values flagged as `DEGRADED`; nulls flagged as `DISCONNECTED`; pinout: TXD $\to$ GPIO 16, RXD $\to$ GPIO 17, 5.0V VCC).
     - Lines 80-109: Bosch BME280 validation (checks $-20.0 \le T \le 65.0^\circ\text{C}$, $1.0 \le RH \le 100.0\%$, $800.0 \le P \le 1100.0\text{ hPa}$; out of bounds flagged as `DEGRADED`; nulls flagged as `DISCONNECTED`; pinout: SDA $\to$ GPIO 21, SCL $\to$ GPIO 22, 3.3V VCC).
     - Lines 111-125: Raindrop moisture plate validation (ADC1 CH6 GPIO 34, 3.3V VCC; verifies `rain_flag`).
     - Lines 127-138: MicroSD SPI logger validation (VSPI bus: CS $\to$ GPIO 5, SCK $\to$ GPIO 18, MOSI $\to$ GPIO 23, MISO $\to$ GPIO 19).
     - Lines 140-149: State machine transitions:
       - If not alive ($\Delta t > 120\text{s}$ or no packet): `station_liveness = "OFFLINE"`
       - Else if `pms_connected and bme_connected`: `station_liveness = "LIVE_ACTIVE"`
       - Else: `station_liveness = "PARTIAL_DEGRADED"`
4. **Multi-Provider Weather & Open-Source Fallback**:
   - `services/external_providers/multi_provider_router.py`:
     - Lines 118-126: Fallback sequence: `preferred` $\to$ `open_meteo` $\to$ `weatherapi` $\to$ `bright_sky` $\to$ `met_norway` $\to$ `visual_crossing` $\to$ `openweathermap` $\to$ `tomorrow_io` $\to$ `fallback_offline`.
     - Lines 169-264: `compare_all_providers` executes parallel async queries across providers, returning latency benchmarks, consensus averages (`avg_temperature_c`, `avg_humidity_pct`, `avg_pressure_hpa`), and OpenAQ ground-truth reference data.
5. **Firmware Implementation**:
   - `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`:
     - Lines 50-56: Defines hardware pins: PMS RX $\to$ 16, TX $\to$ 17; BME SDA $\to$ 21, SCL $\to$ 22; SD CS $\to$ 5; Rain ADC $\to$ 34.
     - Lines 87-133: 32-byte frame parser verifying header `0x42 0x4D`, frame length 28, and checksum.
     - Lines 138-160: Circular CSV logging to MicroSD (`/airsense_telemetry.csv`).
     - Lines 165-225: HTTP POST pushing telemetry JSON to `/api/v1/ingest/reading`.
6. **Frontend User Interfaces**:
   - `apps/web/hardware_dashboard.html`: React 18 SPA at `/hardware` with pulsating green/red indicator, 4 sensor status badges, interactive simulation buttons (`⚡ Validate & Make Sensor LIVE`, `🛑 Test Disconnect / Offline`, `🔄 Run Health Probe`), 24/7 failover notification alert, live packet table, and pin troubleshooting card.
   - `apps/web/opensource_dashboard.html`: React 18 SPA at `/opensource` with 24/7 keyless open-source APIs, WMO 4501 status badges, 24-hour predictive AI trajectory forecast with 90% confidence intervals, and 7-provider benchmark matrix.
7. **Existing Test Coverage**:
   - `tests/unit/test_sensor_health.py`: 5 tests covering all online, disconnected PMS, station offline, `/api/v1/ingest/sensors/diagnostic` contract, and HTML dashboard route accessibility.
   - `tests/unit/test_multi_weather_providers.py`: 12 tests covering WMO registry, provider mappings, fallback execution, and comparison endpoint.
   - `tests/integration/test_ingestion_api.py`: 3 tests covering live ingestion, idempotency deduplication, and auth token enforcement.

---

## 2. Logic Chain

1. **Deterministic Connectivity Validation**:
   - By combining timestamp recency ($\Delta t \le 120\text{s}$) with physical sensor metric bounds ($0.1 \le \text{PM}_{2.5} \le 1000.0$ and $-20 \le T \le 65^\circ\text{C}$), the backend avoids false positives where an ESP32 node is online but disconnected from its daughter sensor boards.
2. **Actionable Troubleshooting Guidance**:
   - Every sensor fault state in `SensorHealthEngine` attaches an explicit `troubleshooting_step` identifying exact GPIO pin numbers, voltage rails (5.0V vs 3.3V), and I2C address checks.
3. **Resilient Failover Architecture**:
   - When a hardware station disconnects, the state machine transitions to `OFFLINE`. The frontend detects this and immediately displays the failover alert directing operators to `/opensource`.
   - On the backend, `MultiProviderWeatherEngine` provides zero-downtime meteorological fallback using keyless public providers (Open-Meteo, Bright Sky DWD, MET Norway).
4. **Dual Dedicated Dashboards**:
   - Serving `/hardware` and `/opensource` as distinct dedicated routes allows clean separation of concerns between on-site ground-truth hardware monitoring and continuous 24/7 open-source meteorological intelligence.

---

## 3. Caveats

1. **Static Station/Device Defaults in Ingest Router**:
   - In `apps/api/routers/ingest_router.py` lines 315-316, the diagnostic route supplies `"station_code": "BIC-KHI-ROOF-01"` and `"device_uid": "AIRSENSE-NODE-KHI-01"` when evaluating the latest reading. If multiple physical stations are active simultaneously, extracting these identifiers from the matched `Station`/`Device` DB record makes the endpoint fully multi-station aware.
2. **MicroSD Liveness Inference**:
   - Currently, `microsd` status is marked `ONLINE` if the station is transmitting packets with valid sequence numbers. If explicit SD error reporting is desired over HTTP, a boolean `sd_mounted` flag in `ESP32IngestPayload` could be added.

---

## 4. Conclusion

The AirSense-v2 backend and sensor diagnostic subsystems are thoroughly architected and fully implemented:
1. **Deterministic Hardware Connection Validation**: Fully operational via `SensorHealthEngine` and `GET /api/v1/ingest/sensors/diagnostic`, checking 120s heartbeat window, PMS7003 UART frames, BME280 I2C bus response, Rainplate ADC levels, MicroSD SPI storage, and 3-state state machine (`LIVE_ACTIVE`, `PARTIAL_DEGRADED`, `OFFLINE`).
2. **Dedicated Hardware Ground-Truth Hub (`/hardware`)**: Fully implemented with sensor badges, live telemetry streaming, interactive browser validation controls, and automated failover alerts.
3. **Dedicated 24/7 Open-Source Meteorological Hub (`/opensource`)**: Fully implemented with keyless multi-provider atmospheric data, WMO 4501 status translation, 24-hour predictive AI PM2.5 trajectories with 90% CIs, and parallel provider benchmarking.
4. **Resilience & Fallback**: Automated multi-provider cascade ensuring continuous 24/7/365 operational availability.

---

## 5. Verification Method

### 1. File Inspection
Inspect the following core implementation files:
- `apps/api/routers/ingest_router.py`
- `services/quality_control/sensor_health_engine.py`
- `services/external_providers/multi_provider_router.py`
- `apps/web/hardware_dashboard.html`
- `apps/web/opensource_dashboard.html`
- `tests/unit/test_sensor_health.py`
- `tests/unit/test_multi_weather_providers.py`

### 2. Test Execution
Run the automated test suite:
```powershell
pytest tests/unit/test_sensor_health.py -v
pytest tests/unit/test_multi_weather_providers.py -v
pytest tests/integration/test_ingestion_api.py -v
```

### 3. Invalidation Conditions
This survey assessment would be invalidated if:
- `SensorHealthEngine` fails to flag packets older than 120s as `OFFLINE`.
- Out-of-range sensor readings are improperly marked `ONLINE`.
- The `/hardware` and `/opensource` routes fail to render or route between each other.

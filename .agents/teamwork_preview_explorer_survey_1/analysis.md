# Comprehensive Backend & Sensor Diagnostic Analysis Report

## 1. Executive Summary
This investigation analyzed the AirSense-v2 codebase in `c:\Users\HP\AirSense-v2` focusing on backend architecture, telemetry ingestion pipelines, deterministic hardware sensor connectivity diagnostics, multi-provider weather fallback, and dedicated dashboard routes.

The platform is built on an asynchronous **FastAPI** backend with **SQLAlchemy 2.0 / aiosqlite** storage, a **6-stage Sensory Quality Control engine**, a dedicated **Sensor Health & Liveness Engine**, and dual dedicated frontend dashboards (`/hardware` and `/opensource`).

---

## 2. Backend Architecture & Technology Stack

### 2.1 Core Framework & Entrypoints
- **Application Framework**: FastAPI (`apps/api/main.py`) running on Python 3.12/3.13 with async lifespan management (`lifespan`).
- **Database Engine**: SQLAlchemy 2.0 Async with `aiosqlite` targeting SQLite (`./data/airsense.db`) with fallback support for PostgreSQL via `asyncpg`.
- **Database Models**: Defined in `apps/api/db/models.py`, comprising:
  - `Campus` & `Station`: Geographic and metadata hierarchy.
  - `Device`: Hardware identity (`ESP32_WROOM_32D`), firmware version, and salted SHA-256 token hash.
  - `RawReading`: Non-destructive raw telemetry store with SHA-256 content hashes (`content_hash`) and idempotency keys (`idempotency_key`).
  - `QualityAssessment`: Evaluation flags (impossible values, high humidity, ordering consistency, spikes) and composite quality score $[0.0, 1.0]$.
  - `Observation` & `HourlyObservation`: Model-eligible ground-truth observations and hourly rollups with circular wind direction averaging.
  - `ModelRun`, `Prediction`, `EvaluationEvent`: Operational ML forecasting and validation tracking.
  - `ExternalProviderRun` & `ExternalComparison`: Meteorological sync runs and side-by-side comparative benchmarks.

### 2.2 Ingestion & Health Routes
1. **Telemetry Ingestion**: `POST /api/v1/ingest/reading` in `apps/api/routers/ingest_router.py`
   - Accepts `ESP32IngestPayload` (matching ESP32 firmware schema).
   - Validates device authentication via `Bearer` token or `X-Device-Token`.
   - Checks content-hash deduplication (`compute_content_hash(station_code, observed_at, pm2_5, temp)`).
   - Inserts `RawReading`, executes `QualityControlEngine.evaluate_reading`, records `QualityAssessment`, creates `Observation` (if quality score $\ge 0.60$), updates `station.last_seen_at`, and computes hourly aggregates.
2. **Latest Telemetry Stream**: `GET /api/v1/ingest/latest`
   - Returns up to 50 recent raw readings with sequence numbers, timestamps, PM1/PM2.5/PM10, temperature, humidity, pressure, and rain flags.
3. **Sensor Diagnostic Endpoint**: `GET /api/v1/ingest/sensors/diagnostic`
   - Evaluates the most recent `RawReading` and invokes `SensorHealthEngine.evaluate_sensor_connectivity`.
4. **General Platform Health**: `GET /api/v1/health`, `GET /api/v1/ready`, `GET /api/v1/version`.

---

## 3. Sensor Connectivity & Hardware Diagnostic Architecture

The hardware connectivity evaluation is implemented in `services/quality_control/sensor_health_engine.py` via `SensorHealthEngine`.

### 3.1 Packet Recency & Heartbeat Window
- **Threshold**: `OFFLINE_THRESHOLD_SECONDS = 120` (2 minutes).
- **Calculation**: Computes elapsed seconds between current UTC time and `last_received_at`:
  $$\Delta t = \text{now\_utc} - \text{last\_received\_at}$$
- **Evaluation**:
  - If `last_received_at` is None or $\Delta t > 120\text{s}$, the station is marked as `is_station_alive = False`, forcing overall station state to **`OFFLINE`**.
  - All sensors default to `is_connected = False` with actionable recovery steps.

### 3.2 Individual Physical Sensor Health Rules

| Sensor | Physical Interface | Pin Mapping | Valid Operational Bounds | Degradation / Fault State | Troubleshooting Guidance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Plantower PMS7003** | UART2 (Serial) | TXD $\to$ GPIO 16 (RX2)<br>RXD $\to$ GPIO 17 (TX2)<br>VCC $\to$ 5.0V VIN | $0.1 \le \text{PM}_{2.5} \le 1000.0\ \mu\text{g/m}^3$<br>$0.1 \le \text{PM}_{10} \le 1500.0\ \mu\text{g/m}^3$ | - Exact zero counts ($\text{PM}_{2.5} = 0, \text{PM}_{10} = 0$) $\to$ `DEGRADED`<br>- Missing/null $\to$ `DISCONNECTED` | *"Check 5.0V power rail wire, and verify Pin 4 (TXD) -> GPIO 16, Pin 5 (RXD) -> GPIO 17."* |
| **Bosch BME280** | I2C Bus (0x76/0x77) | SDA $\to$ GPIO 21<br>SCL $\to$ GPIO 22<br>VCC $\to$ 3.3V (Strictly) | $-20.0^\circ\text{C} \le T \le 65.0^\circ\text{C}$<br>$1.0\% \le RH \le 100.0\%$<br>$800.0 \le P \le 1100.0\text{ hPa}$ | - Out-of-bounds readings $\to$ `DEGRADED`<br>- Missing/null $\to$ `DISCONNECTED` | *"Check 3.3V rail (NEVER 5V), verify SDA -> GPIO 21, SCL -> GPIO 22, and common ground bridge."* |
| **Raindrop Plate** | ADC1 CH6 (Analog) | AO $\to$ GPIO 34<br>VCC $\to$ 3.3V<br>GND $\to$ GND | `rain_flag` is boolean (`True` = Wet, `False` = Dry) | - Null / unread ADC $\to$ `DISCONNECTED` | *"Verify Rain comparator board AO pin -> ESP32 GPIO 34 and VCC -> 3.3V."* |
| **MicroSD SPI Logger** | VSPI Bus | CS $\to$ GPIO 5<br>SCK $\to$ GPIO 18<br>MOSI $\to$ GPIO 23<br>MISO $\to$ GPIO 19 | Verified mounted filesystem with valid sequence | - Station offline or card unmounted $\to$ `DISCONNECTED` | *"Ensure FAT32 Samsung EVO card is inserted and CS -> GPIO 5, SCK -> GPIO 18, MOSI -> GPIO 23, MISO -> GPIO 19."* |

### 3.3 Station State Machine & Transition Logic
The station state transitions deterministically based on sensor probe outcomes:
1. **`OFFLINE`**:
   - Condition: No telemetry packet received within the 120s heartbeat window ($\Delta t > 120\text{s}$) or `last_received_at is None`.
   - Summary: *"Hardware station is OFFLINE. No telemetry received within the last 120 seconds. Check Mini UPS power and Wi-Fi connection."*
2. **`LIVE_ACTIVE`**:
   - Condition: Station is alive ($\Delta t \le 120\text{s}$) AND both primary sensors are verified (`pms_connected == True` and `bme_connected == True`).
   - Summary: *"All physical sensors are verified CONNECTED and streaming live ground-truth telemetry."*
3. **`PARTIAL_DEGRADED`**:
   - Condition: Station is alive ($\Delta t \le 120\text{s}$) BUT either PMS7003 or BME280 (or both) failed connectivity checks.
   - Summary: *"Station is transmitting, but one or more sensors failed hardware connectivity validation."*

---

## 4. Multi-Provider Weather Fallback & Open-Source Hub

The meteorological intelligence subsystem in `services/external_providers/multi_provider_router.py` orchestrates 8 atmospheric sources:
1. **Open-Meteo**: Primary zero-key open-source provider (hourly numerical weather + CAMS air quality).
2. **WeatherAPI.com**: High-quota key provider with integrated air quality and astronomy data.
3. **Bright Sky / DWD**: Zero-key German Weather Service open-source API.
4. **MET Norway**: Zero-key Nordic Meteorological Institute API.
5. **Visual Crossing**: High-resolution historical and 15-day solar forecasts.
6. **OpenWeatherMap**: Real-time atmospheric conditions and air pollution index.
7. **Tomorrow.io**: Hyperlocal minute precipitation data.
8. **OpenAQ**: Global reference monitor ground-truth comparison.

### Fallback Hierarchy
When querying `/api/v1/providers/weather/current`, `MultiProviderWeatherEngine` executes an automated fallback cascade:
$$\text{Preferred Provider} \to \text{Open-Meteo} \to \text{WeatherAPI} \to \text{Bright Sky} \to \text{MET Norway} \to \text{Visual Crossing} \to \text{OpenWeatherMap} \to \text{Tomorrow.io} \to \text{Synthetic Fallback}$$
- Real-time caching is enabled with 60-second TTL.
- WMO 4501 standard weather codes ($0..99$) are mapped with descriptions, Lucide/FontAwesome icons, and status colors.
- Consensus weather calculation aggregates mean temperature, humidity, and barometric pressure across all active providers in `/api/v1/providers/weather/compare`.

---

## 5. Frontend Dashboards & Dedicated Routes

### 5.1 Route Mounting (`apps/api/main.py`)
- `/` or `/ops`: Serves master operations interface (`apps/web/index.html`).
- `/hardware`: Serves dedicated Hardware Ground-Truth Hub (`apps/web/hardware_dashboard.html`).
- `/opensource`: Serves dedicated 24/7 Open-Source Meteorological Hub (`apps/web/opensource_dashboard.html`).
- `/enterprise`: Serves Enterprise Platform (`apps/web_enterprise/index.html`).

### 5.2 Hardware Ground-Truth Dashboard Features (`/hardware`)
- **Visual Status Badges**: Real-time sensor chip badges for PMS7003, BME280, Rainplate, and MicroSD with interface specs, pin configurations, and live values.
- **Pulsating Liveness Indicator**:
  - Green pulsating dot (`SENSOR: LIVE & STREAMING`) when `isLiveActive` is true.
  - Red pulsating dot (`SENSOR: OFFLINE / DISCONNECTED`) when timed out.
- **Interactive Validation Test Suite**:
  - `⚡ Validate & Make Sensor LIVE`: Emulates live calibrated ESP32 packet transmission to `/api/v1/ingest/reading`.
  - `🛑 Test Disconnect / Offline`: Emulates sensor disconnection / I2C ACK timeout.
  - `🔄 Run Health Probe`: Triggers immediate re-evaluation of `/api/v1/ingest/sensors/diagnostic`.
- **24/7 Failover Notification Banner**: Activates automatically on sensor disconnect, warning the operator and providing a one-click CTA to the Open-Source Dashboard.
- **Live Ingestion Telemetry Stream**: Auto-refreshing table displaying verified packets with timestamps, sequence numbers, and QC status.

### 5.3 24/7 Open-Source Dashboard Features (`/opensource`)
- **Keyless & Multi-API Integration**: Real-time atmospheric metrics (Temperature, Humidity, Pressure, Wind Speed, Rain).
- **WMO 4501 Atmospheric Badge**: Standardized weather condition indicators.
- **24-Hour Walk-Forward Predictive AI Table**: PM2.5 trajectory forecast with 90% confidence intervals and operational HVAC ventilation advisories.
- **Multi-Provider Comparative Benchmark Matrix**: Side-by-side comparison across 7 weather providers and OpenAQ reference monitors with latency tracking and consensus metrics.

---

## 6. Test Harness & Test Coverage

### Test Suites Located in `tests/`:
1. `tests/unit/test_sensor_health.py`:
   - `test_sensor_health_all_online`: Verifies `LIVE_ACTIVE` status and all 4 sensors online.
   - `test_sensor_health_disconnected_pms`: Verifies `PARTIAL_DEGRADED` status when PMS7003 is disconnected.
   - `test_sensor_health_station_offline`: Verifies `OFFLINE` status when no packet received for $>120$ seconds.
   - `test_api_sensor_diagnostic_endpoint`: Verifies `GET /api/v1/ingest/sensors/diagnostic` endpoint contract.
   - `test_api_dedicated_dashboard_routes`: Verifies `GET /hardware` and `GET /opensource` return HTTP 200 with appropriate HTML content.
2. `tests/unit/test_multi_weather_providers.py`:
   - Validates WMO 4501 registry completeness and provider condition-to-WMO mappings.
   - Validates multi-provider fallback hierarchy and parallel comparative benchmarking.
   - Validates `/api/v1/providers/weather/current`, `/api/v1/providers/weather/compare`, and `/api/v1/providers/status`.
3. `tests/integration/test_ingestion_api.py`:
   - Tests live ESP32 ingestion with valid device tokens, duplicate rejection, and unauthorized token handling.

---

## 7. Observations & Architectural Recommendations

1. **Station Dynamic Resolution**:
   - In `apps/api/routers/ingest_router.py` (lines 315-316), `station_code` and `device_uid` default to `"BIC-KHI-ROOF-01"` and `"AIRSENSE-NODE-KHI-01"`. For multi-station deployments, resolving the `station_code` and `device_uid` directly from the joined `Station` and `Device` records in the database query provides seamless dynamic multi-station support.
2. **Deterministic Simulator Integration**:
   - The browser-based validation tools in `hardware_dashboard.html` interact directly with the live `/api/v1/ingest/reading` route, allowing hardware engineers to simulate both continuous streaming and hardware faults in real time.
3. **Zero-Downtime High-Availability**:
   - The combination of edge MicroSD logging in the ESP32 firmware (`airsense_esp32_firmware.ino`) and cloud multi-provider numerical model fallback guarantees continuous 24/7/365 telemetry and forecasting capability.

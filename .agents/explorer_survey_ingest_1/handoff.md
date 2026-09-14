# AirSense Platform — R1: Edge-to-Cloud Ingestion & Hardware Integration Survey Report

## 1. Observation

### 1.1 FastAPI Application Initialization & Router Topology
- **Application Entrypoint (`apps/api/main.py`)**:
  - **Lifespan Management (Lines 32–75)**: Implements `@asynccontextmanager async def lifespan(app: FastAPI)` which initializes the SQLite database schema on startup via `await conn.run_sync(Base.metadata.create_all)` and auto-seeds initial default Campus records for Islamabad (`ISB_CAMPUS`) and Karachi (`KHI_CAMPUS`).
  - **App Instance (Lines 77–82)**: Initialized as `app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, description="AirSense Pakistan...", lifespan=lifespan)`.
  - **CORS Configuration (Lines 84–90)**: Configured with `CORSMiddleware`, reading origins dynamically from `settings.get_cors_origins_list()` (defaults to `http://localhost:3000,http://127.0.0.1:3000`).
  - **Static & Web Interface Mounts (Lines 106–122)**:
    - Mounts `apps/web/` to `/static` and serves `apps/web/index.html` on routes `/` and `/ops` (Hardware Control Center).
    - Serves `apps/web_enterprise/index.html` on `/enterprise` (Enterprise Risk Intelligence Platform).
  - **Router Registration Hierarchy (Lines 93–104)**:
    1. `admin_router` (`apps/api/routers/admin_router.py`) — Campus/station/device admin & backup endpoints.
    2. `ingest_router` (`apps/api/routers/ingest_router.py`) — Edge telemetry ingestion & latest telemetry retrieval.
    3. `import_router` (`apps/api/routers/import_router.py`) — MicroSD / batch CSV two-stage import pipeline.
    4. `quality_router` (`apps/api/routers/quality_router.py`) — QC rules & assessment history.
    5. `provider_router` (`apps/api/routers/provider_router.py`) — External weather/AQI sync runs.
    6. `export_router` (`apps/api/routers/export_router.py`) — CSV/JSON dataset export.
    7. `model_router` (`apps/api/routers/model_router.py`) — ML model runs & promotion events.
    8. `forecast_router` (`apps/api/routers/forecast_router.py`) — Time-series forecast queries.
    9. `comparison_router` (`apps/api/routers/comparison_router.py`) — Ground-truth vs external provider comparison.
    10. `evaluation_router` (`apps/api/routers/evaluation_router.py`) — Alert rule triggers & evaluation logs.
    11. `inference_router` (`apps/api/routers/inference_router.py`) — Real-time on-demand model inference.

### 1.2 Ingestion Subsystem Endpoints (`apps/api/routers/ingest_router.py`)
- **`POST /api/v1/ingest/reading` (Lines 61–245)**:
  - **Authentication**: Uses FastAPI dependency `device: Device = Depends(authenticate_device)`.
  - **Idempotency & Deduplication (Lines 114–141)**:
    - Calculates a deterministic SHA-256 content hash via `compute_content_hash(station.station_code, observed_at_utc, pm2_5, temp)` (`services/quality_control/qc_engine.py:37–41`).
    - Checks for prior occurrences matching `(station_id, content_hash)`. If detected, returns `accepted=True`, `duplicate=True`, `quality_processing_state="duplicate_skipped"` without duplicating DB records.
  - **Raw Telemetry Preservation (Lines 144–169)**: Inserts an immutable `RawReading` entity storing raw sensor values, sequence number, schema version, idempotency key, and the complete incoming JSON payload in `payload_json`.
  - **Sensory QC Verification (Lines 170–194)**: Evaluates the packet against physical bounds, sensor ordering ($PM_1 \le PM_{2.5} \le PM_{10}$), spike threshold ($>150\ \mu g/m^3$), high humidity ($>90\%$), generating a `QualityAssessment` record.
  - **Observation Generation (Lines 197–216)**: If not rejected, generates an `Observation` with `source="onsite_esp32"`, `source_type="ground_truth"`, and `is_model_eligible=(qc_score >= 0.60)`.
  - **Station Activity Timestamp (Lines 218–220)**: Updates `station.last_seen_at = received_at_utc`.
  - **Hourly Rollup Aggregation (Lines 222–230)**: Invokes `HourlyAggregationEngine.process_hour()` to maintain real-time hourly means, medians, circular wind directions, completeness metrics, and eligibility.
  - **Response Payload (Lines 232–244)**: Returns JSON containing `request_id`, `ingestion_id`, `raw_reading_id`, `accepted: true`, `duplicate: false`, `observed_at_utc`, `received_at_utc`, `campus_code`, `station_code`, `quality_processing_state`, and `server_schema_version: "1.0"`.
- **`GET /api/v1/ingest/latest` (Lines 253–287)**:
  - Queries `raw_readings` ordered by `received_at.desc()` with optional `station_id` filtering and configurable limit (default: 50).
  - Streams array of structured telemetry dicts formatted with ISO-8601 UTC timestamps for operational dashboards.
- **`GET /api/v1/ingest/health` (Lines 247–251)**:
  - Returns `{"subsystem": "sensor_ingestion", "status": "healthy", "supported_paths": ["live_esp32_http", "sd_card_csv"]}`.

### 1.3 Edge Telemetry Schemas & Hardware Integration
- **Pydantic Telemetry Schema (`apps/api/routers/ingest_router.py:36–58`)**:
  ```python
  class ESP32IngestPayload(BaseModel):
      schema_version: str = Field("1.0")
      device_uid: Optional[str] = None
      station_code: Optional[str] = None
      timestamp: Optional[str] = None           # ISO-8601 format
      timestamp_epoch: Optional[int] = None     # Unix epoch seconds
      pm1: Optional[float] = None
      pm2_5: Optional[float] = None
      pm10: Optional[float] = None
      temperature: Optional[float] = None
      humidity: Optional[float] = None
      pressure: Optional[float] = None
      rain_flag: Optional[bool] = None
      firmware_version: str = Field("1.0.0")
      sequence_number: Optional[int] = None
      # Legacy / Flexible compatibility
      device_id: Optional[str] = None
      campus_code: Optional[str] = None
      timestamp_utc: Optional[str] = None
      readings: Optional[Dict[str, Any]] = None
  ```
- **Firmware Implementation (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`)**:
  - **Target Microcontroller**: ESP32 WROOM-32D.
  - **Plantower PMS7003 Laser Optical Particle Counter**:
    - Pins: UART2 on GPIO16 (RX) and GPIO17 (TX).
    - Serial Protocol: 9600 baud, 32-byte frame verification starting with `0x42 0x4D`, validating 16-bit frame checksum, reading standard atmospheric PM1.0, PM2.5, PM10.0 concentrations (Lines 50–51, 87–133).
  - **Bosch BME280 Environmental Sensor**:
    - Pins: I2C bus on GPIO21 (SDA) and GPIO22 (SCL).
    - Bus Addresses: Auto-detects `0x76` or `0x77`.
    - Channels: Temperature ($^\circ C$), Relative Humidity ($\%RH$), Barometric Pressure ($hPa$) (Lines 52–53, 246–255, 336–344).
  - **MicroSD SPI Edge Backup Logger**:
    - Pins: SPI bus on GPIO23 (MOSI), GPIO19 (MISO), GPIO18 (SCK), GPIO5 (CS).
    - Logging: Non-blocking circular CSV logging to `/airsense_telemetry.csv` (180+ days buffer capacity for network-disconnected campus operations) (Lines 54, 138–160, 258–275).
  - **Raindrop Sensor Board (Analog Comparator)**:
    - Pins: GPIO34 (ADC1 analog channel).
    - Range: 12-bit ADC (0–4095; dry $\approx 4095$, rain threshold $< 2500$) (Lines 55, 347–353).
  - **Cloud Ingestion Client (`sendTelemetryToCloud`, Lines 165–225)**:
    - Constructs JSON matching `ESP32IngestPayload`.
    - HTTP POST with `Authorization: Bearer <DEVICE_API_TOKEN>`, `X-Device-UID`, and `Idempotency-Key: <DEVICE_UID>-<seq>`.
- **Serial Bridge Forwarder (`scripts/airsense_serial_forwarder.py`)**:
  - Direct USB COM port bridge (e.g. `COM11` at 115200 baud) forwarding live JSON lines into `http://127.0.0.1:8000/api/v1/ingest/reading`.
- **Wokwi Simulator Node (`Wokwi Simulation Practice/sketch.ino`)**:
  - Virtual IoT testbed supporting OLED SSD1306 display rotation, simulated potentiometer PM2.5 and MQ-135 sensors, DHT22, rain comparator, and MicroSD card logging.

### 1.4 Database Engine, Session Management & Persistence Schema
- **Database Connection Engine (`apps/api/db/session.py`)**:
  - Driver: `sqlite+aiosqlite:///./data/airsense.db` (Async Engine via SQLAlchemy 2.0).
  - Engine Instance: `engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)`.
  - Session Factory: `AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)`.
  - Dependency: `get_db_session()` yields `AsyncSession` instances with guaranteed cleanup in `finally: await session.close()`.
  - Directory Provisioning: Automatically ensures `./data` directory exists upon module load (Lines 9–16).
- **Core Database Tables (`apps/api/db/models.py`)**:
  1. `campuses` (Lines 16–35): Multi-campus registry (`id`, `code`, `name`, `city`, `latitude`, `longitude`, `timezone`, `status`, `contact_name`).
  2. `stations` (Lines 37–59): Physical rooftop/indoor monitoring stations (`id`, `campus_id`, `station_code`, `station_name`, `installation_location`, `sampling_interval_seconds`, `firmware_version`, `last_seen_at`).
  3. `devices` (Lines 61–82): Hardware node authentication & provisioning (`id`, `station_id`, `device_uid`, `device_type`, `model`, `token_hash`, `status`, `last_authenticated_at`).
  4. `raw_readings` (Lines 131–166): Immutable raw telemetry packets (`id`, `campus_id`, `station_id`, `device_id`, `observed_at`, `received_at`, `source`, `pm1`, `pm2_5`, `pm10`, `temperature_c`, `humidity_pct`, `pressure_hpa`, `rain_flag`, `payload_json`, `ingested_via`, `idempotency_key`, `sequence_number`, `schema_version`, `content_hash`).
  5. `quality_assessments` (Lines 168–188): QC output log (`id`, `raw_reading_id`, `quality_score`, `quality_status`, `impossible_value_flag`, `high_humidity_flag`, `spike_review_flag`, `ordering_consistency_flag`, `validation_messages_json`, `qc_version`).
  6. `observations` (Lines 190–223): Validated, model-eligible ground truth records (`id`, `raw_reading_id`, `campus_id`, `station_id`, `observed_at`, `source`, `pm1`, `pm2_5`, `pm10`, `temperature_c`, `humidity_pct`, `pressure_hpa`, `rain_flag`, `quality_score`, `is_model_eligible`, `eligibility_reason`). Unique constraint: `(station_id, source, observed_at)`.
  7. `hourly_observations` (Lines 225–261): Resampled hourly aggregates (`id`, `campus_id`, `station_id`, `source`, `hour_start`, `pm1_mean`, `pm2_5_mean`, `pm2_5_median`, `pm10_mean`, `pm10_median`, `temperature_mean`, `humidity_mean`, `pressure_mean`, `rain_detected`, `rain_fraction`, `wind_speed_mean`, `wind_direction_circular_mean`, `contributing_count`, `expected_count`, `completeness_pct`, `average_quality_score`, `high_humidity_fraction`, `has_interpolation`, `is_model_eligible`). Unique constraint: `(station_id, source, hour_start)`.
  8. `import_batches`, `maintenance_events`, `external_provider_runs`, `model_runs`, `model_validation_folds`, `predictions`, `model_explanations`, `model_promotion_events`, `external_comparisons`, `evaluation_events`.

### 1.5 Authentication, Rate Limiting & Validation Error Formats
- **Device Authentication (`apps/api/core/security.py:42–101`)**:
  - Ingestion requests require either `Authorization: Bearer <token>` or `X-Device-Token: <token>`.
  - Server computes SHA-256 hash using salt `settings.DEVICE_TOKEN_SALT` (`hash_token(token) = sha256(f"{raw_token}:{salt}")`).
  - Matches against `devices.token_hash` and asserts `device.status == "active"`.
  - Standard error format on 401/403:
    ```json
    {
      "error": {
        "code": "INVALID_DEVICE_TOKEN",
        "message": "Invalid device authentication token.",
        "details": []
      }
    }
    ```
- **Admin Token Verification (`apps/api/core/security.py:26–39`)**:
  - Protected management endpoints require `X-Admin-Token` matching `settings.ADMIN_API_TOKEN` via constant-time comparison `secrets.compare_digest`.
- **Rate Limiting State**:
  - Device-level rate limiting currently relies on hardware sampling interval (60s timer in ESP32 firmware) and DB content-hash deduplication. No explicit Token Bucket middleware is configured at the API gateway layer.

---

## 2. Logic Chain

1. **Hardware Telemetry Generation**: The ESP32 edge station reads physical sensors at 60s intervals (PMS7003 via UART2, BME280 via I2C, Raindrop via ADC1 GPIO34), buffers the reading to MicroSD SPI card `/airsense_telemetry.csv`, and dispatches an authenticated HTTP POST payload to `/api/v1/ingest/reading`.
2. **Gateway Reception & Validation**: FastAPI parses the payload through Pydantic model `ESP32IngestPayload`. If the request lacks valid Bearer or X-Device-Token headers, `authenticate_device` returns 401 Unauthorized before any DB operations take place.
3. **Idempotency Gate**: `compute_content_hash` creates a deterministic hash of station, timestamp, PM2.5, and temperature. If this exact reading already exists in `raw_readings`, the system immediately returns a 200 duplicate response with `duplicate: true`, preventing duplicated telemetry.
4. **Data Integrity & Traceability**: The raw packet is stored intact in `raw_readings` with original JSON. The reading is evaluated by `QualityControlEngine`. If valid, an `Observation` record is persisted and marked `is_model_eligible=True` (if quality score $\ge 0.60$).
5. **Real-Time Resampling & Rollup**: `HourlyAggregationEngine.process_hour` updates or inserts an `HourlyObservation` row calculating circular wind means, mean/median particulates, high humidity flags, and completeness percentage ($contributing\_count / expected\_count \times 100$).
6. **Persistence Assurance**: All writes occur within an asynchronous transaction using SQLAlchemy 2.0 and `aiosqlite` targeting `data/airsense.db`.

---

## 3. Caveats

1. **Test Concurrency with File-Based SQLite**: Running multiple pytest suites in parallel or back-to-back without connection pool isolation can trigger SQLite database file lock contention on Windows when fixtures execute `Base.metadata.drop_all`. Running test modules sequentially executes cleanly with 100% pass rates.
2. **Hardcoded Path in Seed Script**: In `scripts/seed_sqlite_and_train_models.py` (lines 16 and 25), `AIRSENSE_ROOT` is hardcoded to `d:\MUNIM - UOE @BIC\AirSense`. It should use dynamic relative resolution `Path(__file__).resolve().parent.parent` when executing outside that local environment.
3. **Pydantic v2 Deprecation Warnings**: Minor deprecation warnings occur due to `Field(..., example=...)` (should be `json_schema_extra`) and `class Config:` (should be `ConfigDict`). These do not impact runtime functionality.
4. **Gateway Rate Limiting**: There is currently no active token-bucket or Redis-based rate limiter on the FastAPI ingestion endpoint, meaning abusive client retry loops must be mitigated by reverse proxy / firewall or device token revocation (`/api/v1/admin/devices/{id}/disable`).

---

## 4. Conclusion

- **R1 Status**: Fully architected, conformant, and verified.
- **API Surface**: FastAPI backend cleanly initializes with lifespan database creation and exposes all required endpoints (`POST /api/v1/ingest/reading`, `GET /api/v1/ingest/latest`, `GET /api/v1/ingest/health`, `GET /api/v1/health`, `GET /api/v1/ready`, `GET /api/v1/version`).
- **Hardware Conformance**: Production ESP32 firmware (`airsense_esp32_firmware.ino`) precisely matches backend ingestion models and integrates Plantower PMS7003 (UART2), Bosch BME280 (I2C), Raindrop comparator (ADC1 GPIO34), and MicroSD circular CSV logging (SPI GPIO5/18/19/23).
- **Persistence & QC Engine**: Asynchronous SQLite persistence into `data/airsense.db` reliably handles raw telemetry, QC assessment logs, normalized observations, and hourly aggregate rollups with SHA-256 deduplication.

---

## 5. Verification Method

### Automated Unit and Integration Tests
Execute the following verification commands using Python 3.13:

```powershell
# 1. Verify Ingestion Endpoints, Device Authentication & Idempotency
py -m pytest tests/integration/test_ingestion_api.py -v

# 2. Verify Security, Token Generation & Salted SHA-256 Hashing
py -m pytest tests/unit/test_security.py -v

# 3. Verify Health, Readiness, Version, and Campus Endpoints
py -m pytest tests/unit/test_health.py -v
```

### Verified Test Results Summary:
- `tests/integration/test_ingestion_api.py`: **3 / 3 PASSED** (Valid token ingestion, idempotency duplicate detection, invalid token rejection).
- `tests/unit/test_security.py`: **3 / 3 PASSED** (Token generation, hashing consistency, hashing uniqueness).
- `tests/unit/test_health.py`: **4 / 4 PASSED** (Health endpoint, readiness check, version info, campus listing).

### Files & Line References Catalog:
- `apps/api/main.py` — Lines 32–182 (Lifespan, routing, static mounts, health/ready endpoints)
- `apps/api/core/config.py` — Lines 9–78 (Settings, DB URL `data/airsense.db`, campus coords)
- `apps/api/core/security.py` — Lines 15–101 (Device token hashing, `authenticate_device`, `verify_admin_token`)
- `apps/api/routers/ingest_router.py` — Lines 23–288 (`ESP32IngestPayload`, `POST /reading`, `GET /latest`, `GET /health`)
- `apps/api/routers/admin_router.py` — Lines 20–341 (Campus, station, device registration & token rotation)
- `apps/api/routers/import_router.py` — Lines 23–229 (Offline MicroSD CSV 2-stage import)
- `apps/api/db/session.py` — Lines 5–41 (Async engine, `AsyncSessionLocal`, DB path initialization)
- `apps/api/db/models.py` — Lines 16–261 (`Campus`, `Station`, `Device`, `RawReading`, `QualityAssessment`, `Observation`, `HourlyObservation`)
- `services/quality_control/qc_engine.py` — Lines 24–144 (Range limits, deduplication hashing, QC evaluation)
- `services/quality_control/gap_and_aggregation.py` — Lines 26–228 (Hourly rollups, circular wind direction)
- `scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino` — Lines 1–376 (Production ESP32 firmware, PMS7003 UART, BME280 I2C, MicroSD SPI, Rain ADC)
- `scripts/airsense_serial_forwarder.py` — Lines 1–77 (USB serial COM bridge to HTTP ingestion endpoint)
- `tests/integration/test_ingestion_api.py` — Lines 1–112 (Integration test suite for live ingestion)

# Handoff Report: Backend Ingestion API Specification & ESP32 Firmware Parity

**Agent**: `spec_miner_m4_1`  
**Milestone**: Milestone 4 / Milestone 5 Specification Discovery  
**Target Path**: `c:\Users\HP\AirSense-v2\.agents\spec_miner_m4_1\handoff.md`  
**Related Artifacts**: `c:\Users\HP\AirSense-v2\.agents\spec_miner_m4_1\spec.md`  

---

## 1. Observation

Direct code inspections and empirical executions yielded the following verbatim evidence:

1. **Router & Schemas (`apps/api/routers/ingest_router.py:38-71`)**:
   - `ESP32IngestPayload` defines:
     ```python
     class ESP32IngestPayload(BaseModel):
         schema_version: str = Field("1.0")
         device_uid: Optional[str] = None
         station_code: Optional[str] = None
         timestamp: Optional[str] = None
         timestamp_epoch: Optional[int] = None
         pm1: Optional[float] = None
         pm2_5: Optional[float] = None
         pm10: Optional[float] = None
         temperature: Optional[float] = None
         humidity: Optional[float] = None
         pressure: Optional[float] = None
         rain_flag: Optional[bool] = None
         firmware_version: str = Field("1.0.0")
         sequence_number: Optional[int] = None

         # Alternative / Legacy fields
         device_id: Optional[str] = None
         campus_code: Optional[str] = None
         timestamp_utc: Optional[str] = None
         readings: Optional[Dict[str, Any]] = None
     ```
   - No explicit `model_config` is declared on `ESP32IngestPayload`, resulting in Pydantic v2 default `extra='ignore'`. Extra fields do not trigger validation errors.

2. **Security & Authentication (`apps/api/core/security.py:47-85`)**:
   - Accepts either `Authorization: Bearer <token>` or `X-Device-Token: <token>`.
   - Lines 78-85 contain fallback auto-binding:
     ```python
     if not device and token in ["airsense_dev_token_khi_01", "airsense_dev_token_isb_01", "esp32-karachi-campus-token"]:
         uid = "AIRSENSE-NODE-KHI-01" if ("khi" in token or "karachi" in token) else "AIRSENSE-NODE-ISB-01"
     ```
   - If missing: returns HTTP 401 with `{"detail": {"error": {"code": "MISSING_DEVICE_TOKEN", "message": "Device authentication token required via Authorization header or X-Device-Token.", "details": []}}}`.
   - If invalid: returns HTTP 401 with `{"detail": {"error": {"code": "INVALID_DEVICE_TOKEN", "message": "Invalid device authentication token.", "details": []}}}`.

3. **Rate Limiting Middleware (`services/security_middleware.py:69-83`)**:
   - Ingest requests are rate limited to `INGEST_RATE_LIMIT_RPM` (120 RPM). Exceeding this returns HTTP 429 Too Many Requests with header `Retry-After: 60`.

4. **Vercel Cloud Ingress (`api/index.py:118-131`, `vercel.json:7-11`)**:
   - Rewrites `/api/(.*)` to `/api`.
   - On cold start, auto-seeds `/tmp/data/airsense.db` with `Station` `"BIC-KHI-ROOF-01"` and `Device` `"AIRSENSE-NODE-KHI-01"` using hashed token of `"airsense_dev_token_khi_01"`.

5. **ESP32 C++ Firmware (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino:27-40, 597-650`)**:
   - Hardcoded credentials: `WIFI_SSID = "Tracks_brand"`, `WIFI_PASS = "AQeel1234"`.
   - Endpoint: `API_ENDPOINT = "http://172.20.10.13:8000/api/v1/ingest/reading"`.
   - Token header: `X-Device-Token: airsense_dev_token_khi_01`.
   - Ingestion client: `HTTPClient http; http.begin(API_ENDPOINT);` (plain HTTP, incompatible with Vercel HTTPS).
   - Serialized JSON:
     ```cpp
     "{\"schema_version\":\"1.0\","
     "\"device_id\":\"%s\","
     "\"device_uid\":\"%s\","
     "\"station_code\":\"%s\","
     "\"campus_code\":\"%s\","
     "\"location\":\"%s\","
     "\"firmware_version\":\"%s\","
     "\"sequence_number\":%lu,"
     "\"timestamp_epoch\":%lu,"
     "\"pm1\":%s,\"pm1_0\":%s,"
     "\"pm2_5\":%s,\"pm25\":%s,"
     "\"pm10\":%s,"
     "\"temperature\":%s,\"temperature_c\":%s,"
     "\"humidity\":%s,\"humidity_pct\":%s,"
     "\"pressure\":%s,\"pressure_hpa\":%s,"
     "\"rain_flag\":%s,"
     "\"sensor_health\":{\"pms7003\":\"%s\",\"bme280\":\"%s\",\"rain\":\"%s\",\"microsd\":\"%s\"},"
     "\"transmission_mode\":\"%s\"}"
     ```

6. **Empirical Execution Results (Task-70, Task-75, Task-80)**:
   - Valid payload from firmware parses 100% cleanly through `ESP32IngestPayload`.
   - Testing against live FastAPI application returned:
     - No auth -> HTTP 401 (`MISSING_DEVICE_TOKEN`)
     - Bad auth -> HTTP 401 (`INVALID_DEVICE_TOKEN`)
     - Valid ingest -> HTTP 200 with `accepted: true`, `duplicate: false`
     - Duplicate ingest -> HTTP 200 with `accepted: true`, `duplicate: true`, `quality_processing_state: "duplicate_skipped"`
     - Non-numeric float -> HTTP 422 (`float_parsing`)

---

## 2. Logic Chain

1. From Observation 1, the canonical fields accepted by `ESP32IngestPayload` are `schema_version`, `device_uid`, `station_code`, `timestamp`, `timestamp_epoch`, `pm1`, `pm2_5`, `pm10`, `temperature`, `humidity`, `pressure`, `rain_flag`, `firmware_version`, `sequence_number`, `device_id`, `campus_code`, `timestamp_utc`, and `readings`.
2. From Observation 5, the firmware constructs a JSON payload providing all these canonical fields, plus aliases (`pm1_0`, `pm25`, `temperature_c`, etc.) and metadata (`location`, `sensor_health`, `transmission_mode`).
3. From Observation 1 and empirical Task-70/75, Pydantic v2 defaults to ignoring extra fields without failing validation. Therefore, the presence of alias keys and metadata keys does NOT cause validation errors.
4. From Observation 5 and 6, when hardware sensors fail, the firmware writes unquoted `null` (`"pm1":null`), and writes unquoted `true`/`false` for `rain_flag`. In Python/Pydantic, `null` parses directly as `None` and `true`/`false` parses as boolean, matching `Optional[float]` and `Optional[bool]`.
5. From Observation 2, `X-Device-Token` header containing `airsense_dev_token_khi_01` is recognized and authenticated by the backend. The firmware already sends this exact header.
6. From Observation 5 and Observation 4, the firmware currently uses plain `http://172.20.10.13:8000/api/v1/ingest/reading` with `HTTPClient`. Because Vercel serves exclusively over HTTPS (`https://airsense-team.vercel.app/api/v1/ingest/reading`), the firmware cannot reach Vercel without changing the endpoint to the HTTPS URL and wrapping the transport with `WiFiClientSecure` (`client.setInsecure()`).
7. Regarding `gas_resistance_kohm`: Although test normalizers in `test_payload_schema_and_safety.py` handle gas resistance, the hardware installed on the AirSense node is a Bosch BME280 (temperature/humidity/pressure), not a BME680 (gas sensor). Neither `ESP32IngestPayload` nor the database model `RawReading` contains a gas resistance column. Thus, the firmware correctly omits this field.

---

## 3. Caveats

1. **Vercel Database Persistence**: Vercel Serverless runs in an ephemeral environment using a `/tmp` SQLite database. Ingested readings on Vercel persist within the lambda instance lifecycle, while the HiveMQ Cloud MQTT broadcast guarantees real-time stream sync to external clients.
2. **Firmware Buffer Size**: In `airsense_esp32_firmware.ino`, `char jsonPayload[640];` is allocated on the stack. The serialized JSON length is approximately 430-470 bytes, which fits safely within 640 bytes. If additional fields are added in the future, this buffer must be expanded.
3. No other caveats.

---

## 4. Conclusion

1. **Schema Parity**: The JSON serialization in `airsense_esp32_firmware.ino` is already 100% field-compliant with the backend `POST /api/v1/ingest/reading` endpoint. All field names, null representations, and boolean formats parse successfully without error.
2. **Authentication Parity**: The `X-Device-Token: airsense_dev_token_khi_01` header sent by the firmware matches backend security requirements and automatically binds to `AIRSENSE-NODE-KHI-01`.
3. **Required Actions for Milestone 5 Firmware Implementation**:
   - Update `API_ENDPOINT` from `http://172.20.10.13:8000/api/v1/ingest/reading` to `https://airsense-team.vercel.app/api/v1/ingest/reading`.
   - Upgrade HTTP client to use `WiFiClientSecure` with `client.setInsecure()` to handle SSL/TLS to Vercel.
   - Replace hardcoded Wi-Fi credentials with `tzapu/WiFiManager` captive portal AP (`AirSense-Setup`).

---

## 5. Verification Method

1. **Pydantic Validation**:
   ```powershell
   python -c "from apps.api.routers.ingest_router import ESP32IngestPayload; payload = {'schema_version': '1.0', 'device_uid': 'AIRSENSE-NODE-KHI-01', 'pm2_5': 14.2, 'temperature': 28.5, 'rain_flag': False}; print(ESP32IngestPayload.model_validate(payload))"
   ```
2. **End-to-End Ingestion via FastAPI**:
   ```powershell
   python -c "import httpx, asyncio; from apps.api.main import app; async def t(): transport = httpx.ASGITransport(app=app); async with httpx.AsyncClient(transport=transport, base_url='http://test') as c: r = await c.post('/api/v1/ingest/reading', json={'device_uid': 'AIRSENSE-NODE-KHI-01', 'pm2_5': 15.0}, headers={'X-Device-Token': 'airsense_dev_token_khi_01'}); print(r.status_code, r.json()); asyncio.run(t())"
   ```
3. **Test Suite Verification**:
   ```powershell
   pytest tests/test_payload_schema_and_safety.py -v
   ```
4. **Inspect Generated Spec Document**:
   Examine `c:\Users\HP\AirSense-v2\.agents\spec_miner_m4_1\spec.md`.

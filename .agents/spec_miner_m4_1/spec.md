# AirSense-v2 Telemetry Ingestion API Specification & Firmware Compliance Report

**Document Version**: 1.0.0  
**Timestamp**: 2026-09-05T18:05:00Z  
**Author**: `spec_miner_m4_1`  
**Scope**: Ingestion API endpoint `POST /api/v1/ingest/reading`, headers, database models, Pydantic schemas, and ESP32 firmware serialization compliance (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`).

---

## 1. Executive Summary

An exhaustive inspection and empirical validation was conducted on the AirSense-v2 backend ingestion system (`apps/api/routers/ingest_router.py`, `apps/api/core/security.py`, `apps/api/db/models.py`, and `api/index.py`), together with the C++ ESP32 firmware (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`) and test suites (`tests/test_payload_schema_and_safety.py`).

Key findings:
1. **Endpoint Route**: `POST /api/v1/ingest/reading` (served locally via FastAPI and on Vercel at `https://airsense-team.vercel.app/api/v1/ingest/reading`).
2. **Payload Parsing**: Managed by Pydantic model `ESP32IngestPayload`. Unrecognized fields (e.g. `location`, `transmission_mode`, `sensor_health`, `pm1_0`, `pm25`, etc.) are safely ignored without validation errors (`extra='ignore'`).
3. **Firmware Compliance**: The JSON payload constructed in `airsense_esp32_firmware.ino` sends both canonical keys (`pm1`, `pm2_5`, `pm10`, `temperature`, `humidity`, `pressure`, `rain_flag`, `sequence_number`, `timestamp_epoch`, `device_uid`, `station_code`, `campus_code`, `firmware_version`, `schema_version`) and alias keys. It validates 100% cleanly against `ESP32IngestPayload`.
4. **Discrepancies / Gaps**:
   - **Target Endpoint & Protocol**: Firmware currently targets `http://172.20.10.13:8000/api/v1/ingest/reading` using plain HTTP `HTTPClient`. Per Milestone 5 requirements, it must be upgraded to `https://airsense-team.vercel.app/api/v1/ingest/reading` using `WiFiClientSecure` with `client.setInsecure()`.
   - **Gas Resistance**: `gas_resistance_kohm` is mentioned in test normalizers and serial bridge, but neither `ESP32IngestPayload` nor `RawReading` contains this column. The physical hardware has a BME280 sensor (temperature/humidity/pressure), not a BME680 (gas), so gas resistance is properly omitted from the firmware.
   - **Authentication**: Firmware passes header `X-Device-Token: airsense_dev_token_khi_01`. Backend explicitly accepts this and maps it to `AIRSENSE-NODE-KHI-01`.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Ingestion API | `POST /api/v1/ingest/reading` | Primary endpoint for physical and bridge ESP32 telemetry ingestion. Performs authentication, hardware sanity bounds checking, deduplication, raw preservation, quality control scoring, hourly aggregation, and cloud MQTT broadcast. | JSON body (`ESP32IngestPayload`), Header `X-Device-Token` or `Authorization`, optional `Idempotency-Key` | HTTP 200 JSON with `accepted: true`, `ingestion_id`, `request_id`, `observed_at_utc`, `quality_processing_state` | HTTP 400 (station unbound), HTTP 401 (missing/invalid token), HTTP 403 (device disabled), HTTP 422 (type validation), HTTP 429 (rate limited > 120 RPM) | `apps/api/routers/ingest_router.py:75-314` |
| 2 | Device Auth | Device Token Authentication | Verifies hardware station identity against hashed tokens in database, with fallback auto-binding for standard deployment tokens (`airsense_dev_token_khi_01`). | Header `X-Device-Token: <token>` OR `Authorization: Bearer <token>` | Injected `Device` SQLModel object with `last_authenticated_at` updated | HTTP 401 `MISSING_DEVICE_TOKEN`, HTTP 401 `INVALID_DEVICE_TOKEN`, HTTP 403 `DEVICE_DISABLED` | `apps/api/core/security.py:47-114` |
| 3 | Idempotency | Deduplication & Re-transmission Handling | Detects duplicate packets using SHA-256 `content_hash(station_code, observed_at, pm2_5, temp)`. Skips duplicate DB writes while returning HTTP 200. | Ingest JSON with identical timestamp and core metrics | HTTP 200 JSON with `duplicate: true`, `accepted: true`, `quality_processing_state: "duplicate_skipped"` | None (gracefully absorbs retransmissions) | `apps/api/routers/ingest_router.py:153-180` |
| 4 | Data Sanitization | Hardware Fault Value Filtering | Filters BME280 bus lockups (e.g. -148.5°C, < -40°C, > 85°C) and pressure/humidity anomalies before storing and running QC. | Raw floats from hardware | Sanitized float or `None` | Prevents corrupted values from polluting observations | `apps/api/routers/ingest_router.py:115-139` |
| 5 | Live Forwarding | HiveMQ Telemetry Broadcast | Automatically forwards validated readings to global HiveMQ MQTT broker (`airsense/karachi/bic_roof/telemetry`) on port 1883 for remote live dashboards. | Telemetry dictionary | MQTT publish packet | Silently suppressed on broker network failure | `apps/api/routers/ingest_router.py:23-34`, `270-289` |
| 6 | Diagnostics | Sensor Health Diagnostic API | Probes recent telemetry packets (<15s threshold) and evaluates individual chip health for PMS7003, BME280, Rainplate, and MicroSD. | `GET /api/v1/ingest/sensors/diagnostic` (optional `station_id`) | Diagnostic report JSON with `station_liveness`, chip statuses (`ONLINE`, `DEGRADED`, `OFFLINE`), pin repair tips | Returns fallback diagnostic report if no readings found | `apps/api/routers/ingest_router.py:359-394` |
| 7 | Query | Ingest Health & Latest Readings | Inspects ingestion subsystem operational state and fetches recent raw packets for session history. | `GET /api/v1/ingest/health`, `GET /api/v1/ingest/latest?limit=50` | Health status JSON / array of serialized `RawReading` objects | HTTP 500 on DB failure | `apps/api/routers/ingest_router.py:316-357` |
| 8 | Ingress | Vercel Serverless Path Normalizer & DB Bootstrap | Adapts FastAPI ASGI app to Vercel Python runtime, pre-populating `/tmp/data/airsense.db` with default station and device bindings on cold-start. | Vercel HTTP request with URL rewrite (`/api/(.*)`) | Dispatches request to FastAPI ASGI engine | Logs error and returns HTTP 500 if DB setup fails | `api/index.py:1-171` |

---

## 3. Edge Cases & Empirical Observations

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Pydantic Schema | All telemetry fields set to `null` (`pm1: null`, `temperature: null`, etc.) | Parses successfully without error (`None` for all values). Endpoint accepts packet, generates QC result with flags, stores raw reading. |
| 2 | Pydantic Schema | Coercible numeric strings (`"pm2_5": "14.5"`, `"rain_flag": "true"`, `"sequence_number": "10"`) | Pydantic cleanly coerces to `float(14.5)`, `bool(True)`, and `int(10)`. Status: HTTP 200. |
| 3 | Pydantic Schema | Non-numeric string in float field (`"pm2_5": "not_a_float"`) | FastAPI catches validation failure and immediately returns HTTP 422 Unprocessable Entity with location `["body", "pm2_5"]`. |
| 4 | Pydantic Schema | Unrecognized extra keys (`"gas_resistance_kohm": 120.5`, `"location": "ROOF"`, `"sensor_health": {...}`) | Ignored without error (`extra='ignore'`). Ingestion succeeds with HTTP 200. |
| 5 | Authentication | Missing `X-Device-Token` and `Authorization` headers | Fails immediately with HTTP 401 Unauthorized and code `MISSING_DEVICE_TOKEN`. |
| 6 | Authentication | Invalid `X-Device-Token: bad_token_123` | Fails with HTTP 401 Unauthorized and code `INVALID_DEVICE_TOKEN`. |
| 7 | Authentication | Known default token `X-Device-Token: airsense_dev_token_khi_01` | Automatically binds to `AIRSENSE-NODE-KHI-01` if not previously hashed in database. Status: HTTP 200. |
| 8 | Timestamp | ISO 8601 string timestamp (`"2026-09-05T18:00:00Z"`) | Parsed via `datetime.fromisoformat()` to UTC datetime. |
| 9 | Timestamp | Unix epoch timestamp (`"timestamp_epoch": 1757181000`) | Converted to UTC datetime via `datetime.fromtimestamp()`. |
| 10 | Timestamp | Pre-NTP epoch (< 1,000,000,000, e.g. unbooted ESP32 clock returning `123`) | Server detects invalid epoch and gracefully defaults `observed_at_utc` to current server `received_at_utc`. |
| 11 | Deduplication | Exact duplicate reading sent twice in short succession | First request returns HTTP 200 with `duplicate: false`. Second request returns HTTP 200 with `duplicate: true`, `quality_processing_state: "duplicate_skipped"`, and skips duplicate database insert. |
| 12 | Rate Limiting | More than 120 POST requests per minute from the same IP | Security middleware triggers HTTP 429 Too Many Requests with header `Retry-After: 60`. |

---

## 4. Exact Schema Specification for `POST /api/v1/ingest/reading`

### 4.1 Request Headers

| Header Name | Type | Required? | Default / Example | Notes |
|-------------|------|-----------|-------------------|-------|
| `Content-Type` | String | **Required** | `application/json` | Standard JSON MIME type required by FastAPI body parser. |
| `X-Device-Token` | String | **Conditional** | `airsense_dev_token_khi_01` | Required if `Authorization` header is not provided. |
| `Authorization` | String | **Conditional** | `Bearer airsense_dev_token_khi_01` | Required if `X-Device-Token` is not provided. |
| `Idempotency-Key` | String | Optional | `uuid4` hex or custom string | Client-provided key mapped to `RawReading.idempotency_key`. |

### 4.2 Request Body JSON Fields (`ESP32IngestPayload`)

| Field Name | JSON Type | Python / Pydantic Type | Required? | Default | Description & Constraints |
|------------|-----------|------------------------|-----------|---------|---------------------------|
| `schema_version` | String | `str` | Optional | `"1.0"` | Schema version identifier string. |
| `device_uid` | String | `Optional[str]` | Optional | `None` | Device UID (e.g. `"AIRSENSE-NODE-KHI-01"`). |
| `station_code` | String | `Optional[str]` | Optional | `None` | Station code (e.g. `"BIC-KHI-ROOF-01"`). |
| `timestamp` | String | `Optional[str]` | Optional | `None` | ISO 8601 formatted timestamp string. |
| `timestamp_epoch` | Integer | `Optional[int]` | Optional | `None` | UNIX epoch in seconds (e.g. `1757181000`). Valid if `> 1000000000`. |
| `pm1` | Float / Null | `Optional[float]` | Optional | `None` | PM1.0 particulate concentration (μg/m³). |
| `pm2_5` | Float / Null | `Optional[float]` | Optional | `None` | PM2.5 particulate concentration (μg/m³). Primary key for AQI and QC. |
| `pm10` | Float / Null | `Optional[float]` | Optional | `None` | PM10 particulate concentration (μg/m³). |
| `temperature` | Float / Null | `Optional[float]` | Optional | `None` | Ambient temperature in °C. Sanitized to `None` if `< -40.0`, `> 85.0`, or `== -148.5`. |
| `humidity` | Float / Null | `Optional[float]` | Optional | `None` | Relative humidity in %. Sanitized to `None` if `< 0.0`, `> 100.0`, or `(temp is None and hum == 0.0)`. |
| `pressure` | Float / Null | `Optional[float]` | Optional | `None` | Barometric pressure in hPa. Sanitized to `None` if `< 300.0`, `> 1200.0`, or `(temp is None and press > 1150.0)`. |
| `rain_flag` | Boolean / Null | `Optional[bool]` | Optional | `None` | Rain sensor state: `true` (wet / rain) or `false` (dry). |
| `firmware_version`| String | `str` | Optional | `"1.0.0"` | Firmware version string (e.g. `"v3.5.0-HARDENED"`). |
| `sequence_number` | Integer | `Optional[int]` | Optional | `None` | Packet sequence counter incremented per sample. |
| `device_id` | String | `Optional[str]` | Optional | `None` | Alternative / legacy alias for `device_uid`. |
| `campus_code` | String | `Optional[str]` | Optional | `None` | Alternative / legacy campus identifier (e.g. `"KARACHI"`). |
| `timestamp_utc` | String | `Optional[str]` | Optional | `None` | Alternative / legacy ISO timestamp string. |
| `readings` | Object | `Optional[Dict[str, Any]]` | Optional | `None` | Alternative nested readings dictionary (`{"pm1": ..., "pm25": ..., ...}`). |

*Note on Unrecognized Fields*: Additional keys sent in the payload (such as `location`, `pm1_0`, `pm25`, `temperature_c`, `humidity_pct`, `pressure_hpa`, `sensor_health`, `transmission_mode`) are permitted without causing HTTP 422 errors because Pydantic v2 defaults to `extra='ignore'`.

### 4.3 HTTP Response Status Codes and Bodies

#### 4.3.1 Success: 200 OK (New Telemetry Reading Accepted)
```json
{
  "request_id": "req_8f1245b65cbb",
  "ingestion_id": "0ceb70b9-16a5-4d2b-9ca8-06625ba1598d",
  "raw_reading_id": "0ceb70b9-16a5-4d2b-9ca8-06625ba1598d",
  "accepted": true,
  "duplicate": false,
  "observed_at_utc": "2026-09-05T18:03:01+00:00",
  "received_at_utc": "2026-09-05T18:03:01.593061+00:00",
  "campus_code": "KARACHI",
  "station_code": "BIC-KHI-ROOF-01",
  "quality_processing_state": "accepted",
  "server_schema_version": "1.0"
}
```

#### 4.3.2 Success: 200 OK (Idempotent Duplicate Detected)
```json
{
  "request_id": "req_0ea9c0bf9e20",
  "ingestion_id": "0ceb70b9-16a5-4d2b-9ca8-06625ba1598d",
  "raw_reading_id": "0ceb70b9-16a5-4d2b-9ca8-06625ba1598d",
  "accepted": true,
  "duplicate": true,
  "observed_at_utc": "2026-09-05T18:03:01+00:00",
  "received_at_utc": "2026-09-05T18:03:01.906595+00:00",
  "campus_code": "KARACHI",
  "station_code": "BIC-KHI-ROOF-01",
  "quality_processing_state": "duplicate_skipped",
  "server_schema_version": "1.0"
}
```

#### 4.3.3 Error: 400 Bad Request (Device Unbound to Valid Station)
```json
{
  "detail": {
    "error": {
      "code": "STATION_NOT_FOUND",
      "message": "Device not bound to a valid station.",
      "request_id": "req_1a2b3c4d5e6f"
    }
  }
}
```

#### 4.3.4 Error: 401 Unauthorized (Missing or Invalid Device Token)
- Missing Token:
```json
{
  "detail": {
    "error": {
      "code": "MISSING_DEVICE_TOKEN",
      "message": "Device authentication token required via Authorization header or X-Device-Token.",
      "details": []
    }
  }
}
```
- Invalid Token:
```json
{
  "detail": {
    "error": {
      "code": "INVALID_DEVICE_TOKEN",
      "message": "Invalid device authentication token.",
      "details": []
    }
  }
}
```

#### 4.3.5 Error: 403 Forbidden (Device Disabled or Inactive)
```json
{
  "detail": {
    "error": {
      "code": "DEVICE_DISABLED",
      "message": "Device 'AIRSENSE-NODE-KHI-01' is currently disabled.",
      "details": []
    }
  }
}
```

#### 4.3.6 Error: 422 Unprocessable Entity (Schema Validation Failure)
```json
{
  "detail": [
    {
      "type": "float_parsing",
      "loc": ["body", "pm2_5"],
      "msg": "Input should be a valid number, unable to parse string as a number",
      "input": "not_a_float"
    }
  ]
}
```

#### 4.3.7 Error: 429 Too Many Requests (Rate Limit Exceeded)
```json
{
  "detail": "Ingest rate limit exceeded. Maximum 120 requests per minute."
}
```

---

## 5. Discrepancy & Parity Analysis with `airsense_esp32_firmware.ino`

### 5.1 JSON Payload Field Comparison Table

| Field Name | In ESP32 Firmware | In Backend Schema (`ESP32IngestPayload`) | Parity Status | Resolution / Guidance |
|---|---|---|---|---|
| `schema_version` | `"1.0"` | `str = Field("1.0")` | **EXACT MATCH** | None needed. |
| `device_id` | `"AIRSENSE-NODE-KHI-01"` | `Optional[str] = None` | **EXACT MATCH** | Accepted as legacy alias. |
| `device_uid` | `"AIRSENSE-NODE-KHI-01"` | `Optional[str] = None` | **EXACT MATCH** | Matches database device record. |
| `station_code` | `"BIC-KHI-ROOF-01"` | `Optional[str] = None` | **EXACT MATCH** | Matches database station record. |
| `campus_code` | `"KARACHI"` | `Optional[str] = None` | **EXACT MATCH** | Matches database campus record. |
| `location` | `"BIC_ROOF_KARACHI"` | Not in schema | **SUPERSET** | Safely ignored by Pydantic; preserved in serial logs. |
| `firmware_version` | `"v3.5.0-HARDENED"` | `str = Field("1.0.0")` | **EXACT MATCH** | Accepted string. |
| `sequence_number` | `packet_seq` (long integer) | `Optional[int] = None` | **EXACT MATCH** | Stored in `RawReading.sequence_number`. |
| `timestamp_epoch` | `time(NULL)` (long integer) | `Optional[int] = None` | **EXACT MATCH** | Used to derive `observed_at_utc`. |
| `pm1` | `pm1_str` (float / `null`) | `Optional[float] = None` | **EXACT MATCH** | Unquoted `null` or float accepted. |
| `pm1_0` | `pm1_str` (float / `null`) | Not in schema | **SUPERSET (ALIAS)** | Redundant alias; ignored by backend. |
| `pm2_5` | `pm25_str` (float / `null`) | `Optional[float] = None` | **EXACT MATCH** | Primary key for PM2.5. |
| `pm25` | `pm25_str` (float / `null`) | Not in root schema | **SUPERSET (ALIAS)** | Redundant alias; ignored by backend. |
| `pm10` | `pm10_str` (float / `null`) | `Optional[float] = None` | **EXACT MATCH** | Primary key for PM10. |
| `temperature` | `temp_str` (float / `null`) | `Optional[float] = None` | **EXACT MATCH** | Primary key for temperature. |
| `temperature_c` | `temp_str` (float / `null`) | Not in schema | **SUPERSET (ALIAS)** | Redundant alias; ignored by backend. |
| `humidity` | `hum_str` (float / `null`) | `Optional[float] = None` | **EXACT MATCH** | Primary key for humidity. |
| `humidity_pct` | `hum_str` (float / `null`) | Not in schema | **SUPERSET (ALIAS)** | Redundant alias; ignored by backend. |
| `pressure` | `press_str` (float / `null`) | `Optional[float] = None` | **EXACT MATCH** | Primary key for pressure. |
| `pressure_hpa` | `press_str` (float / `null`) | Not in schema | **SUPERSET (ALIAS)** | Redundant alias; ignored by backend. |
| `rain_flag` | `true` / `false` (boolean) | `Optional[bool] = None` | **EXACT MATCH** | Unquoted boolean accepted. |
| `gas_resistance_kohm` | Omitted from firmware | Not in schema | **CONSISTENT** | BME280 has no gas sensor (only BME680 does). Correctly omitted. |
| `sensor_health` | Object with chip statuses | Not in schema | **SUPERSET** | Ignored by Pydantic; backend dynamically recalculates chip health in `SensorHealthEngine`. |
| `transmission_mode`| `"WIFI_DIRECT"` / `"SERIAL_BRIDGE"` | Not in schema | **SUPERSET** | Ignored by Pydantic; backend records `"esp32_http"`. |

### 5.2 Critical Inconsistencies & Required Firmware Upgrades

1. **API Endpoint & Protocol**:
   - **Current in `.ino` line 38**:
     ```cpp
     const char* API_ENDPOINT = "http://172.20.10.13:8000/api/v1/ingest/reading";
     ```
   - **Required Target**:
     ```cpp
     const char* API_ENDPOINT = "https://airsense-team.vercel.app/api/v1/ingest/reading";
     ```
   - **Reason**: The ESP32 cannot push telemetry to the live Vercel cloud dashboard if targeting an unreachable private LAN IP `172.20.10.13`.

2. **TLS / HTTPS Transport**:
   - **Current in `.ino` lines 640-650**:
     Uses plain `HTTPClient http; http.begin(API_ENDPOINT);` which cannot perform TLS handshakes with Vercel's HTTPS endpoint.
   - **Required Fix**:
     Include `<WiFiClientSecure.h>`, instantiate `WiFiClientSecure client; client.setInsecure();`, and pass `client` into `http.begin(client, API_ENDPOINT);` to allow direct secure ingestion without CA certificate pinning overhead.

3. **Static Credentials vs WiFiManager**:
   - **Current in `.ino` lines 27-28**:
     Hardcoded `WIFI_SSID` ("Tracks_brand") and `WIFI_PASS` ("AQeel1234").
   - **Required Fix**:
     Replace with `tzapu/WiFiManager` captive portal auto-connect flow (`AirSense-Setup` AP), eliminating hardcoded Wi-Fi credentials.

---

## 6. Recommendations for Milestone 5 Workers

1. **Keep the Dual-Key JSON Payload**: The current `snprintf` in the firmware provides both canonical keys (`pm2_5`, `temperature`, `humidity`, `pressure`) and alias keys (`pm25`, `temperature_c`, etc.). This guarantees zero regressions across both the FastAPI backend and any existing Python bridge parsers.
2. **Preserve `null` and Boolean Formatting**: Ensure `pm1_str`, etc. remain serialized as unquoted `null` when sensors fail, and `rain_flag` remains serialized as unquoted `true` / `false`.
3. **Upgrade Ingestion Client to `WiFiClientSecure`**:
   ```cpp
   #include <WiFiClientSecure.h>
   ...
   WiFiClientSecure secureClient;
   secureClient.setInsecure();
   HTTPClient http;
   http.begin(secureClient, API_ENDPOINT);
   http.setTimeout(4000); // Allow reasonable TLS handshake time
   http.addHeader("Content-Type", "application/json");
   http.addHeader("X-Device-Token", DEVICE_TOKEN);
   int httpResponseCode = http.POST(jsonPayload);
   ```
4. **Token Preservation**: Maintain `DEVICE_TOKEN = "airsense_dev_token_khi_01";` because it is pre-configured and auto-bound to `AIRSENSE-NODE-KHI-01` in the Vercel bootstrap layer (`api/index.py`).

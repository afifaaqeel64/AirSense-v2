# AirSense-v2 Hardware Serial Bridge & E2E Verification Test Suite Survey Report

**Agent**: `explorer_survey_bridge_tests_1`  
**Parent**: `orchestrator_3` (Conversation ID: `d855ea29-0400-4419-801f-9d26248c059f`)  
**Mission**: Survey the hardware serial bridge (`scripts/airsense_serial_live_bridge.py`, etc.) and E2E verification test suites (`tests/`), identifying dual-routing mechanisms to local and live public HTTPS endpoints, HTTPS endpoint verification harness requirements, and bridge packet forwarding verification methodology.

---

## 1. Observation

### 1.1 Hardware Serial Bridge Architecture (`scripts/airsense_serial_live_bridge.py`)
- **Port Discovery & Serial Acquisition** (lines 119-156, 396-413):
  - `scan_available_ports()` filters out virtual Bluetooth serial ports (`"bluetooth"`, `"bthenum"`, `"bth\"`) and ranks ports by keyword matching (`cp210`, `ch340`, `ch9102`, `ftdi`, `silicon labs`, `wch`, `espressif`, `usb to uart`, `uart`).
  - `find_esp32_port(preferred_port)` prioritizes explicit CLI arguments (e.g. `COM7`) while falling back to dynamic port detection.
  - `run_bridge()` creates `serial.Serial(current_port, baudrate=115200, timeout=2.0)` inside an auto-recovery loop with exponential backoff (1.0s to 8.0s) and jitter.
- **Dual Parser & Normalization** (lines 175-369):
  - Structured JSON Line Parser: Extracts `[JSON_TELEMETRY] {...}` or bare JSON `{...}` directly.
  - Fallback ASCII Regex Parser: Extracts regex patterns for PMS7003 (`PM1.0: ... | PM2.5: ... | PM10: ...`), BME280 (`Temp: ... | Hum: ... | Press: ...`), Gas resistance, and Rain plate (`Raw ADC: ...`, `Rain: YES/Wet/Dry`).
  - `build_telemetry_payload()` normalizes readings, clamps physical particulate bounds, identifies degraded/frozen sensor states (`DEGRADED_FROZEN` if 29.5°C, 65% RH, 1012 hPa), and tags packet with `transmission_mode="SERIAL_BRIDGE"`.
- **Current Forwarding Pipeline** (lines 28-32, 159-173, 428-450):
  ```python
  API_ENDPOINT = "http://127.0.0.1:8000/api/v1/ingest/reading"
  HEADERS = {
      "Content-Type": "application/json",
      "X-Device-Token": "airsense_dev_token_khi_01"
  }
  ```
  - Ingestion call: `push_to_local_api(payload)` executes a synchronous `urllib.request.urlopen` against `API_ENDPOINT` with a 2.0s timeout.
  - Dual MQTT publisher: `DualBrokerMqttPublisher` connects to HiveMQ (`broker.hivemq.com:1883`) and EMQX (`broker.emqx.io:1883`), publishing to `airsense/karachi/bic_roof/telemetry` and `airsense/telemetry`.
  - **Limitation**: Currently hardcoded to `http://127.0.0.1:8000`. No public HTTPS endpoint configuration exists in the bridge script, and no dual-routing mechanism is implemented to forward packets simultaneously to both local and live cloud backends.

### 1.2 Inspection of the 5 Production Endpoints
The 5 required production endpoints were located in the codebase:
1. `GET /api/v1/health/liveness` (`apps/api/main.py:257-266`):
   - Returns HTTP 200: `{"status": "healthy", "process": "running", "environment": "production", "timestamp_utc": "...", "display_timezone": "Asia/Karachi"}`.
   - Public, requires no authentication.
2. `GET /api/v1/health/readiness` (`apps/api/main.py:270-333`):
   - Probes database (`SELECT 1`), disk writability (`./data/backups/.healthcheck_write_test`), background scheduler status, and campus pilots.
   - Returns HTTP 200 with `status: "ready"` (or HTTP 503 if degraded).
   - Public, requires no authentication.
3. `POST /api/v1/ingest/reading` (`apps/api/routers/ingest_router.py:75-240`):
   - Accepts `ESP32IngestPayload`. Protected by `authenticate_device` (`apps/api/core/security.py:47-105`).
   - Accepts `X-Device-Token: airsense_dev_token_khi_01` (or `Authorization: Bearer <token>`).
   - Automatically auto-binds standard dev/deploy tokens to `AIRSENSE-NODE-KHI-01`.
   - Returns HTTP 200/201: `{"accepted": true, "ingestion_id": "...", "received_at_utc": "...", "station_code": "BIC-KHI-ROOF-01", "duplicate": false, "quality_processing_state": "..."}`.
4. `GET /api/v1/ingest/sensors/diagnostic` (`apps/api/routers/ingest_router.py:359-394`):
   - Evaluates latest sensor telemetry using `SensorHealthEngine.evaluate_sensor_connectivity()`.
   - Returns HTTP 200: `{"overall_state": "LIVE_ACTIVE"|"OFFLINE"|"PARTIAL_DEGRADED", "sensors": {"pms7003": ..., "bme280": ..., "rainplate": ..., "microsd": ...}, "heartbeat": {"seconds_since_last_packet": ..., "is_alive": ...}}`.
   - Public, requires no authentication.
5. `GET /api/v1/providers/weather/telemetry-feed` (`apps/api/routers/provider_router.py:285-307`):
   - Parameters: `limit` (int, default 30), `force_refresh` (bool), `latitude` (float, default 24.8607), `longitude` (float, default 67.0011).
   - Generates/returns 60-second cadence continuous meteorological observations.
   - Returns HTTP 200: `{"status": "success", "cadence_seconds": 60, "server_time_utc": "...", "current_metrics": {...}, "records": [...]}`.
   - Public, requires no authentication.

### 1.3 Inspection of Existing Test Suites (`tests/`)
- Total test count: **285 tests collected** across unit, integration, and e2e test directories.
- `tests/unit/test_production_readiness.py`: Tests liveness, readiness, security headers, metrics, and rate limiting using `fastapi.testclient.TestClient(app)`.
- `tests/integration/test_ingestion_api.py`: Tests `/api/v1/ingest/reading` using `httpx.AsyncClient(transport=ASGITransport(app=app))`.
- `tests/e2e/test_dual_dashboards_e2e.py`: Tests `/api/v1/ingest/sensors/diagnostic` and multi-provider comparisons using `ASGITransport(app=app)`.
- `tests/test_bridge_resilience.py` & `tests/test_challenger_bridge_adversarial.py`: Tests COM scanning, reconnection loops, mock serial parsing, and MQTT publisher isolation using `unittest.mock`.
- **Key Observation & Gap**:
  1. All 285 tests execute in-process via ASGI transport or TestClient. **Zero tests execute over real network sockets or public HTTPS URLs.**
  2. `/api/v1/providers/weather/telemetry-feed` is **not tested anywhere** in `tests/`.

---

## 2. Logic Chain

### 2.1 Dual-Routing Architectural Requirement
1. Physical ESP32 hardware transmits telemetry via USB serial (COM port) to the laptop running `airsense_serial_live_bridge.py`.
2. When the backend is deployed to a public cloud platform (e.g. Render at `https://airsense-api.onrender.com` or custom HTTPS domain), the web dashboard (`https://airsense-team.vercel.app` or cloud `/ops`) requires data posted to the cloud endpoint.
3. At the same time, local edge analysis, local dashboards (`http://127.0.0.1:8000/ops`), and local SQLite records must continue to receive telemetry without interruption.
4. Serial packet arrival rate is ~1 packet every 1-3 seconds. An external HTTPS round-trip to a cloud server (e.g. Singapore region) typically takes 150-500 ms, with potential multi-second spikes or timeouts if cloud connectivity fluctuates.
5. If the bridge calls the cloud HTTPS endpoint synchronously in the main serial thread:
   - A network lag or TLS timeout (2-5s) will block the serial loop.
   - Serial input buffers on Windows COM ports will accumulate unread bytes, causing buffer overflows or stale readings.
6. **Therefore**: Dual-routing MUST be architected with:
   - Dynamic configuration: Local URL (`AIRSENSE_LOCAL_API_URL`), Cloud URL (`AIRSENSE_CLOUD_API_URL` or `--cloud-url` CLI flag), and Device Token (`AIRSENSE_DEVICE_TOKEN`).
   - Fault isolation: Local server downtime must never block cloud transmission; cloud network failure must never drop local ingestion.
   - Non-blocking execution: A lightweight thread pool (`ThreadPoolExecutor(max_workers=2)`) or fast asynchronous non-blocking worker threads to dispatch both HTTP requests concurrently with strict timeouts (<= 2.5s).

### 2.2 Live Public HTTPS Test Harness Requirement
1. In-process tests (`ASGITransport`) bypass DNS, TLS handshakes, reverse proxy routing, network firewalls, and HTTP keepalive behaviors.
2. In production, Render provisions a public HTTPS domain (e.g. `https://airsense-api.onrender.com`).
3. To rigorously verify deployment health:
   - A dedicated test harness (`scripts/verify_live_endpoints.py` / `tests/e2e/test_live_public_endpoints.py`) must send genuine HTTPS requests via `httpx.Client(verify=True)` to the target public URL.
   - It must systematically validate all 5 endpoints in dependency order:
     `Liveness (HTTP 200)` -> `Readiness (HTTP 200, DB connected)` -> `Telemetry Feed (HTTP 200, records present)` -> `Ingest Reading (HTTP 200, accepted)` -> `Sensor Diagnostic (HTTP 200, station active)`.

### 2.3 Bridge Packet Forwarding Verification Methodology
1. A physical ESP32 cannot be assumed present in CI or automated verification environments.
2. An effective verification method must validate the complete pipeline:
   `Simulated UART Stream -> Bridge Parser -> Payload Builder -> Dual Dispatcher -> Live Cloud HTTPS Response`.
3. By feeding a synthetic serial packet with an incremented sequence number through the bridge's ingestion engine, and immediately querying `GET /api/v1/ingest/sensors/diagnostic` on the public HTTPS endpoint, we can deterministically assert that:
   - The packet reached the cloud database.
   - The station transition state became `LIVE_ACTIVE`.
   - The sequence number recorded in the cloud matches the synthetic packet.

---

## 3. Caveats

1. **Render Free-Tier Spin-Down / Cold Start**:
   - Render free-tier web services spin down after 15 minutes of inactivity. Initial HTTPS requests to a dormant service may take 30-50 seconds to respond. The live test harness must include a pre-flight warm-up probe with an extended initial timeout (60s) before executing tight-timeout assertions.
2. **Device Token Salt in Cloud Environment**:
   - `render.yaml` sets `DEVICE_TOKEN_SALT: generateValue: true`.
   - However, `apps/api/core/security.py:78-85` includes fallback auto-binding for `"airsense_dev_token_khi_01"`. When this token is presented, the server automatically maps and updates the token hash in PostgreSQL for device `AIRSENSE-NODE-KHI-01`. Thus, standard tokens work reliably across deployments.
3. **No Code Modifications Made**:
   - As an explorer agent operating in read-only mode, no production source files (`scripts/airsense_serial_live_bridge.py`, `tests/`) have been modified in this survey. All proposed implementations below are ready for the implementer agent.

---

## 4. Conclusion & Actionable Blueprint

### 4.1 Implementation Blueprint for Dual-Routing in `scripts/airsense_serial_live_bridge.py`

#### A. Configuration & Target Endpoints
Add environment variable and CLI argument handling at the top of `scripts/airsense_serial_live_bridge.py`:

```python
import os
from concurrent.futures import ThreadPoolExecutor

# Dual-Routing Target Endpoints
LOCAL_API_ENDPOINT = os.getenv("AIRSENSE_LOCAL_API_URL", "http://127.0.0.1:8000/api/v1/ingest/reading")
CLOUD_API_ENDPOINT = os.getenv("AIRSENSE_CLOUD_API_URL", None)  # e.g., "https://airsense-api.onrender.com/api/v1/ingest/reading"

DEVICE_AUTH_TOKEN = os.getenv("AIRSENSE_DEVICE_TOKEN", "airsense_dev_token_khi_01")
HEADERS = {
    "Content-Type": "application/json",
    "X-Device-Token": DEVICE_AUTH_TOKEN
}

# Dedicated ThreadPool for non-blocking HTTP dispatch
http_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="AirSense-HttpPush")
```

#### B. Resilient HTTP Push Function
```python
def push_to_endpoint(url: str, payload: dict, label: str = "HTTP") -> bool:
    """Dispatches payload to a specific HTTP/HTTPS endpoint with fast timeout and error containment."""
    if not url:
        return False
    try:
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            if resp.status in (200, 201):
                return True
            else:
                print(f"[{label} WARN] Unexpected HTTP {resp.status} from {url}")
                return False
    except urllib.error.HTTPError as he:
        print(f"[{label} HTTP ERROR] {he.code} {he.reason} -> {url}")
        return False
    except Exception as ex:
        # Non-fatal: do not crash bridge if target is offline or network drops
        return False

def push_telemetry_dual_async(payload: dict):
    """Submits dual HTTP ingestion tasks to background thread pool, preventing serial loop blocking."""
    # 1. Local backend dispatch
    if LOCAL_API_ENDPOINT:
        http_pool.submit(push_to_endpoint, LOCAL_API_ENDPOINT, payload, "LOCAL INGEST")
    # 2. Live Cloud HTTPS backend dispatch
    if CLOUD_API_ENDPOINT:
        http_pool.submit(push_to_endpoint, CLOUD_API_ENDPOINT, payload, "CLOUD INGEST")
```

#### C. CLI Argument Integration in `run_bridge()`
Update the CLI parser to accept `--cloud-url` or `--cloud`:
```python
# In main block:
parser = argparse.ArgumentParser(description="AirSense USB Serial Live Bridge")
parser.add_argument("port", nargs="?", default="AUTO", help="COM port (e.g. COM7 or AUTO)")
parser.add_argument("--cloud-url", default=os.getenv("AIRSENSE_CLOUD_API_URL"), help="Public Cloud Ingestion Endpoint")
```

---

### 4.2 Production Live HTTPS Test Harness Blueprint (`scripts/verify_live_endpoints.py`)

A complete, self-contained verification script to validate all 5 endpoints against any public HTTPS URL:

```python
"""AirSense Pakistan - Live Public HTTPS End-to-End Verification Suite.
Validates all 5 production endpoints against live cloud infrastructure.
"""

import sys
import time
import json
import httpx

DEFAULT_PUBLIC_URL = "https://airsense-api.onrender.com"
DEVICE_TOKEN = "airsense_dev_token_khi_01"

def run_live_verification(base_url: str):
    base_url = base_url.rstrip("/")
    print("=" * 70)
    print(f"  AirSense Pakistan: Live HTTPS E2E Endpoint Verification")
    print(f"  Target Base URL: {base_url}")
    print("=" * 70)

    results = []

    with httpx.Client(timeout=30.0, follow_redirects=True, verify=True) as client:
        # --- Pre-flight Warm-up (Handles Render Cold-Start) ---
        print("\n[0/5] Warming up target public cloud instance...")
        try:
            t0 = time.time()
            warm = client.get(f"{base_url}/api/v1/health/liveness", timeout=60.0)
            elapsed = (time.time() - t0) * 1000
            print(f"      Cloud instance responsive! (HTTP {warm.status_code}, {elapsed:.0f}ms)")
        except Exception as e:
            print(f"      [WARN] Warm-up probe encountered: {e}")

        # --- Test 1: Liveness Probe ---
        print("\n[1/5] Testing GET /api/v1/health/liveness...")
        t0 = time.time()
        res1 = client.get(f"{base_url}/api/v1/health/liveness")
        lat1 = (time.time() - t0) * 1000
        ok1 = res1.status_code == 200 and res1.json().get("status") == "healthy"
        results.append(("1. Liveness Probe", res1.status_code, f"{lat1:.1f}ms", "PASS" if ok1 else "FAIL"))
        print(f"      Response: HTTP {res1.status_code} | Latency: {lat1:.1f}ms | Status: {res1.json().get('status')}")

        # --- Test 2: Readiness Probe ---
        print("\n[2/5] Testing GET /api/v1/health/readiness...")
        t0 = time.time()
        res2 = client.get(f"{base_url}/api/v1/health/readiness")
        lat2 = (time.time() - t0) * 1000
        data2 = res2.json() if res2.status_code == 200 else {}
        db_connected = data2.get("database", {}).get("connected", False)
        sched_running = data2.get("background_scheduler", {}).get("running", False)
        ok2 = res2.status_code == 200 and data2.get("status") == "ready" and db_connected
        results.append(("2. Readiness Probe", res2.status_code, f"{lat2:.1f}ms", "PASS" if ok2 else "FAIL"))
        print(f"      Response: HTTP {res2.status_code} | DB: {'CONNECTED' if db_connected else 'FAIL'} | Scheduler: {'RUNNING' if sched_running else 'STOPPED'}")

        # --- Test 3: Telemetry Feed ---
        print("\n[3/5] Testing GET /api/v1/providers/weather/telemetry-feed...")
        t0 = time.time()
        res3 = client.get(f"{base_url}/api/v1/providers/weather/telemetry-feed", params={"limit": 5, "latitude": 24.8607, "longitude": 67.0011})
        lat3 = (time.time() - t0) * 1000
        data3 = res3.json() if res3.status_code == 200 else {}
        records = data3.get("records", [])
        ok3 = res3.status_code == 200 and len(records) > 0
        results.append(("3. Telemetry Feed", res3.status_code, f"{lat3:.1f}ms", "PASS" if ok3 else "FAIL"))
        print(f"      Response: HTTP {res3.status_code} | Records: {len(records)} | Cadence: {data3.get('cadence_seconds')}s")

        # --- Test 4: Live Ingest Reading ---
        print("\n[4/5] Testing POST /api/v1/ingest/reading...")
        seq = int(time.time()) % 100000
        test_payload = {
            "schema_version": "1.0",
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "station_code": "BIC-KHI-ROOF-01",
            "campus_code": "KARACHI",
            "sequence_number": seq,
            "timestamp_epoch": int(time.time()),
            "pm1": 8.5,
            "pm2_5": 16.2,
            "pm10": 24.1,
            "temperature": 30.5,
            "humidity": 63.0,
            "pressure": 1011.8,
            "gas_resistance_kohm": 46.2,
            "rain_flag": False,
            "sensor_health": {"pms7003": "OK", "bme280": "OK", "rain": "OK"},
            "firmware_version": "v3.5.0-PROD-VERIFY",
            "transmission_mode": "E2E_VERIFICATION_HARNESS"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Device-Token": DEVICE_TOKEN
        }
        t0 = time.time()
        res4 = client.post(f"{base_url}/api/v1/ingest/reading", json=test_payload, headers=headers)
        lat4 = (time.time() - t0) * 1000
        data4 = res4.json() if res4.status_code in (200, 201) else {}
        ok4 = res4.status_code in (200, 201) and data4.get("accepted") is True
        results.append(("4. Ingest Reading", res4.status_code, f"{lat4:.1f}ms", "PASS" if ok4 else "FAIL"))
        print(f"      Response: HTTP {res4.status_code} | Ingestion ID: {data4.get('ingestion_id')} | QC: {data4.get('quality_processing_state')}")

        # --- Test 5: Sensor Health Diagnostic Status ---
        print("\n[5/5] Testing GET /api/v1/ingest/sensors/diagnostic...")
        t0 = time.time()
        res5 = client.get(f"{base_url}/api/v1/ingest/sensors/diagnostic")
        lat5 = (time.time() - t0) * 1000
        data5 = res5.json() if res5.status_code == 200 else {}
        stn_state = data5.get("overall_state")
        is_live = data5.get("heartbeat", {}).get("is_alive", False)
        ok5 = res5.status_code == 200 and stn_state in ("LIVE_ACTIVE", "PARTIAL_DEGRADED", "ONLINE")
        results.append(("5. Sensor Diagnostics", res5.status_code, f"{lat5:.1f}ms", "PASS" if ok5 else "FAIL"))
        print(f"      Response: HTTP {res5.status_code} | Station State: {stn_state} | Alive: {is_live}")

    # --- Summary Table ---
    print("\n" + "=" * 70)
    print("  AIRSENSE LIVE PUBLIC HTTPS VERIFICATION SUMMARY")
    print("=" * 70)
    print(f" {'Endpoint / Probe':<30} | {'Status':<8} | {'Latency':<10} | {'Result':<6}")
    print("-" * 70)
    all_passed = True
    for name, code, lat, res in results:
        print(f" {name:<30} | HTTP {code:<3} | {lat:<10} | {res:<6}")
        if res != "PASS":
            all_passed = False
    print("=" * 70)
    return all_passed
```

---

### 4.3 Hardware Serial Bridge Packet Forwarding Verification Method

To verify packet forwarding without requiring a live physical ESP32 breadboard:

1. **Synthetic Bridge Ingestion Simulation**:
   - Write a dedicated Pytest file `tests/integration/test_serial_bridge_dual_routing.py` that mocks `serial.Serial` to emit 1 structured JSON packet (`[JSON_TELEMETRY] {...}`) and 1 ASCII multi-line cycle (`PM1.0: ...`).
   - Mock `urllib.request.urlopen` or spawn two lightweight HTTP servers (local and cloud mock).
   - Assert both endpoints receive the exact same payload with `X-Device-Token`.
2. **Live Cloud Forwarding Verification**:
   - Execute synthetic transmission via bridge logic:
     `py scripts/airsense_serial_live_bridge.py SIMULATE --cloud-url https://<public-url>/api/v1/ingest/reading`
   - Immediately verify cloud response via `GET /api/v1/ingest/sensors/diagnostic`.

---

## 5. Verification Method

### 5.1 Project Test Command
To verify existing test suite integrity:
```powershell
py -m pytest tests/unit/test_production_readiness.py tests/integration/test_ingestion_api.py -v
```

### 5.2 Verification Commands for the Implementer
1. **Verify bridge dual-routing**:
   ```powershell
   py -m pytest tests/test_bridge_resilience.py -k "push_to_local_api or DualBroker" -v
   ```
2. **Verify live public HTTPS endpoints**:
   ```powershell
   py scripts/verify_live_endpoints.py https://airsense-api.onrender.com
   ```
3. **Verify sensor diagnostic transition**:
   ```powershell
   curl.exe -s "https://airsense-api.onrender.com/api/v1/ingest/sensors/diagnostic" | jq .
   ```

### 5.3 Invalidation Conditions
- If Render free-tier domain is inaccessible (DNS failure or suspended account).
- If `DATABASE_URL` is unconfigured on Render causing `/api/v1/health/readiness` to return HTTP 503.
- If `X-Device-Token` fails authentication due to unseeded device records in the cloud PostgreSQL database.

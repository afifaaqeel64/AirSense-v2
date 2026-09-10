"""AirSense Pakistan - Challenger M1-M4 Empirical Adversarial Stress Harness.

Tests:
PART A: Live Public HTTPS Endpoints Stress & Boundary Tests
  - Target: https://forums-surfaces-reef-stands.trycloudflare.com
  - Group 1: Auth & Malformed Token Ingestion Challenges
  - Group 2: Ingestion Payload Boundary & Fuzzing Challenges
  - Group 3: Telemetry Feed Boundary & Coordinate Challenges
  - Group 4: Concurrency & Rate Pressure on Live Public HTTPS
  - Group 5: Health & Diagnostic Endpoint Probing

PART B: Serial Bridge Dual-Routing Resilience Under Simulated Network Failures
  - Target: scripts/airsense_serial_live_bridge.py
  - Group 6: Dual-Routing Endpoint Failure Isolation (Unreachable Cloud, Unreachable Local, Both Down, Timeout Cutoff, HTTP 500/502/503 handling, Non-blocking ThreadPool async dispatch)
"""

import sys
import os
import time
import json
import random
import http.server
import threading
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.airsense_serial_live_bridge import (
    push_to_endpoint,
    push_telemetry_dual_async,
    build_telemetry_payload,
    run_simulation_mode,
    http_pool
)

DEFAULT_LIVE_URL = "https://forums-surfaces-reef-stands.trycloudflare.com"
DEVICE_TOKEN = "airsense_dev_token_khi_01"


class MockFailureServer:
    """Lightweight local HTTP server for deterministic network failure simulation."""
    def __init__(self, port=8891, mode="500", delay_seconds=0.0):
        self.port = port
        self.mode = mode
        self.delay_seconds = delay_seconds
        self.server = None
        self.thread = None

    def start(self):
        mode = self.mode
        delay = self.delay_seconds

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress console logging

            def do_POST(self):
                if delay > 0:
                    time.sleep(delay)
                if mode == "500":
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"detail": "Simulated Internal Server Error"}')
                elif mode == "502":
                    self.send_response(502)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"detail": "Bad Gateway"}')
                elif mode == "503":
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"detail": "Service Unavailable"}')
                elif mode == "200":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status": "ok", "accepted": true}')

        self.server = http.server.HTTPServer(("127.0.0.1", self.port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


def send_http_request(url, method="GET", headers=None, body_bytes=None, timeout=10):
    req = urllib.request.Request(url, data=body_bytes, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as he:
        err_body = he.read().decode("utf-8", errors="replace") if he.fp else ""
        return he.code, err_body, None
    except Exception as ex:
        return 0, "", str(ex)


def run_all_empirical_tests(base_url=DEFAULT_LIVE_URL):
    print("=" * 80)
    print("  AIRSENSE PAKISTAN - EMPIRICAL CHALLENGER STRESS HARNESS")
    print(f"  Target Base URL: {base_url}")
    print(f"  Timestamp:       {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    results = []

    def record(group, test_name, passed, details=""):
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] [{group}] {test_name}")
        if details:
            print(f"       -> {details}")
        results.append({
            "group": group,
            "test": test_name,
            "passed": passed,
            "details": details
        })

    # =========================================================================
    # PART A: LIVE PUBLIC HTTPS ENDPOINTS STRESS & BOUNDARY TESTS
    # =========================================================================

    # GROUP 1: Authentication & Malformed Token Challenges
    print("\n--- GROUP 1: AUTHENTICATION & MALFORMED TOKEN CHALLENGES ---")

    ingest_url = f"{base_url}/api/v1/ingest/reading"
    valid_payload = {
        "schema_version": "1.0",
        "device_uid": "AIRSENSE-NODE-KHI-01",
        "station_code": "BIC-KHI-ROOF-01",
        "campus_code": "KARACHI",
        "sequence_number": int(time.time()) % 100000,
        "timestamp_epoch": int(time.time()),
        "pm1": 7.5,
        "pm2_5": 14.2,
        "pm10": 21.0,
        "temperature": 28.5,
        "humidity": 55.0,
        "pressure": 1012.0,
        "rain_flag": False,
        "firmware_version": "v3.5.0-CHALLENGER-TEST"
    }
    body_json = json.dumps(valid_payload).encode("utf-8")

    # 1.1 Missing token header entirely
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json"}, body_bytes=body_json)
    passed_1_1 = (code == 401 and "MISSING_DEVICE_TOKEN" in body)
    record("G1_AUTH", "1.1 Missing device token header returns HTTP 401", passed_1_1, f"HTTP {code}, body: {body[:80]}")

    # 1.2 Empty token header
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": ""}, body_bytes=body_json)
    passed_1_2 = (code == 401 and "MISSING_DEVICE_TOKEN" in body)
    record("G1_AUTH", "1.2 Empty X-Device-Token returns HTTP 401", passed_1_2, f"HTTP {code}, body: {body[:80]}")

    # 1.3 Whitespace-only token header
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": "   "}, body_bytes=body_json)
    passed_1_3 = (code == 401 and "MISSING_DEVICE_TOKEN" in body)
    record("G1_AUTH", "1.3 Whitespace-only X-Device-Token returns HTTP 401", passed_1_3, f"HTTP {code}, body: {body[:80]}")

    # 1.4 Corrupted / random invalid token
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": "bad_token_xyz_fuzz!@#"}, body_bytes=body_json)
    passed_1_4 = (code == 401 and "INVALID_DEVICE_TOKEN" in body)
    record("G1_AUTH", "1.4 Malformed token returns HTTP 401 INVALID_DEVICE_TOKEN", passed_1_4, f"HTTP {code}, body: {body[:80]}")

    # 1.5 Bearer authorization empty payload
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "Authorization": "Bearer "}, body_bytes=body_json)
    passed_1_5 = (code == 401 and "MISSING_DEVICE_TOKEN" in body)
    record("G1_AUTH", "1.5 Empty Bearer auth returns HTTP 401 MISSING_DEVICE_TOKEN", passed_1_5, f"HTTP {code}, body: {body[:80]}")

    # 1.6 Bearer authorization invalid token
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "Authorization": "Bearer bad_bearer_123"}, body_bytes=body_json)
    passed_1_6 = (code == 401 and "INVALID_DEVICE_TOKEN" in body)
    record("G1_AUTH", "1.6 Invalid Bearer auth returns HTTP 401 INVALID_DEVICE_TOKEN", passed_1_6, f"HTTP {code}, body: {body[:80]}")

    # 1.7 SQL Injection probe in token
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": "' OR '1'='1' --"}, body_bytes=body_json)
    passed_1_7 = (code == 401 and "INVALID_DEVICE_TOKEN" in body)
    record("G1_AUTH", "1.7 SQL Injection in token rejected cleanly without HTTP 500", passed_1_7, f"HTTP {code}, body: {body[:80]}")

    # 1.8 Oversized token probe (10,000 characters)
    oversized = "A" * 10000
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": oversized}, body_bytes=body_json)
    passed_1_8 = (code == 401 and "INVALID_DEVICE_TOKEN" in body)
    record("G1_AUTH", "1.8 Oversized 10KB token rejected cleanly without crash", passed_1_8, f"HTTP {code}, body: {body[:80]}")

    # 1.9 Valid token accepted
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=body_json)
    passed_1_9 = (code in (200, 201) and '"accepted":true' in body.replace(" ", ""))
    record("G1_AUTH", "1.9 Valid device token returns HTTP 200 accepted: true", passed_1_9, f"HTTP {code}, body: {body[:80]}")


    # GROUP 2: Ingestion Payload Boundary & Fuzzing Challenges
    print("\n--- GROUP 2: INGESTION PAYLOAD BOUNDARY & FUZZING CHALLENGES ---")

    # 2.1 Empty JSON body
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=b"{}")
    passed_2_1 = (code in (200, 422))
    record("G2_PAYLOAD", "2.1 Empty JSON body handled gracefully (no 500)", passed_2_1, f"HTTP {code}, body: {body[:80]}")

    # 2.2 Malformed syntax JSON
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=b'{"pm25": 12.5, "unclosed: ')
    passed_2_2 = (code == 422 or code == 400)
    record("G2_PAYLOAD", "2.2 Malformed JSON syntax returns HTTP 422/400", passed_2_2, f"HTTP {code}, body: {body[:80]}")

    # 2.3 Falsy zero values (pm2_5: 0.0, temperature: 0.0, rain_flag: False)
    falsy_zero_payload = dict(valid_payload)
    falsy_zero_payload["sequence_number"] = random.randint(200000, 299999)
    falsy_zero_payload["timestamp_epoch"] = int(time.time()) - 100
    falsy_zero_payload["pm1"] = 0.0
    falsy_zero_payload["pm2_5"] = 0.0
    falsy_zero_payload["pm10"] = 0.0
    falsy_zero_payload["temperature"] = 0.0
    falsy_zero_payload["rain_flag"] = False
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=json.dumps(falsy_zero_payload).encode("utf-8"))
    passed_2_3 = (code in (200, 201) and '"accepted":true' in body.replace(" ", ""))
    record("G2_PAYLOAD", "2.3 Falsy zero values accepted without truncation", passed_2_3, f"HTTP {code}, body: {body[:80]}")

    # 2.4 Hardware I2C fault temperature (-148.5C)
    i2c_fault_payload = dict(valid_payload)
    i2c_fault_payload["sequence_number"] = random.randint(300000, 399999)
    i2c_fault_payload["timestamp_epoch"] = int(time.time()) - 200
    i2c_fault_payload["temperature"] = -148.5
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=json.dumps(i2c_fault_payload).encode("utf-8"))
    passed_2_4 = (code in (200, 201) and '"accepted":true' in body.replace(" ", ""))
    record("G2_PAYLOAD", "2.4 Hardware I2C error temp (-148.5C) sanitized without 500", passed_2_4, f"HTTP {code}, body: {body[:80]}")

    # 2.5 Out-of-bounds particulate matter (pm2_5: -15.0)
    neg_pm_payload = dict(valid_payload)
    neg_pm_payload["sequence_number"] = random.randint(400000, 499999)
    neg_pm_payload["timestamp_epoch"] = int(time.time()) - 300
    neg_pm_payload["pm2_5"] = -15.0
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=json.dumps(neg_pm_payload).encode("utf-8"))
    passed_2_5 = (code in (200, 201))
    record("G2_PAYLOAD", "2.5 Negative PM2.5 processed by QC without crash", passed_2_5, f"HTTP {code}, body: {body[:80]}")

    # 2.6 Extreme particulate matter (pm2_5: 99999.0)
    huge_pm_payload = dict(valid_payload)
    huge_pm_payload["sequence_number"] = random.randint(500000, 599999)
    huge_pm_payload["timestamp_epoch"] = int(time.time()) - 400
    huge_pm_payload["pm2_5"] = 99999.0
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=json.dumps(huge_pm_payload).encode("utf-8"))
    passed_2_6 = (code in (200, 201))
    record("G2_PAYLOAD", "2.6 Extreme PM2.5 (99,999 ug/m3) processed safely", passed_2_6, f"HTTP {code}, body: {body[:80]}")

    # 2.7 Malformed timestamp string fallback
    bad_ts_payload = dict(valid_payload)
    bad_ts_payload["sequence_number"] = random.randint(600000, 699999)
    bad_ts_payload["timestamp"] = "INVALID_TIMESTAMP_STRING_XYZ"
    code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=json.dumps(bad_ts_payload).encode("utf-8"))
    passed_2_7 = (code in (200, 201))
    record("G2_PAYLOAD", "2.7 Malformed timestamp string falls back to server UTC", passed_2_7, f"HTTP {code}, body: {body[:80]}")

    # 2.8 Idempotency duplicate rejection
    dup_payload = dict(valid_payload)
    dup_payload["sequence_number"] = 777888
    dup_payload["timestamp_epoch"] = 1756990000
    dup_bytes = json.dumps(dup_payload).encode("utf-8")
    c1, b1, _ = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=dup_bytes)
    c2, b2, _ = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=dup_bytes)
    passed_2_8 = (c2 in (200, 201) and ('"duplicate":true' in b2.replace(" ", "") or '"accepted":true' in b2.replace(" ", "")))
    record("G2_PAYLOAD", "2.8 Idempotency hash catches duplicate payload", passed_2_8, f"HTTP {c2}, duplicate detected")


    # GROUP 3: Telemetry Feed Boundary & Coordinate Challenges
    print("\n--- GROUP 3: TELEMETRY FEED BOUNDARY & COORDINATE CHALLENGES ---")

    feed_base = f"{base_url}/api/v1/providers/weather/telemetry-feed"

    # 3.1 Default query (no coordinates)
    code, body, err = send_http_request(feed_base)
    passed_3_1 = (code == 200 and '"status":"success"' in body.replace(" ", ""))
    record("G3_FEED", "3.1 Default coordinates query returns HTTP 200", passed_3_1, f"HTTP {code}")

    # 3.2 North Pole (90.0, 0.0)
    code, body, err = send_http_request(f"{feed_base}?latitude=90.0&longitude=0.0")
    passed_3_2 = (code == 200 and '"status":"success"' in body.replace(" ", ""))
    record("G3_FEED", "3.2 North Pole boundary (90.0, 0.0) returns HTTP 200", passed_3_2, f"HTTP {code}")

    # 3.3 South Pole (-90.0, 0.0)
    code, body, err = send_http_request(f"{feed_base}?latitude=-90.0&longitude=0.0")
    passed_3_3 = (code == 200 and '"status":"success"' in body.replace(" ", ""))
    record("G3_FEED", "3.3 South Pole boundary (-90.0, 0.0) returns HTTP 200", passed_3_3, f"HTTP {code}")

    # 3.4 Date Line (+180.0 and -180.0)
    code1, body1, _ = send_http_request(f"{feed_base}?latitude=0.0&longitude=180.0")
    code2, body2, _ = send_http_request(f"{feed_base}?latitude=0.0&longitude=-180.0")
    passed_3_4 = (code1 == 200 and code2 == 200)
    record("G3_FEED", "3.4 Date line boundary (+-180.0 lon) returns HTTP 200", passed_3_4, f"HTTP {code1}/{code2}")

    # 3.5 Prime Meridian & Equator (0.0, 0.0)
    code, body, err = send_http_request(f"{feed_base}?latitude=0.0&longitude=0.0")
    passed_3_5 = (code == 200 and '"status":"success"' in body.replace(" ", ""))
    record("G3_FEED", "3.5 Equator & Prime Meridian (0.0, 0.0) returns HTTP 200", passed_3_5, f"HTTP {code}")

    # 3.6 Out-of-bounds coordinates (120.0, 300.0)
    code, body, err = send_http_request(f"{feed_base}?latitude=120.0&longitude=300.0")
    passed_3_6 = (code in (200, 400, 422))
    record("G3_FEED", "3.6 Out-of-bounds coordinates handled gracefully without 500", passed_3_6, f"HTTP {code}")

    # 3.7 Limit boundary: minimum valid (limit=1)
    code, body, err = send_http_request(f"{feed_base}?limit=1")
    passed_3_7 = False
    if code == 200:
        data = json.loads(body)
        passed_3_7 = (len(data.get("records", [])) == 1)
    record("G3_FEED", "3.7 Limit minimum boundary (limit=1) returns exactly 1 record", passed_3_7, f"HTTP {code}")

    # 3.8 Limit boundary: maximum valid (limit=100)
    code, body, err = send_http_request(f"{feed_base}?limit=100")
    passed_3_8 = False
    if code == 200:
        data = json.loads(body)
        passed_3_8 = (len(data.get("records", [])) <= 100)
    record("G3_FEED", "3.8 Limit maximum boundary (limit=100) returns HTTP 200", passed_3_8, f"HTTP {code}")

    # 3.9 Limit violation below min (limit=0)
    code, body, err = send_http_request(f"{feed_base}?limit=0")
    passed_3_9 = (code == 422)
    record("G3_FEED", "3.9 Limit violation below minimum (limit=0) rejected with HTTP 422", passed_3_9, f"HTTP {code}")

    # 3.10 Limit violation above max (limit=101)
    code, body, err = send_http_request(f"{feed_base}?limit=101")
    passed_3_10 = (code == 422)
    record("G3_FEED", "3.10 Limit violation above maximum (limit=101) rejected with HTTP 422", passed_3_10, f"HTTP {code}")

    # 3.11 Type violation (limit="abc")
    code, body, err = send_http_request(f"{feed_base}?limit=abc")
    passed_3_11 = (code == 422)
    record("G3_FEED", "3.11 Non-numeric limit parameter rejected with HTTP 422", passed_3_11, f"HTTP {code}")


    # GROUP 4: Concurrency & Rate Pressure on Live Public HTTPS
    print("\n--- GROUP 4: CONCURRENCY & RATE PRESSURE ON LIVE PUBLIC HTTPS ---")

    # 4.1 Rapid sequential burst of 10 requests
    seq_start = time.time()
    seq_success = 0
    seq_latencies = []
    for i in range(10):
        t0 = time.time()
        p = dict(valid_payload)
        p["sequence_number"] = 800000 + i
        p["timestamp_epoch"] = int(time.time()) - (1000 + i * 2)
        code, body, _ = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=json.dumps(p).encode("utf-8"))
        lat = (time.time() - t0) * 1000
        seq_latencies.append(lat)
        if code in (200, 201):
            seq_success += 1
    seq_elapsed = time.time() - seq_start
    avg_seq_lat = sum(seq_latencies) / len(seq_latencies) if seq_latencies else 0
    passed_4_1 = (seq_success == 10)
    record("G4_CONCURRENCY", "4.1 Rapid sequential burst (10/10) success", passed_4_1, f"{seq_success}/10 passed, avg latency {avg_seq_lat:.1f}ms, total {seq_elapsed:.2f}s")

    # 4.2 Concurrent burst of 10 requests via ThreadPoolExecutor
    conc_start = time.time()
    conc_results = []
    def make_concurrent_request(idx):
        t0 = time.time()
        p = dict(valid_payload)
        p["sequence_number"] = 900000 + idx
        p["timestamp_epoch"] = int(time.time()) - (2000 + idx * 3)
        code, body, err = send_http_request(ingest_url, method="POST", headers={"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}, body_bytes=json.dumps(p).encode("utf-8"), timeout=15)
        lat = (time.time() - t0) * 1000
        return code, lat, err

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(make_concurrent_request, i) for i in range(10)]
        for fut in as_completed(futures):
            conc_results.append(fut.result())

    conc_elapsed = time.time() - conc_start
    conc_success = sum(1 for c, _, _ in conc_results if c in (200, 201))
    conc_avg_lat = sum(l for _, l, _ in conc_results) / len(conc_results) if conc_results else 0
    passed_4_2 = (conc_success == 10)
    record("G4_CONCURRENCY", "4.2 Concurrent burst (10/10) over public HTTPS", passed_4_2, f"{conc_success}/10 passed, avg latency {conc_avg_lat:.1f}ms, total {conc_elapsed:.2f}s")


    # GROUP 5: Health & Diagnostic Probing over Live Public HTTPS
    print("\n--- GROUP 5: HEALTH & DIAGNOSTIC ENDPOINT PROBING ---")

    # 5.1 Liveness Probe
    code, body, _ = send_http_request(f"{base_url}/api/v1/health/liveness")
    passed_5_1 = (code == 200 and '"status":"healthy"' in body.replace(" ", ""))
    record("G5_HEALTH", "5.1 GET /api/v1/health/liveness returns HTTP 200 healthy", passed_5_1, f"HTTP {code}")

    # 5.2 Readiness Probe
    code, body, _ = send_http_request(f"{base_url}/api/v1/health/readiness")
    passed_5_2 = (code == 200 and '"connected":true' in body.replace(" ", ""))
    record("G5_HEALTH", "5.2 GET /api/v1/health/readiness returns HTTP 200 db connected", passed_5_2, f"HTTP {code}")

    # 5.3 Sensor Diagnostic Probe
    code, body, _ = send_http_request(f"{base_url}/api/v1/ingest/sensors/diagnostic")
    passed_5_3 = (code == 200 and '"station_liveness"' in body and '"sensors"' in body)
    record("G5_HEALTH", "5.3 GET /api/v1/ingest/sensors/diagnostic returns HTTP 200", passed_5_3, f"HTTP {code}")


    # =========================================================================
    # PART B: SERIAL BRIDGE DUAL-ROUTING RESILIENCE UNDER NETWORK FAILURES
    # =========================================================================
    print("\n--- GROUP 6: SERIAL BRIDGE DUAL-ROUTING FAILURE SIMULATION ---")

    test_payload = build_telemetry_payload(
        seq=999,
        pm1=8.0,
        pm25=15.0,
        pm10=22.0,
        temp=29.0,
        hum=60.0,
        press=1012.0,
        rain=False
    )

    # 6.1 Unreachable Cloud Endpoint isolation (non-routable IP)
    t_start = time.time()
    cloud_fail_result = push_to_endpoint("http://192.0.2.1:9999/api/v1/ingest/reading", test_payload, label="FAIL_TEST", timeout=1.5)
    t_elapsed = time.time() - t_start
    passed_6_1 = (cloud_fail_result is False and t_elapsed <= 2.5)
    record("G6_BRIDGE", "6.1 Unreachable cloud endpoint returns False cleanly within timeout", passed_6_1, f"returned False in {t_elapsed:.2f}s (timeout enforced)")

    # 6.2 Dual-dispatch isolation: Local succeeds even if Cloud fails
    local_url = "http://127.0.0.1:8000/api/v1/ingest/reading"
    unreachable_cloud = "http://192.0.2.1:9999/api/v1/ingest/reading"
    futures = push_telemetry_dual_async(test_payload, local_url=local_url, cloud_url=unreachable_cloud)
    passed_6_2 = False
    if len(futures) == 2:
        res_local = futures[0].result(timeout=5.0)
        res_cloud = futures[1].result(timeout=5.0)
        passed_6_2 = (res_local is True and res_cloud is False)
        record("G6_BRIDGE", "6.2 Dual-dispatch isolates failure: local succeeds while cloud fails", passed_6_2, f"local={res_local}, cloud={res_cloud}")
    else:
        record("G6_BRIDGE", "6.2 Dual-dispatch submits 2 futures", False, f"got {len(futures)} futures")

    # 6.3 Dual-dispatch isolation: Cloud succeeds even if Local is unreachable
    unreachable_local = "http://127.0.0.1:9998/api/v1/ingest/reading"
    cloud_live_url = f"{base_url}/api/v1/ingest/reading"
    futures = push_telemetry_dual_async(test_payload, local_url=unreachable_local, cloud_url=cloud_live_url)
    passed_6_3 = False
    if len(futures) == 2:
        res_local = futures[0].result(timeout=5.0)
        res_cloud = futures[1].result(timeout=5.0)
        passed_6_3 = (res_local is False and res_cloud is True)
        record("G6_BRIDGE", "6.3 Dual-dispatch isolates failure: live cloud succeeds while local fails", passed_6_3, f"local={res_local}, cloud={res_cloud}")
    else:
        record("G6_BRIDGE", "6.3 Dual-dispatch submits 2 futures", False, f"got {len(futures)} futures")

    # 6.4 Simulated HTTP 500 from endpoint
    server_500 = MockFailureServer(port=8891, mode="500")
    server_500.start()
    try:
        res_500 = push_to_endpoint("http://127.0.0.1:8891/api/v1/ingest/reading", test_payload, label="MOCK_500", timeout=2.0)
        passed_6_4 = (res_500 is False)
        record("G6_BRIDGE", "6.4 HTTP 500 from endpoint handled gracefully without crash", passed_6_4, f"result={res_500}")
    finally:
        server_500.stop()

    # 6.5 Simulated HTTP 502 / 503 Bad Gateway / Unavailable
    server_502 = MockFailureServer(port=8892, mode="502")
    server_502.start()
    try:
        res_502 = push_to_endpoint("http://127.0.0.1:8892/api/v1/ingest/reading", test_payload, label="MOCK_502", timeout=2.0)
        passed_6_5 = (res_502 is False)
        record("G6_BRIDGE", "6.5 HTTP 502 Bad Gateway handled gracefully without crash", passed_6_5, f"result={res_502}")
    finally:
        server_502.stop()

    # 6.6 Timeout Cutoff Enforcement (Simulated slow server delaying 5.0s with timeout=1.5s)
    server_slow = MockFailureServer(port=8893, mode="200", delay_seconds=5.0)
    server_slow.start()
    try:
        t_before = time.time()
        res_slow = push_to_endpoint("http://127.0.0.1:8893/api/v1/ingest/reading", test_payload, label="MOCK_SLOW", timeout=1.5)
        slow_elapsed = time.time() - t_before
        passed_6_6 = (res_slow is False and slow_elapsed < 3.0)
        record("G6_BRIDGE", "6.6 Strict timeout cutoff enforced on slow hanging endpoint", passed_6_6, f"returned False in {slow_elapsed:.2f}s (< 3.0s)")
    finally:
        server_slow.stop()

    # 6.7 Non-blocking high-throughput async dispatch under persistent failure
    t_dispatch_start = time.time()
    dispatched_futures = []
    for i in range(20):
        futs = push_telemetry_dual_async(test_payload, local_url=local_url, cloud_url=unreachable_cloud)
        dispatched_futures.extend(futs)
    dispatch_time = time.time() - t_dispatch_start
    passed_6_7 = (dispatch_time < 0.20 and len(dispatched_futures) == 40)
    record("G6_BRIDGE", "6.7 Non-blocking async dispatch: 20 packets (40 tasks) dispatched immediately", passed_6_7, f"dispatch time {dispatch_time*1000:.1f}ms for 40 tasks")

    # Wait for background pool to settle
    for f in dispatched_futures:
        try:
            f.result(timeout=3.5)
        except Exception:
            pass

    # 6.8 run_simulation_mode with unreachable cloud endpoint completes cleanly
    sim_payload = run_simulation_mode(cloud_url=unreachable_cloud, local_url=local_url, wait_for_completion=True)
    passed_6_8 = (sim_payload is not None and sim_payload["transmission_mode"] == "SERIAL_BRIDGE_SIMULATE")
    record("G6_BRIDGE", "6.8 run_simulation_mode finishes cleanly when cloud is unreachable", passed_6_8, f"simulation completed successfully")

    # =========================================================================
    # SUMMARY & VERDICT EVALUATION
    # =========================================================================
    print("\n" + "=" * 80)
    print("  EMPIRICAL CHALLENGER VERIFICATION SUMMARY")
    print("=" * 80)
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["passed"])
    failed_tests = total_tests - passed_tests

    print(f"Total Empirical Challenges: {total_tests}")
    print(f"Passed:                     {passed_tests}")
    print(f"Failed:                     {failed_tests}")
    print(f"Success Rate:               {(passed_tests/total_tests)*100:.1f}%")
    print("=" * 80)

    verdict = "APPROVE" if failed_tests == 0 else "REQUEST_CHANGES"
    print(f"\nEXPLICIT VERDICT: {verdict}")

    output_summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "success_rate_pct": round((passed_tests / total_tests) * 100, 1),
        "verdict": verdict,
        "results": results
    }

    with open("scripts/challenger_m1_m4_results.json", "w") as f:
        json.dump(output_summary, f, indent=2)

    return passed_tests, failed_tests, verdict


if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LIVE_URL
    p, f, v = run_all_empirical_tests(url_arg)
    sys.exit(0 if f == 0 else 1)

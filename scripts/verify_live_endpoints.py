"""AirSense Pakistan - Live Public HTTPS End-to-End Verification Suite.

Validates all 5 production endpoints against live cloud infrastructure:
1. GET /api/v1/health/liveness
2. GET /api/v1/health/readiness
3. GET /api/v1/providers/weather/telemetry-feed
4. POST /api/v1/ingest/reading
5. GET /api/v1/ingest/sensors/diagnostic
"""

import os
import sys
import time
import json
import httpx

DEFAULT_BASE_URL = os.getenv("AIRSENSE_VERIFY_URL", "http://127.0.0.1:8000")
DEVICE_TOKEN = os.getenv("AIRSENSE_DEVICE_TOKEN", "airsense_dev_token_khi_01")


def run_live_verification(base_url: str = None) -> bool:
    if not base_url:
        base_url = DEFAULT_BASE_URL
    base_url = base_url.rstrip("/")

    print("=" * 75)
    print("  AirSense Pakistan: Live HTTPS E2E Endpoint Verification")
    print(f"  Target Base URL: {base_url}")
    print(f"  Device Token:    {DEVICE_TOKEN[:6]}...{DEVICE_TOKEN[-4:]}")
    print("=" * 75)

    results = []

    # Use httpx with reasonable connect & read timeouts and standard TLS verification
    with httpx.Client(timeout=30.0, follow_redirects=True, verify=True) as client:
        # --- Pre-flight Warm-up (Handles Cloud Cold-Start) ---
        print("\n[0/5] Warming up target instance (pre-flight probe)...")
        try:
            t0 = time.time()
            warm = client.get(f"{base_url}/api/v1/health/liveness", timeout=60.0)
            elapsed = (time.time() - t0) * 1000
            print(f"      Instance responsive! (HTTP {warm.status_code}, {elapsed:.0f}ms)")
        except Exception as e:
            print(f"      [WARN] Warm-up probe encountered: {e}")

        # --- Test 1: Liveness Probe ---
        print("\n[1/5] Testing GET /api/v1/health/liveness...")
        try:
            t0 = time.time()
            res1 = client.get(f"{base_url}/api/v1/health/liveness")
            lat1 = (time.time() - t0) * 1000
            data1 = res1.json() if res1.status_code == 200 else {}
            status_val = data1.get("status")
            ok1 = res1.status_code == 200 and status_val in ("healthy", "ok")
            results.append(("1. Liveness Probe", res1.status_code, f"{lat1:.1f}ms", "PASS" if ok1 else "FAIL"))
            print(f"      Response: HTTP {res1.status_code} | Latency: {lat1:.1f}ms | Status: {status_val}")
        except Exception as e:
            results.append(("1. Liveness Probe", "ERR", "N/A", f"FAIL ({e})"))
            print(f"      [ERROR] {e}")

        # --- Test 2: Readiness Probe ---
        print("\n[2/5] Testing GET /api/v1/health/readiness...")
        try:
            t0 = time.time()
            res2 = client.get(f"{base_url}/api/v1/health/readiness")
            lat2 = (time.time() - t0) * 1000
            data2 = res2.json() if res2.status_code == 200 else {}
            db_connected = data2.get("database", {}).get("connected", False)
            sched_running = data2.get("background_scheduler", {}).get("running", False)
            status_val = data2.get("status")
            ok2 = res2.status_code == 200 and status_val == "ready" and db_connected
            results.append(("2. Readiness Probe", res2.status_code, f"{lat2:.1f}ms", "PASS" if ok2 else "FAIL"))
            print(f"      Response: HTTP {res2.status_code} | Latency: {lat2:.1f}ms | DB: {'CONNECTED' if db_connected else 'FAIL'} | Scheduler: {'RUNNING' if sched_running else 'STOPPED'}")
        except Exception as e:
            results.append(("2. Readiness Probe", "ERR", "N/A", f"FAIL ({e})"))
            print(f"      [ERROR] {e}")

        # --- Test 3: Telemetry Feed ---
        print("\n[3/5] Testing GET /api/v1/providers/weather/telemetry-feed...")
        try:
            t0 = time.time()
            res3 = client.get(
                f"{base_url}/api/v1/providers/weather/telemetry-feed",
                params={"limit": 5, "latitude": 24.8607, "longitude": 67.0011}
            )
            lat3 = (time.time() - t0) * 1000
            data3 = res3.json() if res3.status_code == 200 else {}
            records = data3.get("records", [])
            cadence = data3.get("cadence_seconds", 60)
            ok3 = res3.status_code == 200 and len(records) > 0
            results.append(("3. Telemetry Feed", res3.status_code, f"{lat3:.1f}ms", "PASS" if ok3 else "FAIL"))
            print(f"      Response: HTTP {res3.status_code} | Latency: {lat3:.1f}ms | Records: {len(records)} | Cadence: {cadence}s")
        except Exception as e:
            results.append(("3. Telemetry Feed", "ERR", "N/A", f"FAIL ({e})"))
            print(f"      [ERROR] {e}")

        # --- Test 4: Live Ingest Reading ---
        print("\n[4/5] Testing POST /api/v1/ingest/reading...")
        try:
            seq = int(time.time()) % 100000
            test_payload = {
                "schema_version": "1.0",
                "device_uid": "AIRSENSE-NODE-KHI-01",
                "station_code": "BIC-KHI-ROOF-01",
                "campus_code": "KARACHI",
                "sequence_number": seq,
                "timestamp_epoch": int(time.time()),
                "pm1": 9.2,
                "pm2_5": 18.5,
                "pm10": 27.3,
                "temperature": 31.0,
                "humidity": 62.0,
                "pressure": 1011.5,
                "gas_resistance_kohm": 48.0,
                "rain_flag": False,
                "sensor_health": {"pms7003": "OK", "bme280": "OK", "rain": "OK", "microsd": "OK"},
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
            accepted = data4.get("accepted", False)
            ingest_id = data4.get("ingestion_id")
            qc_state = data4.get("quality_processing_state")
            ok4 = res4.status_code in (200, 201) and accepted is True and ingest_id is not None
            results.append(("4. Ingest Reading", res4.status_code, f"{lat4:.1f}ms", "PASS" if ok4 else "FAIL"))
            print(f"      Response: HTTP {res4.status_code} | Latency: {lat4:.1f}ms | Ingest ID: {ingest_id} | QC: {qc_state} | Accepted: {accepted}")
        except Exception as e:
            results.append(("4. Ingest Reading", "ERR", "N/A", f"FAIL ({e})"))
            print(f"      [ERROR] {e}")

        # --- Test 5: Sensor Health Diagnostic Status ---
        print("\n[5/5] Testing GET /api/v1/ingest/sensors/diagnostic...")
        try:
            t0 = time.time()
            res5 = client.get(f"{base_url}/api/v1/ingest/sensors/diagnostic")
            lat5 = (time.time() - t0) * 1000
            data5 = res5.json() if res5.status_code == 200 else {}
            stn_state = data5.get("station_liveness") or data5.get("overall_state")
            seconds_ago = data5.get("seconds_since_last_packet")
            is_live = (seconds_ago is not None and seconds_ago <= 120) or data5.get("heartbeat", {}).get("is_alive", False)
            # Must be LIVE_ACTIVE or ONLINE or PARTIAL_DEGRADED after the recent ingest reading
            ok5 = res5.status_code == 200 and stn_state in ("LIVE_ACTIVE", "ONLINE", "PARTIAL_DEGRADED")
            results.append(("5. Sensor Diagnostics", res5.status_code, f"{lat5:.1f}ms", "PASS" if ok5 else "FAIL"))
            print(f"      Response: HTTP {res5.status_code} | Latency: {lat5:.1f}ms | Station State: {stn_state} | Seconds Ago: {seconds_ago} | PMS7003: {data5.get('sensors', {}).get('pms7003', {}).get('status')}")
        except Exception as e:
            results.append(("5. Sensor Diagnostics", "ERR", "N/A", f"FAIL ({e})"))
            print(f"      [ERROR] {e}")

    # --- Summary Table ---
    print("\n" + "=" * 75)
    print("  AIRSENSE LIVE PUBLIC HTTPS VERIFICATION SUMMARY")
    print("=" * 75)
    print(f" {'Endpoint / Probe':<32} | {'Status':<8} | {'Latency':<10} | {'Result':<6}")
    print("-" * 75)
    all_passed = True
    for name, code, lat, res in results:
        print(f" {name:<32} | {str(code):<8} | {lat:<10} | {res:<6}")
        if res != "PASS":
            all_passed = False
    print("=" * 75)

    if all_passed:
        print("\n[SUCCESS] ALL 5 PRODUCTION ENDPOINTS VERIFIED OPERATIONAL!")
    else:
        print("\n[FAILURE] ONE OR MORE ENDPOINTS FAILED VERIFICATION.")

    return all_passed


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    success = run_live_verification(target)
    sys.exit(0 if success else 1)

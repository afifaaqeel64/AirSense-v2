"""AirSense Pakistan - Independent Deep Forensic & Live Verification Suite.

Author: auditor_victory_4
Purpose: Independently verify all claims of project completion:
1. Genuine TLS/HTTPS connectivity on Cloudflare Tunnel.
2. Production health probes (liveness, readiness).
3. Database connectivity and background scheduler telemetry.
4. Schema validation and authentication enforcement.
5. Ingestion of live reading and immediate dynamic reflection in sensor diagnostics.
6. Autonomous 60s background scheduler progression.
"""

import sys
import time
import json
import httpx
from datetime import datetime, timezone

TARGET_URL = "https://forums-surfaces-reef-stands.trycloudflare.com"
DEVICE_TOKEN = "airsense_dev_token_khi_01"


def run_audit():
    print("=" * 80)
    print("  AUDITOR_VICTORY_4: INDEPENDENT DEEP LIVE VERIFICATION")
    print(f"  Target: {TARGET_URL}")
    print(f"  Time UTC: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    audit_results = {}
    client = httpx.Client(timeout=30.0, follow_redirects=True, verify=True)

    # -------------------------------------------------------------
    # Check 1: Liveness Probe
    # -------------------------------------------------------------
    print("\n--- Check 1: Liveness Probe (GET /api/v1/health/liveness) ---")
    try:
        t0 = time.time()
        r = client.get(f"{TARGET_URL}/api/v1/health/liveness")
        lat = (time.time() - t0) * 1000
        print(f"Status Code: {r.status_code} (Latency: {lat:.1f}ms)")
        data = r.json()
        print(f"Response Payload:\n{json.dumps(data, indent=2)}")

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert data.get("status") == "healthy", f"Expected status 'healthy', got {data.get('status')}"
        assert data.get("process") == "running", f"Expected process 'running', got {data.get('process')}"
        assert "timestamp_utc" in data, "Missing timestamp_utc"
        audit_results["Check 1: Liveness Probe"] = ("PASS", f"HTTP {r.status_code}, {lat:.1f}ms")
    except Exception as e:
        print(f"[FAIL] Check 1: {e}")
        audit_results["Check 1: Liveness Probe"] = ("FAIL", str(e))

    # -------------------------------------------------------------
    # Check 2: Deep Readiness Probe & Scheduler Status
    # -------------------------------------------------------------
    print("\n--- Check 2: Readiness Probe (GET /api/v1/health/readiness) ---")
    try:
        t0 = time.time()
        r = client.get(f"{TARGET_URL}/api/v1/health/readiness")
        lat = (time.time() - t0) * 1000
        print(f"Status Code: {r.status_code} (Latency: {lat:.1f}ms)")
        data = r.json()
        print(f"Response Payload:\n{json.dumps(data, indent=2)}")

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert data.get("status") == "ready", f"Expected status 'ready', got {data.get('status')}"
        assert data.get("database", {}).get("connected") is True, "Database not connected"
        assert data.get("storage", {}).get("disk_writable") is True, "Storage not disk_writable"
        
        sched = data.get("background_scheduler", {})
        is_sched_running = sched.get("is_running")
        uptime = sched.get("uptime_seconds", 0)
        workers = sched.get("active_workers", [])
        stats = sched.get("execution_stats", {})

        print(f"Scheduler is_running: {is_sched_running}, Uptime: {uptime}s, Workers: {workers}")
        print(f"Scheduler Execution Stats: {stats}")

        assert is_sched_running is True, f"Scheduler is_running is not True: {is_sched_running}"
        assert len(workers) >= 4, f"Expected at least 4 active workers, got {workers}"
        for w in ["minute_weather_engine", "hardware_watchdog", "hourly_qc_rollup", "daily_backup"]:
            assert w in workers, f"Worker {w} missing from active_workers"

        audit_results["Check 2: Readiness Probe & Scheduler"] = ("PASS", f"HTTP {r.status_code}, Uptime {uptime}s, 4 workers")
    except Exception as e:
        print(f"[FAIL] Check 2: {e}")
        audit_results["Check 2: Readiness Probe & Scheduler"] = ("FAIL", str(e))

    # -------------------------------------------------------------
    # Check 3: Meteorological Telemetry Feed
    # -------------------------------------------------------------
    print("\n--- Check 3: Telemetry Feed (GET /api/v1/providers/weather/telemetry-feed) ---")
    try:
        t0 = time.time()
        r = client.get(f"{TARGET_URL}/api/v1/providers/weather/telemetry-feed?limit=10")
        lat = (time.time() - t0) * 1000
        print(f"Status Code: {r.status_code} (Latency: {lat:.1f}ms)")
        data = r.json()
        records = data.get("records", [])
        print(f"Cadence: {data.get('cadence_seconds')}s, Total Records: {len(records)}")
        if records:
            print(f"Latest Record Sample:\n{json.dumps(records[0], indent=2)}")

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert data.get("status") == "success", f"Expected status 'success', got {data.get('status')}"
        assert len(records) >= 5, f"Expected at least 5 records, got {len(records)}"
        latest = records[0]
        assert "temp" in latest and "hum" in latest and "pm25" in latest, "Missing metrics in record"
        assert "wmo_description" in latest, "Missing wmo_description"

        audit_results["Check 3: Telemetry Feed"] = ("PASS", f"HTTP {r.status_code}, {len(records)} records, {lat:.1f}ms")
    except Exception as e:
        print(f"[FAIL] Check 3: {e}")
        audit_results["Check 3: Telemetry Feed"] = ("FAIL", str(e))

    # -------------------------------------------------------------
    # Check 4: Authentication Security Enforcement (Anti-Facade)
    # -------------------------------------------------------------
    print("\n--- Check 4: Auth Enforcement Check (POST /api/v1/ingest/reading with bad token) ---")
    try:
        t0 = time.time()
        bad_headers = {"Content-Type": "application/json", "X-Device-Token": "INVALID_TOKEN_FAKE_9999"}
        dummy_payload = {"device_uid": "AIRSENSE-NODE-KHI-01", "pm2_5": 10.0}
        r_auth = client.post(f"{TARGET_URL}/api/v1/ingest/reading", json=dummy_payload, headers=bad_headers)
        lat = (time.time() - t0) * 1000
        print(f"Response with invalid token: HTTP {r_auth.status_code} (Latency: {lat:.1f}ms)")
        print(f"Payload: {r_auth.text[:200]}")

        # Real backend MUST reject invalid device tokens with 401 or 403
        assert r_auth.status_code in (401, 403), f"Expected 401 or 403 for unauthorized token, got {r_auth.status_code}"
        audit_results["Check 4: Auth Enforcement"] = ("PASS", f"Correctly rejected unauthorized request with HTTP {r_auth.status_code}")
    except Exception as e:
        print(f"[FAIL] Check 4: {e}")
        audit_results["Check 4: Auth Enforcement"] = ("FAIL", str(e))

    # -------------------------------------------------------------
    # Check 5: Live Ingest Reading (Authorized)
    # -------------------------------------------------------------
    print("\n--- Check 5: Live Ingest Reading (POST /api/v1/ingest/reading) ---")
    ingest_time_epoch = int(time.time())
    try:
        t0 = time.time()
        headers = {"Content-Type": "application/json", "X-Device-Token": DEVICE_TOKEN}
        payload = {
            "schema_version": "1.0",
            "device_uid": "AIRSENSE-NODE-KHI-01",
            "station_code": "BIC-KHI-ROOF-01",
            "campus_code": "KARACHI",
            "sequence_number": 88888,
            "timestamp_epoch": ingest_time_epoch,
            "pm1": 8.5,
            "pm2_5": 16.2,
            "pm10": 24.1,
            "temperature": 30.5,
            "humidity": 64.0,
            "pressure": 1010.8,
            "gas_resistance_kohm": 52.0,
            "rain_flag": False,
            "sensor_health": {"pms7003": "OK", "bme280": "OK", "rain": "OK", "microsd": "OK"},
            "firmware_version": "v3.5.0-AUDIT-INDEPENDENT",
            "transmission_mode": "AUDITOR_VICTORY_4_LIVE_PROBE"
        }
        r_ingest = client.post(f"{TARGET_URL}/api/v1/ingest/reading", json=payload, headers=headers)
        lat = (time.time() - t0) * 1000
        print(f"Status Code: {r_ingest.status_code} (Latency: {lat:.1f}ms)")
        data_ingest = r_ingest.json()
        print(f"Ingest Response:\n{json.dumps(data_ingest, indent=2)}")

        assert r_ingest.status_code == 200, f"Expected 200, got {r_ingest.status_code}"
        assert data_ingest.get("accepted") is True, "Ingest not accepted"
        assert data_ingest.get("ingestion_id") is not None, "Missing ingestion_id"
        audit_results["Check 5: Live Ingestion"] = ("PASS", f"HTTP {r_ingest.status_code}, ID: {data_ingest.get('ingestion_id')}")
    except Exception as e:
        print(f"[FAIL] Check 5: {e}")
        audit_results["Check 5: Live Ingestion"] = ("FAIL", str(e))

    # -------------------------------------------------------------
    # Check 6: Sensor Diagnostics Dynamic Reflection
    # -------------------------------------------------------------
    print("\n--- Check 6: Sensor Diagnostics (GET /api/v1/ingest/sensors/diagnostic) ---")
    try:
        t0 = time.time()
        r_diag = client.get(f"{TARGET_URL}/api/v1/ingest/sensors/diagnostic")
        lat = (time.time() - t0) * 1000
        print(f"Status Code: {r_diag.status_code} (Latency: {lat:.1f}ms)")
        data_diag = r_diag.json()
        print(f"Diagnostic Response:\n{json.dumps(data_diag, indent=2)}")

        assert r_diag.status_code == 200, f"Expected 200, got {r_diag.status_code}"
        stn_state = data_diag.get("station_liveness")
        sec_ago = data_diag.get("seconds_since_last_packet")
        print(f"Station Liveness: {stn_state}, Seconds Since Last Packet: {sec_ago}")

        # Because we just pushed a packet in Check 5 seconds ago, seconds_since_last_packet must be <= 15
        # and station_liveness must be LIVE_ACTIVE!
        assert sec_ago is not None and sec_ago <= 15, f"Expected seconds_since_last_packet <= 15, got {sec_ago}"
        assert stn_state in ("LIVE_ACTIVE", "ONLINE"), f"Expected LIVE_ACTIVE, got {stn_state}"
        
        pms_status = data_diag.get("sensors", {}).get("pms7003", {}).get("status")
        bme_status = data_diag.get("sensors", {}).get("bme280", {}).get("status")
        print(f"PMS7003 Status: {pms_status}, BME280 Status: {bme_status}")
        assert pms_status == "ONLINE", f"Expected PMS7003 ONLINE, got {pms_status}"
        assert bme_status == "ONLINE", f"Expected BME280 ONLINE, got {bme_status}"

        audit_results["Check 6: Sensor Diagnostics Dynamic Update"] = ("PASS", f"HTTP {r_diag.status_code}, State: {stn_state}, Recency: {sec_ago}s")
    except Exception as e:
        print(f"[FAIL] Check 6: {e}")
        audit_results["Check 6: Sensor Diagnostics Dynamic Update"] = ("FAIL", str(e))

    # -------------------------------------------------------------
    # Check 7: Autonomous 60s Scheduler Live Execution Proof
    # -------------------------------------------------------------
    print("\n--- Check 7: Autonomous 60s Background Scheduler Live Execution Proof ---")
    print("Capturing initial scheduler stats and waiting 65 seconds to observe autonomous background tick...")
    try:
        r_init = client.get(f"{TARGET_URL}/api/v1/health/readiness")
        sched_init = r_init.json().get("background_scheduler", {})
        init_ticks = sched_init.get("execution_stats", {}).get("minute_weather_ticks", 0)
        init_uptime = sched_init.get("uptime_seconds", 0)
        print(f"Initial State: minute_weather_ticks = {init_ticks}, uptime_seconds = {init_uptime}")

        # Sleep 65 seconds
        for remaining in range(65, 0, -15):
            print(f"Sleeping {remaining}s remaining...")
            time.sleep(15)

        r_after = client.get(f"{TARGET_URL}/api/v1/health/readiness")
        sched_after = r_after.json().get("background_scheduler", {})
        after_ticks = sched_after.get("execution_stats", {}).get("minute_weather_ticks", 0)
        after_uptime = sched_after.get("uptime_seconds", 0)
        print(f"After 65s State: minute_weather_ticks = {after_ticks}, uptime_seconds = {after_uptime}")

        assert after_uptime > init_uptime + 55, f"Uptime did not advance properly: {after_uptime} vs {init_uptime}"
        assert after_ticks >= init_ticks + 1, f"minute_weather_ticks did not advance! Initial: {init_ticks}, After: {after_ticks}"

        audit_results["Check 7: Autonomous Scheduler 60s Cadence"] = (
            "PASS",
            f"Autonomous tick verified! Ticks: {init_ticks} -> {after_ticks}, Uptime: {init_uptime}s -> {after_uptime}s"
        )
    except Exception as e:
        print(f"[FAIL] Check 7: {e}")
        audit_results["Check 7: Autonomous Scheduler 60s Cadence"] = ("FAIL", str(e))

    # -------------------------------------------------------------
    # Final Summary Table
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("  AUDITOR_VICTORY_4 INDEPENDENT AUDIT SUMMARY")
    print("=" * 80)
    all_clean = True
    for check_name, (verdict, details) in audit_results.items():
        print(f" {check_name:<45} | {verdict:<6} | {details}")
        if verdict != "PASS":
            all_clean = False
    print("=" * 80)

    if all_clean:
        print("\n>>> VERDICT: ALL INDEPENDENT CHECKS PASSED EMPIRICALLY! <<<")
    else:
        print("\n>>> VERDICT: INTEGRITY FAILURE OR DISCREPANCY DETECTED! <<<")

    return all_clean


if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)

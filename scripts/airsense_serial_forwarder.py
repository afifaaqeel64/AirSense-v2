"""AirSense Pakistan: USB Serial Bridge & Telemetry Forwarder.

Reads real-time telemetry directly from ESP32 USB COM port (with dynamic auto-detection)
and streams it instantly into the local AirSense FastAPI backend & Dashboard!
Hardened with infinite auto-recovery loops, non-crashing exception handlers, and backoff.
"""

import sys
import time
import json
import re
import random
import urllib.request
import urllib.error
import serial
import serial.tools.list_ports

DEFAULT_BAUD = 115200
API_URL = "http://127.0.0.1:8000/api/v1/ingest/reading"
DEVICE_TOKEN = "airsense_dev_token_khi_01"
DEVICE_UID = "AIRSENSE-NODE-KHI-01"

KNOWN_PORT_KEYWORDS = [
    "cp210", "ch340", "ch9102", "ftdi", "uart", 
    "usb serial", "serial", "silicon labs", "wch", 
    "arduino", "espressif"
]


def scan_ports():
    """Scan and rank available COM ports, prioritizing USB-UART bridge devices."""
    ports = list(serial.tools.list_ports.comports())
    matched = []
    others = []
    
    for p in ports:
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        if any(kw in desc or kw in hwid for kw in KNOWN_PORT_KEYWORDS):
            matched.append(p.device)
        else:
            others.append(p.device)
            
    return matched + others


def find_target_port(preferred_port=None):
    """Finds best matching COM port, falling back cleanly to dynamic scan."""
    available = scan_ports()
    if not available:
        return None

    if preferred_port and preferred_port.upper() not in ("AUTO", "NONE", ""):
        for p in available:
            if p.upper() == preferred_port.upper():
                return p
        print(f"[FORWARDER NOTICE] Port {preferred_port} not found. Available: {available}. Auto-selecting {available[0]}")
        return available[0]

    return available[0]


def post_telemetry(payload, seq):
    """Posts telemetry payload to the local API endpoint."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEVICE_TOKEN}",
        "X-Device-UID": DEVICE_UID,
        "Idempotency-Key": f"{DEVICE_UID}-{seq}-{int(time.time())}"
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=3.0) as res:
        resp_data = json.loads(res.read().decode('utf-8'))
        print(f"[DASHBOARD SUCCESS] Ingestion accepted! ID: {resp_data.get('ingestion_id')} | QC: {resp_data.get('quality_processing_state')}")


def run_forwarder(preferred_port=None, baudrate=DEFAULT_BAUD):
    """Runs serial forwarder with infinite auto-recovery reconnect loop."""
    print("=" * 65)
    print("  AirSense Pakistan: USB Serial Bridge & Dashboard Streamer")
    print(f"  Target: {preferred_port or 'AUTO-DETECT'} @ {baudrate} baud -> Posting to {API_URL}")
    print("=" * 65)

    backoff = 1.0
    max_backoff = 8.0
    seq = 0

    while True:
        ser = None
        current_port = None
        try:
            current_port = find_target_port(preferred_port)
            if not current_port:
                jitter = random.uniform(0.1, 0.4)
                sleep_t = min(backoff + jitter, max_backoff)
                print(f"[FORWARDER SCAN] No active COM ports detected. Retrying in {sleep_t:.1f}s...")
                time.sleep(sleep_t)
                backoff = min(backoff * 1.5, max_backoff)
                continue

            print(f"[FORWARDER] Opening {current_port} at {baudrate} baud...")
            ser = serial.Serial(current_port, baudrate, timeout=1.5)
            print(f"[FORWARDER SUCCESS] Connected to {current_port}! Streaming live telemetry...")
            backoff = 1.0  # Reset backoff on successful connect

            while True:
                raw_line = ser.readline()
                if not raw_line:
                    continue

                line = raw_line.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                    
                print(f"[ESP32 RAW] {line}")
                
                # Check for JSON telemetry line
                json_candidate = None
                if line.startswith("[JSON_TELEMETRY]"):
                    json_candidate = line.replace("[JSON_TELEMETRY]", "").strip()
                elif line.startswith("{") and line.endswith("}"):
                    json_candidate = line

                if json_candidate:
                    try:
                        payload = json.loads(json_candidate)
                        seq += 1
                        post_telemetry(payload, seq)
                    except json.JSONDecodeError:
                        pass
                    except Exception as ex:
                        print(f"[FORWARD ERROR] Could not post to backend: {ex}")

        except serial.SerialException as se:
            err_str = str(se)
            if "PermissionError" in err_str or "Access is denied" in err_str:
                print(f"[FORWARDER WAITING] Port {current_port} is busy or open in Arduino IDE. Please close conflicting apps. Retrying in 2s...")
            else:
                print(f"[FORWARDER DISCONNECT] Serial connection lost on {current_port}: {se}.")
            
            jitter = random.uniform(0.1, 0.4)
            sleep_t = min(backoff + jitter, max_backoff)
            print(f"[FORWARDER RECOVER] Retrying in {sleep_t:.1f}s...")
            time.sleep(sleep_t)
            backoff = min(backoff * 1.5, max_backoff)

        except KeyboardInterrupt:
            print("\n[AirSense] Stopping forwarder...")
            break

        except Exception as e:
            print(f"[FORWARDER ERROR] {e}")
            jitter = random.uniform(0.1, 0.4)
            sleep_t = min(backoff + jitter, max_backoff)
            print(f"[FORWARDER RECOVER] Retrying in {sleep_t:.1f}s...")
            time.sleep(sleep_t)
            backoff = min(backoff * 1.5, max_backoff)

        finally:
            if ser and ser.is_open:
                try:
                    ser.close()
                except Exception:
                    pass


if __name__ == "__main__":
    cli_p = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else None
    if cli_p and cli_p.upper() in ("AUTO", "DEFAULT"):
        cli_p = None

    try:
        run_forwarder(cli_p)
    except KeyboardInterrupt:
        print("\n[AirSense] Forwarder exited cleanly.")

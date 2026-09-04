"""AirSense - Stop USB Serial Bridge
Stops any active airsense_serial_live_bridge process and frees COM7.
"""

import os
import sys
import subprocess
import re

PID_FILE = os.path.join(os.path.dirname(__file__), ".bridge.pid")
stopped_any = False

# 1. Check PID file
if os.path.exists(PID_FILE):
    try:
        with open(PID_FILE, "r") as f:
            pid_str = f.read().strip()
        if pid_str:
            res = subprocess.run(["taskkill", "/F", "/PID", pid_str], capture_output=True, text=True)
            if res.returncode == 0:
                print(f"[AirSense] Terminated bridge process (PID {pid_str}).")
                stopped_any = True
    except Exception as e:
        pass
    finally:
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

# 2. Search WMIC for any remaining instances of airsense_serial_live_bridge
try:
    out = subprocess.check_output(["wmic", "process", "get", "ProcessId,CommandLine"], text=True, errors="ignore")
    pids = [m.group(1) for m in re.finditer(r".*airsense_serial_live_bridge.*?\s+(\d+)\s*$", out, re.MULTILINE)]
    for pid in pids:
        # Don't kill ourselves
        if str(os.getpid()) != pid:
            subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
            print(f"[AirSense] Terminated bridge process (PID {pid}).")
            stopped_any = True
except Exception:
    pass

if stopped_any:
    print("[AirSense] Serial bridge stopped! COM7 is now completely free for Arduino IDE.")
else:
    print("[AirSense] Serial bridge was not running. COM7 is free.")

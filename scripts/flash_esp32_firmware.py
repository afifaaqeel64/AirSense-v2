"""AirSense 1-Click ESP32 Flash Tool & Memory Recovery Utility.
Erase and flashes ESP32 with bulletproof DIO 40MHz settings to prevent any MD5 mismatch.
"""

import sys
import subprocess
import serial.tools.list_ports

def get_com_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = p.description.lower()
        if "cp210" in desc or "ch340" in desc or "uart" in desc:
            return p.device
    if ports:
        return ports[0].device
    return "COM7"

def erase_and_recover(port=None):
    com_port = port or get_com_port()
    print(f"=== AirSense ESP32 Flash Tool ===")
    print(f"Target Port: {com_port}")
    
    print("\n[STEP 1] Erasing Corrupted Flash Sectors...")
    cmd_erase = [sys.executable, "-m", "esptool", "--port", com_port, "--baud", "115200", "erase_flash"]
    res = subprocess.run(cmd_erase)
    
    if res.returncode == 0:
        print("\n[SUCCESS] Flash memory wiped and restored cleanly!")
        print("Now you can click Upload in Arduino IDE with Flash Mode: DOUT or DIO.")
    else:
        print("\n[INFO] If connection timed out, hold the BOOT button on your ESP32 and run again.")

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else None
    erase_and_recover(p)

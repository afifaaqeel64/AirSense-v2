"""AirSense Fast Direct Flasher.
Flashes the compiled binary directly with DOUT 40MHz mode.
"""

import sys
import subprocess
import os

sketch_dir = r"C:\Users\HP\AppData\Local\arduino\sketches\F5084256F8F5400580C13B786BFC4D6A"
merged_bin = os.path.join(sketch_dir, "airsense_esp32_firmware.ino.merged.bin")

cmd = [
    sys.executable, "-m", "esptool",
    "--chip", "esp32",
    "--port", "COM7",
    "--baud", "115200",
    "--before", "default-reset",
    "--after", "hard-reset",
    "write-flash",
    "--flash-mode", "dio",
    "--flash-freq", "40m",
    "--flash-size", "detect",
    "0x1000", os.path.join(sketch_dir, "airsense_esp32_firmware.ino.bootloader.bin"),
    "0x8000", os.path.join(sketch_dir, "airsense_esp32_firmware.ino.partitions.bin"),
    "0xe000", os.path.join(sketch_dir, "boot_app0.bin"),
    "0x10000", os.path.join(sketch_dir, "airsense_esp32_firmware.ino.bin")
]

print("Executing:", " ".join(cmd))
res = subprocess.run(cmd)
if res.returncode == 0:
    print("\n[SUCCESS] ESP32 Flashed 100% Successfully!")
else:
    print(f"\n[FAILED] Exit code: {res.returncode}")

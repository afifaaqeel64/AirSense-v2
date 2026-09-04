# AirSense Pakistan: Arduino IDE Setup & Edge Firmware Deployment Guide

**Document Type:** Technical Setup Manual & Team Onboarding Guide  
**Project Initiative:** COIL AI Collaborative Environmental Intelligence  
**Institution:** Beaconhouse International College (BIC)  
**Campus Focus:** Karachi Campus Deployment (`BIC-KHI-ROOF-01`) & Islamabad Campus Deployment (`BIC-ISB-ROOF-01`)  
**Hardware Target:** Espressif ESP32 WROOM-32D Development Board  
**Document Revision:** August 2026 Enterprise Edition  

---

## 1. Overview & Purpose

This manual provides an end-to-end guide for setting up the **Arduino IDE 2.x** development environment, installing necessary ESP32 board cores and sensor libraries, resolving USB driver issues, configuring production firmware parameters, and flashing the ESP32 microcontroller. 

Sharing this document with team members ensures uniform setup across all development machines without software version mismatches or configuration errors.

---

## 2. Phase 1: Installing Arduino IDE 2.x

1. Download the official installer for **Arduino IDE 2.x** from the Arduino Software Portal:  
   `https://www.arduino.cc/en/software`
2. Run the Windows installer (`.exe`) and follow standard installation prompts.
3. Launch Arduino IDE once installation completes.

---

## 3. Phase 2: Installing ESP32 Board Core Support

By default, Arduino IDE only includes profiles for standard 8-bit AVR boards (such as Arduino Uno). Follow these steps to install full 32-bit Espressif ESP32 support:

1. Open Arduino IDE and open the **Preferences** dialog:
   * Go to **File $\rightarrow$ Preferences** (or press `Ctrl + Comma`).
2. Locate the input field named **Additional boards manager URLs**.
3. Copy and paste the following official Espressif repository URL into the field:
   ```text
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
   *(Note: If there are already other URLs in that field, separate them with a comma or click the small window icon next to the field and paste on a new line).*
4. Click **OK** to save preferences.
5. Open the **Boards Manager**:
   * Click the **Boards Manager** icon on the left sidebar (looks like an IC board), OR navigate via the top menu: **Tools $\rightarrow$ Board $\rightarrow$ Boards Manager...**
6. In the search box, type `esp32`.
7. Locate **esp32 by Espressif Systems** and click **Install**.
8. Wait for the download and compilation toolchains (xtensa-esp32-elf) to complete.

---

## 4. Phase 3: USB to UART Drivers Installation

When plugging the ESP32 board into a Windows PC via USB cable, Windows must recognize the USB-to-Serial bridge chip on the board.

### Identifying Your USB Chip:
Look at the small rectangular chip located right next to the Micro-USB / Type-C port on your ESP32 board:
* **Silicon Labs CP2102 / CP2104:** Displays "SILABS CP2102" on the chip.
  * *Driver:* Download **CP210x Universal Windows Driver** from Silicon Labs:  
    `https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers`
* **WCH CH340G / CH340C:** Displays "WCH CH340" on the chip.
  * *Driver:* Download **CH341SER.EXE** from official WCH portal or reputable vendor links.

### Verification in Windows Device Manager:
1. Press `Win + X` and select **Device Manager**.
2. Expand the section named **Ports (COM & LPT)**.
3. Plug in the ESP32 via USB. You should see a new entry appear:
   * Example: `Silicon Labs CP210x USB to UART Bridge (COM3)` OR `USB-SERIAL CH340 (COM4)`.
4. Take note of the COM port number (`COM3`, `COM4`, etc.).

> [!WARNING]
> If no new COM port appears when plugging in the board, your USB cable is likely a "charging only" cable lacking internal data lines. Swap to a certified high-speed USB data sync cable.

---

## 5. Phase 4: Installing Required Arduino Libraries

The AirSense edge firmware relies on three community and vendor libraries. Install them via the built-in Library Manager:

1. Open Library Manager:
   * Click the **Library Manager** icon on the left sidebar (looks like a stack of books), OR press `Ctrl + Shift + I`, OR go to **Tools $\rightarrow$ Manage Libraries...**
2. Install the following libraries:

| Library Name | Author | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Adafruit BME280 Library** | Adafruit | Latest (2.2.x+) | Reads temperature, humidity, and barometric pressure over I2C |
| **Adafruit Unified Sensor** | Adafruit | Latest (1.1.x+) | Core sensor abstraction dependency for Adafruit sensors |
| **ArduinoJson** | Benoit Blanchon | Version 6.x or 7.x | Serializes live telemetry structs into compact JSON REST payloads |

*(When installing Adafruit BME280, if prompted to "Install all dependencies", click **Install All**).*

The following libraries are built directly into the ESP32 core and do not require separate installation:
* `WiFi.h` (ESP32 Wi-Fi Station & AP management)
* `HTTPClient.h` (Non-blocking HTTP POST client)
* `Wire.h` (Hardware I2C driver)
* `SPI.h` (Hardware SPI bus driver)
* `SD.h` (FAT16/FAT32 MicroSD filesystem driver)

---

## 6. Phase 5: Board Configuration Settings in Arduino IDE

Once the board package is installed and the ESP32 is plugged in, configure the IDE target parameters:

1. In the top toolbar, click the **Board Selection Dropdown** $\rightarrow$ Click **Select other board and port...**
2. In the Search Board field, type: `ESP32 Dev Module`.
3. Select `ESP32 Dev Module` from the list.
4. On the right side, select your active **COM Port** (e.g. `COM3`).
5. Click **OK**.

### Recommended Settings under the `Tools` Menu:
* **Board:** `"ESP32 Dev Module"`
* **Upload Speed:** `921600` (Use `115200` if upload instability occurs)
* **CPU Frequency:** `240MHz (WiFi/BT)`
* **Flash Frequency:** `80MHz`
* **Flash Mode:** `QIO`
* **Flash Size:** `4MB (32Mb)`
* **Partition Scheme:** `Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)`
* **Core Debug Level:** `None` (or `Info` for debugging)
* **Port:** `COMx` *(your detected port)*

---

## 7. Phase 6: Loading and Customizing the Firmware

The production firmware sketch is located at:  
`d:\MUNIM - UOE @BIC\AirSense\scripts\airsense_esp32_firmware\airsense_esp32_firmware.ino`

### Step 1: Open the Sketch
1. In Arduino IDE, click **File $\rightarrow$ Open...**
2. Navigate to `d:\MUNIM - UOE @BIC\AirSense\scripts\airsense_esp32_firmware\airsense_esp32_firmware.ino` and click **Open**.

### Step 2: Configure Network Credentials & Deployment Parameters
Locate Section 1 near the top of the file:

```cpp
// =============================================================================
// 1. CONFIGURATION & CREDENTIALS (UPDATE THESE FOR YOUR NETWORK)
// =============================================================================
const char* WIFI_SSID = "YOUR_WIFI_NAME";           // Campus or local Wi-Fi SSID
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";       // Wi-Fi Password

// Backend Ingestion Endpoint
// For local testing on your PC, find your PC IP via 'ipconfig' (e.g., http://192.168.1.100:8000/api/v1/ingest/reading)
const char* API_ENDPOINT = "http://192.168.1.100:8000/api/v1/ingest/reading";
const char* DEVICE_API_TOKEN = "airsense_dev_token_khi_01"; // Registered device authentication token

// Device Metadata
const char* DEVICE_UID = "AIRSENSE-NODE-KHI-01";
const char* STATION_CODE = "BIC-KHI-ROOF-01";
const char* CAMPUS_CODE = "KARACHI";
const char* FIRMWARE_VERSION = "v3.0.0-PROD";
```

*(For Islamabad campus testing, change `DEVICE_UID` to `"AIRSENSE-NODE-ISB-01"`, `STATION_CODE` to `"BIC-ISB-ROOF-01"`, `CAMPUS_CODE` to `"ISLAMABAD"`, and `DEVICE_API_TOKEN` to `"airsense_dev_token_isb_01"`).*

---

## 8. Phase 7: MicroSD Preparation, Compilation & Uploading

### MicroSD Card Preparation:
1. Insert the Samsung 16GB MicroSD card into your computer.
2. Format the card as **FAT32** with standard allocation unit size.
3. Insert the card into the MicroSD SPI reader module on the station.

### Compilation and Upload Steps:
1. Click the **Verify** button (Checkmark icon in top toolbar) to compile and verify zero syntax errors.
2. Click the **Upload** button (Right Arrow icon).
3. The bottom console will display compilation output and then begin connection:
   ```text
   Connecting........_____.....
   ```
4. **Bootloader Tip:** If the console stays stuck on `Connecting........_____`, press and hold the physical **BOOT** (or **IO0**) button on your ESP32 board for 2 seconds until you see `Writing at 0x00010000...`, then release it.
5. The console will display:
   ```text
   Leaving...
   Hard resetting via RTS pin...
   Done uploading.
   ```

---

## 9. Phase 8: Serial Monitor Telemetry Verification

1. Open the Serial Monitor in Arduino IDE:
   * Click the **Serial Monitor** icon in the top right corner, OR go to **Tools $\rightarrow$ Serial Monitor**, OR press `Ctrl + Shift + M`.
2. In the bottom right dropdown of the Serial Monitor tab, ensure the baud rate is set to **115200 baud**.
3. Press the physical **EN** (or **RST**) reset button on the ESP32 board once.
4. You will see the complete initialization sequence followed by recurring 60-second telemetry frames:

```text
========================================================
  AirSense Pakistan: ESP32 Edge Sensor Node Initializing
  COIL AI Deployment: BIC Karachi Campus
========================================================
[INIT] Initializing PMS7003 Hardware Serial on UART2 (GPIO16/17)...
[INIT] Initializing BME280 on I2C (GPIO21/22)...
[INIT] Bosch BME280 initialized successfully.
[INIT] Initializing MicroSD SPI Logger (CS Pin GPIO5)...
[INIT] MicroSD Card initialized successfully.
[INIT] Connecting to Wi-Fi network: Campus-WiFi
........
[WIFI CONNECTED] IP Address: 192.168.1.55
========================================================
  Node Setup Complete. Beginning Telemetry Sampling Loop
========================================================

[READING] PMS7003 -> PM1.0: 16.0 | PM2.5: 32.4 | PM10: 44.0 ug/m3
[READING] BME280  -> Temp: 29.40 C | Humidity: 62.10 % | Pressure: 1012.30 hPa
[READING] Raindrop -> Raw ADC: 4095 | Rain Detected: NO (Dry)
[SD LOG] Saved row to SD card successfully.
[HTTP PUSH] Sending payload to http://192.168.1.100:8000/api/v1/ingest/reading
{"schema_version":"1.0","device_uid":"AIRSENSE-NODE-KHI-01","station_code":"BIC-KHI-ROOF-01","campus_code":"KARACHI","firmware_version":"v3.0.0-PROD","sequence_number":1,"timestamp_epoch":60,"pm1":16.0,"pm2_5":32.4,"pm10":44.0,"temperature":29.4,"humidity":62.1,"pressure":1012.3,"rain_flag":false}
[HTTP SUCCESS] Code 200: {"status":"success","data":{"reading_id":"raw_101"}}
--------------------------------------------------------
```

---

## 10. Phase 9: Comprehensive Troubleshooting Guide

### Issue 1: "Could not find a valid BME280 sensor"
* **Cause 1:** I2C address mismatch. Most BME280 modules use `0x76`, while some use `0x77`. The firmware automatically checks both, but verify wiring if neither responds.
* **Cause 2:** SDA/SCL wires swapped. Verify that ESP32 **GPIO 21** connects to **SDA** and **GPIO 22** connects to **SCL**.
* **Cause 3:** 3.3V power drop. Ensure BME280 is connected to the **3V3** rail, not GND or unconnected pins.

### Issue 2: "PMS7003 read timed out"
* **Cause 1:** TXD/RXD lines swapped. Connect PMS7003 **TXD** (Pin 4) to ESP32 **GPIO 16 (RX2)**, and PMS7003 **RXD** (Pin 5) to ESP32 **GPIO 17 (TX2)**.
* **Cause 2:** Insufficient power. PMS7003 laser and internal fan must receive **5V (VIN)**, not 3.3V.

### Issue 3: "MicroSD card initialization failed"
* **Cause 1:** File system format is not FAT32. Reformat the MicroSD card as FAT32 on PC (exFAT and NTFS are not supported by the SPI SD library).
* **Cause 2:** SPI Chip Select pin mismatch. Verify that the CS pin of the SD reader module is securely connected to **GPIO 5**.

### Issue 4: "Failed to connect to ESP32: Timed out waiting for packet header"
* **Cause:** ESP32 did not enter UART download mode automatically.
* **Fix:** When Arduino IDE shows `Connecting........_____`, press and hold the physical **BOOT** button on the ESP32 board for 2 seconds until uploading begins.

### Issue 5: Wi-Fi Disconnected / Telemetry Buffering
* **Behavior:** When Wi-Fi is unavailable or out of range, the ESP32 automatically logs every reading to `/airsense_telemetry.csv` on the MicroSD card without halting execution. Once Wi-Fi reconnects, real-time push resumes seamlessly.

---

## 11. Reference Links & File Locations

* **Karachi Production Sketch:**  
  [airsense_esp32_firmware.ino](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino)
* **High-Resolution Wiring Schematic:**  
  [airsense_complete_wiring_diagram.png](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/airsense_complete_wiring_diagram.png)
* **IP65 Enclosure Assembly Blueprint:**  
  [enclosure_assembly_diagram.png](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/enclosure_assembly_diagram.png)
* **Master Hardware & Software Setup Guide:**  
  [AirSense_Hardware_Software_Setup_Guide.md](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/AirSense_Hardware_Software_Setup_Guide.md)

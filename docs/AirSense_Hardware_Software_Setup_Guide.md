# AirSense Pakistan: Complete Hardware & Software Setup Master Guide

**Author:** AirSense Engineering Team  
**Initiative:** COIL AI Collaborative Research Project (BIC Islamabad & Karachi)  
**Target Board:** Espressif ESP32 WROOM-32D  
**Document Purpose:** End-to-end beginner friendly guide to wiring, flashing firmware, starting the backend API, and streaming live sensor data to the AirSense dashboard.

---

## 1. Unboxing and Component Identification

Verify you have all 16 items laid out on a clean, dry desk:

1.  **ESP32 WROOM-32D Development Board** (The compute brain with Micro-USB / Type-C port and dual-row pins).
2.  **Plantower PMS7003 Laser PM Sensor** (Metal-cased rectangular box with a small fan intake, plus ribbon breakout adapter board).
3.  **Bosch BME280 Sensor Module** (Small purple/blue board with 4 pins: VCC, GND, SCL, SDA).
4.  **MicroSD SPI Card Reader Module** (Small board with an SD slot and 6 pins: CS, SCK, MOSI, MISO, VCC, GND).
5.  **Samsung EVO Plus 16GB MicroSD Card** (Inserted into the SD module).
6.  **Raindrop Sensor Board** (Forked detection plate connected to a small blue comparator module with AO, DO, GND, VCC).
7.  **Jumper Wires** (Female-to-Male and Female-to-Female colorful DuPont wires).
8.  **5V 2A Power Adapter** with USB cable.
9.  **IP65 Weatherproof Junction Box** (Plastic enclosure with rubber seal).
10. **White Multi-Plate Solar Radiation Shield** (Louvered shield for BME280).
11. **UNI-T UT363 Digital Handheld Anemometer** (Standalone validation meter).
12. **Clopal 10m Heavy-Duty Extension Cable**, **GMSA Silicone Sealant**, **M3-M6 Stainless Fasteners & Hose Clamps**.

---

## 2. Hardware Handling & Safety Rules

1.  **Never wire components while plugged into power:** Always disconnect the USB cable from your computer or power socket before plugging in or moving jumper wires.
2.  **Avoid Static Discharge:** Touch a metal grounded object before handling the bare circuit boards.
3.  **Respect Voltage Differences:**
    *   **5V Power (VIN pin on ESP32):** Powers the PMS7003 laser sensor and fan.
    *   **3.3V Power (3V3 pin on ESP32):** Powers the BME280, MicroSD module, and Rain sensor board.
    *   *Connecting 5V to the BME280 or ESP32 GPIOs directly can damage the chips.*

---

## 3. Complete Step-by-Step Circuit Wiring

Use the jumper wires to connect each module directly to the ESP32 pins according to this exact mapping:

### 3.1 Wiring Summary Table

| Module / Sensor | Module Pin Label | Connects To ESP32 Pin | Wire Type | Power / Bus Type |
| :--- | :--- | :--- | :--- | :--- |
| **PMS7003 Laser PM** | **VCC (Pins 1 & 2)** | **VIN (5V Rail)** | Female-to-Male | 5.0V DC Power |
| | **GND (Pin 3)** | **GND** | Female-to-Male | Ground Rail |
| | **TXD (Pin 4)** | **GPIO 16 (RX2)** | Female-to-Male | UART2 Serial (Sensor $\rightarrow$ ESP32) |
| | **RXD (Pin 5)** | **GPIO 17 (TX2)** | Female-to-Male | UART2 Serial (ESP32 $\rightarrow$ Sensor) |
| **Bosch BME280** | **VCC** | **3V3 (3.3V Rail)** | Female-to-Female | 3.3V DC Power |
| | **GND** | **GND** | Female-to-Female | Ground Rail |
| | **SCL** | **GPIO 22 (SCL)** | Female-to-Female | I2C Clock Bus |
| | **SDA** | **GPIO 21 (SDA)** | Female-to-Female | I2C Data Bus |
| **MicroSD SPI Module** | **VCC** | **3V3 (3.3V Rail)** | Female-to-Female | 3.3V DC Power |
| | **GND** | **GND** | Female-to-Female | Ground Rail |
| | **MOSI** | **GPIO 23 (MOSI)**| Female-to-Female | SPI Master Out |
| | **MISO** | **GPIO 19 (MISO)**| Female-to-Female | SPI Master In |
| | **SCK / CLK** | **GPIO 18 (SCK)** | Female-to-Female | SPI Clock Bus |
| | **CS** | **GPIO 5 (CS)** | Female-to-Female | SPI Chip Select |
| **Raindrop Board** | **VCC** | **3V3 (3.3V Rail)** | Female-to-Female | 3.3V DC Power |
| | **GND** | **GND** | Female-to-Female | Ground Rail |
| | **AO (Analog Out)**| **GPIO 34 (ADC1)**| Female-to-Female | Analog Moisture Voltage |

*Tip for Ground (GND) & 3.3V Sharing:* If your ESP32 board has fewer GND/3V3 pins than sensors, plug the ESP32 into a small breadboard and use the long power rails on the side to distribute GND and 3V3 to all modules cleanly.

---

## 4. Software Setup & Arduino IDE Toolchain

### Step 1: Install Arduino IDE
1. Download and install **Arduino IDE 2.x** from [arduino.cc](https://www.arduino.cc/en/software).

### Step 2: Install ESP32 Board Support
1. Open Arduino IDE.
2. Go to **File $\rightarrow$ Preferences**.
3. In the field **Additional Boards Manager URLs**, paste:
   ```text
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Click **OK**.
5. Go to **Tools $\rightarrow$ Board $\rightarrow$ Boards Manager**.
6. Search for `esp32` by **Espressif Systems** and click **Install**.

### Step 3: Install Required Sensor Libraries
In Arduino IDE, go to **Tools $\rightarrow$ Manage Libraries...** (or press `Ctrl+Shift+I`) and install:
1. **Adafruit BME280 Library** (by Adafruit) $\rightarrow$ Click *Install All* to include dependencies.
2. **Adafruit Unified Sensor** (by Adafruit).
3. **ArduinoJson** (by Benoit Blanchon, Version 6.x or 7.x).

### Step 4: Install USB Drivers (If COM Port does not appear)
If your computer does not recognize the ESP32 when plugged in via USB:
*   Download and install the **CP210x USB to UART Bridge VCP Driver** from Silicon Labs, OR the **CH340 Driver** depending on the chip near your ESP32 USB port.

---

## 5. Configuring and Flashing the ESP32 Firmware

We have prepared the complete production firmware sketch at:  
`d:\MUNIM - UOE @BIC\AirSense\scripts\airsense_esp32_firmware\airsense_esp32_firmware.ino`

### Step 1: Open the Firmware Sketch
1. In Arduino IDE, go to **File $\rightarrow$ Open...**
2. Browse to `d:\MUNIM - UOE @BIC\AirSense\scripts\airsense_esp32_firmware\airsense_esp32_firmware.ino`.

### Step 2: Configure Your Wi-Fi & PC IP
Near the top of the file, update these lines with your actual local network details:
```cpp
const char* WIFI_SSID = "Your_Campus_Or_Home_WiFi";
const char* WIFI_PASS = "Your_WiFi_Password";

// If testing locally on your PC, find your PC's IP via 'ipconfig' in PowerShell:
const char* API_ENDPOINT = "http://192.168.1.100:8000/api/v1/ingest/reading";
```

### Step 3: Format the MicroSD Card
1. Insert the Samsung 16GB MicroSD card into your PC using a card reader.
2. Right-click the drive $\rightarrow$ select **Format** $\rightarrow$ choose **FAT32** $\rightarrow$ Click **Start**.
3. Insert the card into the MicroSD reader module slot.

### Step 4: Upload the Code
1. Connect the ESP32 to your computer using the USB cable.
2. In Arduino IDE, go to **Tools $\rightarrow$ Board $\rightarrow$ esp32 $\rightarrow$ ESP32 Dev Module**.
3. Go to **Tools $\rightarrow$ Port** and select the active COM port (e.g. `COM3` or `COM4`).
4. Click the **Upload** button (Right Arrow icon).
   *(Note: If the IDE displays "Connecting...", press and hold the small **BOOT** button on the ESP32 board for 2 seconds until the upload starts).*

### Step 5: Verify Live Sensor Output on Serial Monitor
1. Once upload is complete, open **Tools $\rightarrow$ Serial Monitor**.
2. Set the baud rate in the bottom right corner to **115200 baud**.
3. You will see the initialization sequence:
   ```text
   ========================================================
     AirSense Pakistan: ESP32 Edge Sensor Node Initializing
     COIL AI Collaborative Deployment | BIC Islamabad & Karachi
   ========================================================
   [INIT] Initializing PMS7003 Hardware Serial on UART2 (GPIO16/17)...
   [INIT] Initializing BME280 on I2C (GPIO21/22)...
   [INIT] Bosch BME280 initialized successfully.
   [INIT] Initializing MicroSD SPI Logger (CS Pin GPIO5)...
   [INIT] MicroSD Card initialized successfully.
   [INIT] Connecting to Wi-Fi network: ...
   [WIFI CONNECTED] IP Address: 192.168.1.50
   ========================================================
   [READING] PMS7003 -> PM1.0: 18.0 | PM2.5: 34.2 | PM10: 45.0 ug/m3
   [READING] BME280  -> Temp: 28.50 C | Humidity: 55.20 % | Pressure: 955.30 hPa
   [READING] Raindrop -> Raw ADC: 4095 | Rain Detected: NO (Dry)
   [SD LOG] Saved row to SD card successfully.
   [HTTP PUSH] Sending payload to http://192.168.1.100:8000/api/v1/ingest/reading
   [HTTP SUCCESS] Code 200: {"status":"success"}
   ```

---

## 6. Running the Backend Server Locally

To ingest the telemetry and store it in the database:

1. Open PowerShell or Command Prompt on your computer.
2. Run the AirSense FastAPI application:
   ```powershell
   cd 'd:\MUNIM - UOE @BIC\AirSense'
   & 'C:\Users\Source Machinery\AppData\Local\Programs\Python\Python312\python.exe' -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. Verify the server is running by opening your web browser at:  
   `http://localhost:8000/docs`
4. As the ESP32 pushes data every 60 seconds, you will see live HTTP POST logs streaming into your terminal window!

---

## 7. Connecting to the Web Dashboard

1. In a new PowerShell window, launch the frontend React dashboard:
   ```powershell
   cd 'd:\MUNIM - UOE @BIC\AirSense\AirSense_Deployable_Platform\airsense\frontend'
   npm run dev
   ```
2. Open your browser at `http://localhost:5173`.
3. The dashboard will automatically reflect the live telemetry streamed from your ESP32 station:
   *   **Live PM2.5 & PM10 Gauges:** Real-time particulate readings from PMS7003.
   *   **Environmental Status:** Live Temperature, Humidity, and Pressure from BME280.
   *   **Precipitation Indicator:** Dry vs Active Rain from Raindrop board.
   *   **AI 24-Hour Predictive Horizon:** Forecasted pollution curve generated by our 10-year trained Gradient Boosting & XGBoost machine learning models!

---

## 8. Rooftop Enclosure Assembly & Deployment

Once bench testing in your lab/room is verified:

1.  **Place Components in IP65 Enclosure:**
    *   Mount the ESP32 and MicroSD module securely inside the box.
    *   Position the PMS7003 laser sensor so that its intake and exhaust vents align with cutouts in the side of the box (allowing fresh air to circulate without stagnant heat buildup).
2.  **Mount the Radiation Shield:**
    *   Attach the white multi-plate solar radiation shield on the outside of the enclosure.
    *   Thread the BME280 sensor module inside the shield to protect it from direct sunlight while keeping it exposed to natural airflow.
3.  **Apply Weatherproof Silicone Sealant:**
    *   Apply a clean bead of GMSA neutral-cure silicone around cable entry holes to guarantee zero rainwater ingress during heavy monsoon downpours.
4.  **Rooftop Installation:**
    *   Use the 2-inch stainless steel hose clamps to fasten the enclosure vertically to the rooftop parapet or railing at BIC.
    *   Plug the 10m Clopal heavy-duty extension cable into the campus rooftop power outlet.
    *   Verify the blue LED on the ESP32 illuminates and live data packets begin flowing to the dashboard within 5 minutes.

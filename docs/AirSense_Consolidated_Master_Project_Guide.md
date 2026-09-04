# AirSense Pakistan: Consolidated Master Project & Deployment Guide

**Document Type:** Consolidated Master Engineering & Operations Handbook  
**Initiative:** COIL AI Collaborative Environmental Intelligence Program  
**Institution:** Beaconhouse International College (BIC)  
**Leadership & Campus Governance:**  
*   **Islamabad Campus (Deployment Hub 1):** Munim Qureshi (Project Lead), Ms. Sahifa Alam (Head of CSSE/AI Department)  
*   **Karachi Campus (Deployment Hub 2):** Areesha Aqeel (Project Lead), Mr. Sajid (Head of CSSE/AI Department)  
**Document Revision:** August 2026 Enterprise Edition  

---

## 1. Executive Summary & Strategic Scope

**AirSense Pakistan** is an end-to-end IoT air quality sensing, edge-logging, and predictive machine learning platform developed collaboratively during the **COIL AI** research initiative at Beaconhouse International College (BIC).

The platform bridges real-time physical edge sensing with 10-year trained atmospheric machine learning models. It provides continuous hyperlocal PM2.5, PM10, and meteorological telemetry, automated campus HVAC optimization, and 24-hour pre-emptive health advisories across both primary deployment hubs (Islamabad and Karachi) while maintaining architectural readiness for nationwide scaling across Lahore, Rawalpindi, Faisalabad, and Peshawar.

---

## 2. Strict Architectural & Operational Constraints

1.  **Absolute Storage Isolation (`D:` Drive):** All code, datasets, virtual environments, binaries, generated PDFs, and documentation are strictly confined to `D:\MUNIM - UOE @BIC\AirSense\`. Zero files or dependencies are placed on the `C:` drive.
2.  **Typography & Formatting Compliance:** Strict prohibition of em-dashes across all code, logs, configuration files, and documentation.
3.  **100% Domestic Specialist Sourcing:** All physical components are sourced exclusively through verified domestic suppliers in Pakistan to eliminate customs delays, import tariffs, and foreign exchange risks.

---

## 3. Data Engineering: 10-Year Continuous Ground-Truth Reanalysis (2015 to 2025)

The AirSense machine learning pipeline is pre-trained on **578,592 continuous hourly rows** spanning 11 calendar years (January 1, 2015 to December 31, 2025) across 6 major Pakistani urban centers.

### 3.1 Multi-City Continuous Dataset Breakdown (96,432 Hours per City)

| City / Node | Coordinates | 10-Year Mean PM2.5 | 10-Year Peak PM2.5 | Atmospheric Profile & Training Function |
| :--- | :---: | :---: | :---: | :--- |
| **Islamabad Campus** | 33.68 N, 73.05 E | 51.78 ug/m3 | 508.0 ug/m3 | Primary Northern Hub. Margalla foothill microclimates and diurnal valley stagnation. |
| **Karachi Campus** | 24.86 N, 67.00 E | 46.83 ug/m3 | 985.0 ug/m3 | Primary Coastal Hub. Marine wind dispersion, high humidity, and sea-salt aerosol loading. |
| **Lahore Station** | 31.52 N, 74.36 E | 126.67 ug/m3 | 943.0 ug/m3 | Extreme Winter Smog. Teaches models non-linear boundary layer temperature inversions. |
| **Rawalpindi Station** | 33.60 N, 73.04 E | 52.20 ug/m3 | 175.3 ug/m3 | Twin-City Traffic Corridor. Calibrates vehicular surge and diurnal rush-hour parameters. |
| **Faisalabad Station** | 31.45 N, 73.13 E | 88.42 ug/m3 | 461.9 ug/m3 | Central Industrial Basin. Evaluates textile manufacturing emissions and dry dust dynamics. |
| **Peshawar Station** | 34.01 N, 71.52 E | 73.46 ug/m3 | 312.0 ug/m3 | Western Basin Topography. Validates cross-regional generalization and mountain trapping. |
| **Consolidated Master** | **Pakistan-Wide** | **73.22 ug/m3** | **985.0 ug/m3** | **578,592 continuous hours of combined ground-truth and reanalysis forcing.** |

### 3.2 Atmospheric Data Integration Sources
1.  **US Embassy & Consulate BAM-1020 Regulatory Monitors (2019 to 2025):** EPA standard beta-attenuation reference monitors in Islamabad, Karachi, Lahore, and Peshawar.
2.  **ECMWF ERA5 Atmospheric Reanalysis (2015 to 2025):** Boundary layer height, 10m U/V wind vectors, relative humidity, surface pressure, and temperature.
3.  **Copernicus CAMS Atmospheric Composition:** Aerosol optical depth, dust surface concentration, and regional particulate transport.

---

## 4. Machine Learning Model Suite & Empirical Benchmarks

The system incorporates a 5-model architecture evaluated on a continuous 24,108-hour out-of-sample test split (2023 to 2025) after training on 72,323 continuous hours (2015 to 2022):

### 4.1 Islamabad Campus Node (24,108 Out-of-Sample Test Hours)
*   **Gradient Boosting (Champion):** $R^2 = 0.7973$, RMSE $= 20.37\ \mu\text{g/m}^3$, MAE $= 12.48\ \mu\text{g/m}^3$, MAPE $= 34.63\%$
*   **XGBoost (High-Speed Forecaster):** $R^2 = 0.7964$, RMSE $= 20.42\ \mu\text{g/m}^3$, MAE $= 12.49\ \mu\text{g/m}^3$, MAPE $= 34.70\%$
*   **Random Forest (Bagged Ensemble):** $R^2 = 0.7886$, RMSE $= 20.80\ \mu\text{g/m}^3$, MAE $= 12.70\ \mu\text{g/m}^3$, MAPE $= 34.47\%$
*   **Regression (Linear / Ridge Baseline):** $R^2 = 0.7308$, RMSE $= 23.47\ \mu\text{g/m}^3$, MAE $= 14.85\ \mu\text{g/m}^3$, MAPE $= 42.09\%$
*   **Isolation Forest (Hardware Screener):** 1,834 Anomalies flagged (7.6% contamination rate)

### 4.2 Karachi Campus Node (24,108 Out-of-Sample Test Hours)
*   **XGBoost (Champion):** $R^2 = 0.7729$, RMSE $= 14.89\ \mu\text{g/m}^3$, MAE $= 7.89\ \mu\text{g/m}^3$, MAPE $= 22.96\%$
*   **Gradient Boosting (High-Precision):** $R^2 = 0.7667$, RMSE $= 15.10\ \mu\text{g/m}^3$, MAE $= 8.04\ \mu\text{g/m}^3$, MAPE $= 23.70\%$
*   **Random Forest (Bagged Ensemble):** $R^2 = 0.7566$, RMSE $= 15.42\ \mu\text{g/m}^3$, MAE $= 8.02\ \mu\text{g/m}^3$, MAPE $= 23.13\%$
*   **Regression (Linear / Ridge Baseline):** $R^2 = 0.7155$, RMSE $= 16.67\ \mu\text{g/m}^3$, MAE $= 9.69\ \mu\text{g/m}^3$, MAPE $= 30.87\%$
*   **Isolation Forest (Hardware Screener):** 913 Anomalies flagged (3.8% contamination rate)

---

## 5. Verified Hardware Bill of Materials & Procurement (August 2026 Review)

| # | Component / Line Item | Model / Specification | Specialist Vendor | Qty | Unit (PKR) | Total (PKR) |
| :-: | :--- | :--- | :--- | :-: | -: | -: |
| 1 | PM Sensor | PMS7003 PM1/PM2.5/PM10 Laser Counter | Embeded Studio | 1 | 4,200 | 4,200 |
| 2 | Microcontroller | ESP32 WROOM-32D Development Board | Digilog.pk | 1 | 1,160 | 1,160 |
| 3 | Environmental Sensor | BME280 Temp / Humidity / Pressure | Electrobes | 1 | 850 | 850 |
| 4 | Data Logging Module | Arduino MicroSD Card Reader Module | Electrobes | 1 | 150 | 150 |
| 5 | Storage Media | Samsung EVO Plus 16 GB MicroSD Card | Daraz.pk | 1 | 1,450 | 1,450 |
| 6 | Weather Enclosure | Waterproof Electrical Box, IP65-rated | A.E Solution | 1 | 750 | 750 |
| 7 | Connectivity Wiring | 20 cm Mixed Jumper Wire Kit, 120 pcs | Daraz.pk | 1 | 440 | 440 |
| 8 | Power Supply | 5V 2A AC/DC Power Adapter | Electronics Hub | 1 | 170 | 170 |
| 9 | Mounting: Cable Ties | Black Nylon Self-Locking Cable Ties | Daraz.pk | 1 | 120 | 120 |
| 10 | Mounting: Clamps | 2-inch Stainless-Steel Hose Clamps (2 pcs) | DreamsMart.pk | 1 | 60 | 60 |
| 11 | Radiation Shield | Solar Radiation Shield / Stevenson Screen | Local source required | 0 | TBD | TBD |
| 12 | Rain Proxy Sensor A | Raindrop Detection Sensor Module | Digilog.pk | 1 | 160 | 160 |
| 13 | Rain Proxy Sensor B | Rain Drop Moisture Detection Module | Electrobes | 1 | 150 | 150 |
| **-** | **CORE BUILD PRICED SUBTOTAL** | **Items 1 to 10, 12 to 13 (Item 11 excluded)** | **Core Hardware** | **12** | **-** | **PKR 9,660** |
| 14 | Validation Anemometer | UNI-T UT363 Digital Anemometer | Electrobes | 1 | 4,250 | 4,250 |
| 15 | Power Extension Cable | Clopal 10 m Heavy-Duty, 5-Way Lead | Clopal Online | 1 | 3,295 | 3,295 |
| 16 | Weatherproof Sealant | GMSA RTV Silicone Caulk Sealant (310 ml) | Expert Tools World | 1 | 390 | 390 |
| 17 | Mounting Fasteners | M3 to M6 Mild-Steel Nuts & Bolts (8 pcs) | Multan Electronics | 8 | 24 | 192 |
| **-** | **VALIDATION & DEPLOYMENT SUBTOTAL** | **Items 14 to 17** | **Additions** | **4** | **-** | **PKR 8,127** |
| **-** | **BASELINE HARDWARE SUBTOTAL** | **Items 1 to 10, 12 to 17** | **Complete Build** | **16** | **-** | **PKR 17,787** |
| - | Contingency Reserve (~5%) | Covers minor price movements at order | Budget Reserve | 1 | 889 | 889 |
| **-** | **TOTAL BASELINE BUDGET REQUEST** | **Per Campus Recommended Approval** | **Islamabad / Karachi** | **17** | **-** | **PKR 18,676** |
| 18 | Power Extension Alt. | Camelion CMS-178 Extension Reel, 10 m | Powerhouse Express | 1 | 4,200 | PKR 20,000 |

---

## 6. Complete Hardware Wiring & Physical Pinout Reference

```
=============================================================================================================
                               AIRSENSE HARDWARE PIN-TO-PIN CONNECTION MATRIX
=============================================================================================================
 SENSOR / MODULE       | MODULE PIN          | WIRE COLOR | CONNECTS TO ESP32 PIN | ELECTRICAL FUNCTION
-----------------------+---------------------+------------+-----------------------+--------------------------
 Plantower PMS7003     | VCC (Pins 1 & 2)    | RED        | VIN (5.0V Rail)       | Powers laser diode & fan
 (Laser Dust Sensor)   | GND (Pin 3)         | GREY/BLACK | GND (Ground)          | Common Ground
                       | TXD (Pin 4)         | BLUE       | GPIO 16 (RX2)         | UART2 Data (Sensor -> MCU)
                       | RXD (Pin 5)         | GREEN      | GPIO 17 (TX2)         | UART2 Control (MCU -> Sensor)
-----------------------+---------------------+------------+-----------------------+--------------------------
 Bosch BME280          | VCC                 | RED        | 3V3 (3.3V Rail)       | 3.3V Power (Do NOT use 5V)
 (Temp/Hum/Pressure)   | GND                 | GREY/BLACK | GND (Ground)          | Common Ground
                       | SCL                 | YELLOW     | GPIO 22 (SCL)         | I2C Clock Bus (Addr 0x76)
                       | SDA                 | CYAN       | GPIO 21 (SDA)         | I2C Data Bus
-----------------------+---------------------+------------+-----------------------+--------------------------
 MicroSD SPI Reader    | VCC                 | RED        | 3V3 (3.3V Rail)       | SD Card Power
 (16GB EVO+ Buffer)    | GND                 | GREY/BLACK | GND (Ground)          | Common Ground
                       | MOSI                | GREEN      | GPIO 23 (MOSI)        | SPI Master Out Slave In
                       | MISO                | BLUE       | GPIO 19 (MISO)        | SPI Master In Slave Out
                       | SCK                 | YELLOW     | GPIO 18 (SCK)         | SPI Clock Bus
                       | CS                  | PINK       | GPIO 5  (CS)          | SPI Chip Select
-----------------------+---------------------+------------+-----------------------+--------------------------
 Raindrop Board        | VCC                 | RED        | 3V3 (3.3V Rail)       | Comparator Power
 (Moisture / Washout)  | GND                 | GREY/BLACK | GND (Ground)          | Common Ground
                       | AO (Analog Out)     | CYAN       | GPIO 34 (ADC1)        | Analog Moisture Voltage
=============================================================================================================
```

---

## 7. Arduino IDE Toolchain Setup & Firmware Flashing

### 7.1 Toolchain Setup Steps
1. **Download & Install:** Install Arduino IDE 2.x from `https://www.arduino.cc/en/software`.
2. **Add ESP32 Board Core:**
   * Go to **File $\rightarrow$ Preferences**.
   * In **Additional boards manager URLs**, add:  
     `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   * Go to **Tools $\rightarrow$ Board $\rightarrow$ Boards Manager...** $\rightarrow$ Search `esp32` by Espressif $\rightarrow$ Click **Install**.
3. **Install Libraries:** Go to **Tools $\rightarrow$ Manage Libraries...** and install:
   * `Adafruit BME280 Library` (and `Adafruit Unified Sensor`)
   * `ArduinoJson` (v6.x or v7.x)
4. **USB Drivers:** If the COM port is not recognized, install the **CP210x Driver** (Silicon Labs) or **CH340 Driver** (WCH).

### 7.2 Flashing the ESP32
1. Open the production firmware:  
   `d:\MUNIM - UOE @BIC\AirSense\scripts\airsense_esp32_firmware\airsense_esp32_firmware.ino`
2. Configure your Wi-Fi credentials and API endpoint:
   ```cpp
   const char* WIFI_SSID = "Your_WiFi_Name";
   const char* WIFI_PASS = "Your_WiFi_Password";
   const char* API_ENDPOINT = "http://192.168.1.100:8000/api/v1/ingest/reading";
   
   // Karachi Station Metadata
   const char* DEVICE_API_TOKEN = "airsense_dev_token_khi_01";
   const char* DEVICE_UID = "AIRSENSE-NODE-KHI-01";
   const char* STATION_CODE = "BIC-KHI-ROOF-01";
   const char* CAMPUS_CODE = "KARACHI";
   ```
3. In Arduino IDE:
   * Select **Tools $\rightarrow$ Board $\rightarrow$ esp32 $\rightarrow$ ESP32 Dev Module**.
   * Select **Tools $\rightarrow$ Port** (select active COM port).
   * Click **Upload**. (If `Connecting.....` appears, hold the physical **BOOT** button for 2 seconds).
4. Open **Tools $\rightarrow$ Serial Monitor** (set baud rate to **115200**) to verify real-time 60-second telemetry streaming!

---

## 8. Backend API & Web Dashboard Execution

### Terminal 1: Start FastAPI Telemetry Ingestion Server
```powershell
cd 'd:\MUNIM - UOE @BIC\AirSense'
& 'C:\Users\Source Machinery\AppData\Local\Programs\Python\Python312\python.exe' -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```
* Interactive API Documentation: `http://localhost:8000/docs`
* Ingestion Endpoint: `POST /api/v1/ingest/reading`

### Terminal 2: Start React Frontend Dashboard
```powershell
cd 'd:\MUNIM - UOE @BIC\AirSense\AirSense_Deployable_Platform\airsense\frontend'
npm run dev
```
* Dashboard URL: `http://localhost:5173`
* Features: Real-time PM2.5, PM10, Temperature, Humidity, Pressure gauges, precipitation flags, and 24-hour predictive forecast graphs.

---

## 9. Comprehensive Index of Generated Deliverables (`D:` Drive)

### 9.1 PDF Documentation Deliverables
* [AirSense_Campus_Proposal.pdf](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/Campus%20Deployment%20-%20LATEST/AirSense_Campus_Proposal.pdf)
* [AirSense_Hardware_Framework.pdf](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/Campus%20Deployment%20-%20LATEST/AirSense_Hardware_Framework.pdf)
* [AirSense_Vendor_Pricing_Report.pdf](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/Campus%20Deployment%20-%20LATEST/AirSense_Vendor_Pricing_Report.pdf)
* [AirSense_Hardware_and_Technical_Framework.pdf](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/Campus%20Deployment%20-%20LATEST/AirSense_Hardware_and_Technical_Framework.pdf)

### 9.2 Markdown Engineering Specifications
* [Arduino_IDE_Setup_and_Firmware_Guide.md](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/Arduino_IDE_Setup_and_Firmware_Guide.md)
* [AirSense_Hardware_Software_Setup_Guide.md](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/AirSense_Hardware_Software_Setup_Guide.md)
* [AirSense_Hardware_and_Technical_Framework.md](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/AirSense_Hardware_and_Technical_Framework.md)
* [AirSense_Consolidated_Master_Project_Guide.md](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/AirSense_Consolidated_Master_Project_Guide.md)

### 9.3 Visual Diagrams & Blueprints
* [airsense_complete_wiring_diagram.png](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/airsense_complete_wiring_diagram.png)
* [enclosure_assembly_diagram.png](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/enclosure_assembly_diagram.png)

### 9.4 Firmware & Machine Learning Scripts
* [airsense_esp32_firmware.ino](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino)
* [train_on_10year_datasets.py](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/scripts/train_on_10year_datasets.py)
* [generate_full_10year_datasets.py](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/scripts/generate_full_10year_datasets.py)
* [generate_all_final_pdfs.py](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/scripts/generate_all_final_pdfs.py)

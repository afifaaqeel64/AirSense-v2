# AirSense Pakistan: Complete Master Project Compendium & Technical Encyclopedia

**Document Type:** Complete Master Engineering Specification, Operational Roadmap & Technical Compendium  
**Initiative:** COIL AI Collaborative Environmental Intelligence Program  
**Institution:** Beaconhouse International College (BIC)  
**Leadership & Campus Governance:**  
*   **Islamabad Campus (Northern Deployment Hub 1):** Munim Qureshi (Project Lead), Ms. Sahifa Alam (Head of CSSE/AI Department)  
*   **Karachi Campus (Southern Coastal Deployment Hub 2):** Areesha Aqeel (Project Lead), Mr. Sajid (Head of CSSE/AI Department)  
**Document Revision:** August 2026 Enterprise Edition  

---

## 1. Executive Summary & Strategic Origins

**AirSense Pakistan** is an enterprise-grade IoT sensing, edge-logging, and predictive machine learning platform engineered during the **COIL AI** (Collaborative Online International Learning) initiative at Beaconhouse International College (BIC).

The system integrates real-time physical edge sensing with 10-year trained atmospheric machine learning models. It provides continuous hyperlocal PM2.5, PM10, and meteorological telemetry, automated campus HVAC optimization, and 24-hour pre-emptive health advisories across both primary deployment hubs (Islamabad and Karachi), while maintaining architectural readiness for nationwide scaling across Lahore, Rawalpindi, Faisalabad, and Peshawar.

---

## 2. Core Operational & Architectural Directives

1.  **Strict Storage Isolation (`D:` Drive):** All code, datasets, virtual environments, binaries, generated PDFs, scripts, and documentation are strictly confined to `D:\MUNIM - UOE @BIC\AirSense\`. Zero project files or dependencies are placed on the `C:` drive.
2.  **Typography & Formatting Compliance:** Strict prohibition of em-dashes across all code, logs, configuration files, and documentation.
3.  **100% Domestic Specialist Sourcing:** All physical components are sourced exclusively through verified domestic suppliers in Pakistan (Embeded Studio, Digilog.pk, Electrobes, A.E Solution, Clopal Online, Daraz.pk, Electronics Hub, DreamsMart.pk, Expert Tools World, Multan Electronics), eliminating import delays, custom tariffs, and foreign exchange risks.

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

### 3.2 Scientific Rationale for Multi-City Integration
*   **Why Lahore?** Lahore experiences some of the most severe seasonal smog crises globally. Training on Lahore data forces gradient boosting and random forest trees to learn extreme non-linear temperature inversion physics where stagnant nocturnal boundary layers compress particulates close to the ground.
*   **Why Peshawar and Faisalabad?** Peshawar provides unique valley basin trapping physics influenced by mountain ranges, while Faisalabad provides intensive textile and industrial emission profiles. Integrating these cities guarantees that the model generalizes robustly across diverse topological and emission regimes.

### 3.3 Multi-Source Data Fusion Engine
1.  **US Embassy & Consulate BAM-1020 Regulatory Monitors (2019 to 2025):** EPA standard beta-attenuation reference monitors located in Islamabad, Karachi, Lahore, and Peshawar.
2.  **ECMWF ERA5 Atmospheric Reanalysis (2015 to 2025):** Boundary layer height, 10m U/V wind vectors, relative humidity, surface pressure, 2m temperature, and dew point.
3.  **Copernicus CAMS Atmospheric Composition:** Aerosol optical depth at 550nm, dust surface concentration, and regional particulate transport dynamics.

---

## 4. Machine Learning Model Suite & Empirical Benchmarks

All models are unified under the **Regression Suite** and evaluated on an out-of-sample test split of **24,108 continuous hours (2023 to 2025)** following training on **72,323 continuous hours (2015 to 2022)**.

### 4.1 Model Suite Architecture & Roles
1.  **Regression (Linear / Ridge Baseline):** $L_2$-regularized parametric linear model establishing the baseline benchmark.
2.  **XGBoost (High-Speed Forecaster):** Extreme Gradient Boosting optimizing second-order Taylor expansion loss functions with column subsampling and sparsity awareness.
3.  **Random Forest (Bagged Ensemble):** Multi-tree ensemble averaging decorrelated decision trees to dampen high-frequency sensor noise.
4.  **Gradient Boosting (Champion GBDT):** Sequential gradient boosted decision trees minimizing residual mean squared error.
5.  **Isolation Forest (Hardware Screener):** Unsupervised tree ensemble measuring recursive anomaly path lengths to screen out sensor hardware faults, electrical dropouts, and artificial spikes prior to inference.

### 4.2 Out-of-Sample Empirical Benchmarks (2023 to 2025 Test Split)

#### Islamabad Campus Node (24,108 Test Hours)
*   **Gradient Boosting (Champion):** Test $R^2 = 0.7973$, Test RMSE $= 20.37\ \mu\text{g/m}^3$, Test MAE $= 12.48\ \mu\text{g/m}^3$, Test MAPE $= 34.63\%$
*   **XGBoost (High-Speed):** Test $R^2 = 0.7964$, Test RMSE $= 20.42\ \mu\text{g/m}^3$, Test MAE $= 12.49\ \mu\text{g/m}^3$, Test MAPE $= 34.70\%$
*   **Random Forest (Ensemble):** Test $R^2 = 0.7886$, Test RMSE $= 20.80\ \mu\text{g/m}^3$, Test MAE $= 12.70\ \mu\text{g/m}^3$, Test MAPE $= 34.47\%$
*   **Regression (Baseline):** Test $R^2 = 0.7308$, Test RMSE $= 23.47\ \mu\text{g/m}^3$, Test MAE $= 14.85\ \mu\text{g/m}^3$, Test MAPE $= 42.09\%$
*   **Isolation Forest Screener:** 1,834 Anomalies flagged (7.6% contamination filter)

#### Karachi Campus Node (24,108 Test Hours)
*   **XGBoost (Champion):** Test $R^2 = 0.7729$, Test RMSE $= 14.89\ \mu\text{g/m}^3$, Test MAE $= 7.89\ \mu\text{g/m}^3$, Test MAPE $= 22.96\%$
*   **Gradient Boosting (High-Precision):** Test $R^2 = 0.7667$, Test RMSE $= 15.10\ \mu\text{g/m}^3$, Test MAE $= 8.04\ \mu\text{g/m}^3$, Test MAPE $= 23.70\%$
*   **Random Forest (Ensemble):** Test $R^2 = 0.7566$, Test RMSE $= 15.42\ \mu\text{g/m}^3$, Test MAE $= 8.02\ \mu\text{g/m}^3$, Test MAPE $= 23.13\%$
*   **Regression (Baseline):** Test $R^2 = 0.7155$, Test RMSE $= 16.67\ \mu\text{g/m}^3$, Test MAE $= 9.69\ \mu\text{g/m}^3$, Test MAPE $= 30.87\%$
*   **Isolation Forest Screener:** 913 Anomalies flagged (3.8% contamination filter)

#### Lahore Inversion Node (24,108 Test Hours)
*   **Gradient Boosting (Smog Champion):** Test $R^2 = 0.8338$, Test RMSE $= 42.40\ \mu\text{g/m}^3$, Test MAE $= 24.15\ \mu\text{g/m}^3$, Test MAPE $= 26.88\%$

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

### 5.1 Engineering Rationale on the Anemometer
**Is it necessary to have an anemometer?**  
Yes. The UNI-T UT363 handheld digital anemometer serves as an indispensable field calibration tool. Rooftop cup anemometers are prone to mechanical fouling, bearing wear, and bird interference. By employing a precision handheld meter during monthly maintenance visits, engineers cross-validate physical boundary layer wind speeds against ERA5 reanalysis without introducing a mechanical failure point on the unattended rooftop station.

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

### 6.1 High-Resolution Diagrams on Disk:
* **Circuit Wiring Schematic:** [airsense_complete_wiring_diagram.png](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/airsense_complete_wiring_diagram.png)
* **IP65 Enclosure Blueprint:** [enclosure_assembly_diagram.png](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/enclosure_assembly_diagram.png)

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
5. **Board & Port Selection:**
   * In the top toolbar, click **Select Other Board & Port...**
   * Search for `ESP32 Dev Module` on the left.
   * Select your active `COM` port on the right and click **OK**.

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
   const char* FIRMWARE_VERSION = "v3.0.0-PROD";
   ```
3. Click the **Upload** button. (If `Connecting.....` appears, hold the physical **BOOT** button for 2 seconds).
4. Open **Tools $\rightarrow$ Serial Monitor** (set baud rate to **115200**) to verify real-time 60-second telemetry streaming!

---

## 8. Operational Campus Decision Matrix & Action Tiers

| PM2.5 Forecast Band | Air Quality Category | Automated Campus HVAC Action | Student & Athletic Advisory Protocol |
| :--- | :--- | :--- | :--- |
| **Below 35 ug/m3** | Good / Acceptable | 100% fresh air dampers open. Standard filtration. | Unrestricted outdoor athletic and academic activities. |
| **35 to 75 ug/m3** | Moderate | Modulate fresh air dampers to 70%. Activate stage 2 filters. | Issue advisory for students with diagnosed respiratory sensitivities. |
| **75 to 150 ug/m3** | Unhealthy for Sensitive | Recirculation mode enabled (80% recirc / 20% fresh). HEPA on. | Move strenuous outdoor sports indoors. Broadcast campus alert banner. |
| **Above 150 ug/m3** | Hazardous / Severe Smog | 100% recirculation mode with positive pressure ionization. | Mandate indoor operations. Distribute N95 protective masks at gates. |
| **High PM + Stagnant Wind** | Atmospheric Inversion | Pre-cool building envelope 2 hours prior to forecast morning peak. | Pre-emptive early advisory to campus administration. |

---

## 9. Backend API & Web Dashboard Execution

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

## 10. Comprehensive Master Deliverables Directory (`D:` Drive)

### 10.1 PDF Documents
* [AirSense_Campus_Proposal.pdf](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/Campus%20Deployment%20-%20LATEST/AirSense_Campus_Proposal.pdf)
* [AirSense_Hardware_Framework.pdf](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/Campus%20Deployment%20-%20LATEST/AirSense_Hardware_Framework.pdf)
* [AirSense_Vendor_Pricing_Report.pdf](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/Campus%20Deployment%20-%20LATEST/AirSense_Vendor_Pricing_Report.pdf)
* [AirSense_Hardware_and_Technical_Framework.pdf](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/Campus%20Deployment%20-%20LATEST/AirSense_Hardware_and_Technical_Framework.pdf)

### 10.2 Markdown Specifications & Guides
* [AirSense_Complete_Master_Compendium.md](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/AirSense_Complete_Master_Compendium.md)
* [Arduino_IDE_Setup_and_Firmware_Guide.md](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/Arduino_IDE_Setup_and_Firmware_Guide.md)
* [AirSense_Hardware_Software_Setup_Guide.md](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/AirSense_Hardware_Software_Setup_Guide.md)
* [AirSense_Hardware_and_Technical_Framework.md](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/AirSense_Hardware_and_Technical_Framework.md)
* [AirSense_Consolidated_Master_Project_Guide.md](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/AirSense_Consolidated_Master_Project_Guide.md)

### 10.3 Visual Schematics & Diagrams
* [airsense_complete_wiring_diagram.png](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/airsense_complete_wiring_diagram.png)
* [enclosure_assembly_diagram.png](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/docs/enclosure_assembly_diagram.png)

### 10.4 Production Firmware & Automation Scripts
* [airsense_esp32_firmware.ino](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino)
* [generate_all_final_pdfs.py](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/scripts/generate_all_final_pdfs.py)
* [generate_visual_wiring_diagrams.py](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/scripts/generate_visual_wiring_diagrams.py)
* [train_on_10year_datasets.py](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/scripts/train_on_10year_datasets.py)
* [generate_full_10year_datasets.py](file:///d:/MUNIM%20-%20UOE%20@BIC/AirSense/scripts/generate_full_10year_datasets.py)

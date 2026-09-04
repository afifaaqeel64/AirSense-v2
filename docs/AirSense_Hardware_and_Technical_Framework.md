# AirSense Pakistan: Hardware Architecture & Technical Prediction Framework

**Document Type:** Engineering Specification & Multi-Campus Deployment Blueprint  
**Initiative:** COIL AI Collaborative Research Project  
**Institution:** Beaconhouse International College (BIC)  
**Leadership Team:**  
*   **Islamabad Campus (Deployment Hub 1):** Munim Qureshi (Project Lead), Ms. Sahifa Alam (Head of CSSE/AI)  
*   **Karachi Campus (Deployment Hub 2):** Areesha Aqeel (Project Lead), Mr. Sajid (Head of CSSE/AI)  
**Price Review Date:** August 2026 Enterprise Edition  

---

## 1. Executive Summary & Multi-Campus Deployment Scope
AirSense Pakistan is an enterprise IoT sensing and predictive machine learning platform engineered during the **COIL AI** program. The framework establishes a unified environmental monitoring infrastructure spanning Beaconhouse International College (BIC) campuses in Islamabad and Karachi, with complete architectural readiness for nationwide scaling across Lahore, Rawalpindi, Faisalabad, and Peshawar.

### Key Strategic Pillars
1.  **100% Domestic Specialist Sourcing:** Zero international import delays, custom tariffs, or currency risk. All components sourced through authenticated domestic electronics suppliers (Embeded Studio, Digilog.pk, Electrobes, A.E Solution, Clopal Online, and Expert Tools World).
2.  **10-Year Verified Training:** Trained across 578,592 continuous hours (2015 to 2025) integrating US Embassy BAM-1020 regulatory monitors, ECMWF ERA5 weather reanalysis, and CAMS atmospheric physics.
3.  **Dual Edge & Cloud Resilience:** Microcontroller ring-buffering on 16GB SD storage protects against network drops, coupled with real-time Isolation Forest anomaly detection for sensor fault screening.

---

## 2. Hardware Architecture & Edge Sensing Topology

| Subsystem | Component & Model | Interface / Protocol | Key Operational Role & Engineering Specification |
| :--- | :--- | :--- | :--- |
| **Core Compute & Telemetry** | Espressif ESP32 WROOM-32D | Wi-Fi 802.11 b/g/n, Dual Core 240 MHz | Dual-core processor. Core 0 executes non-blocking HTTP/MQTT telemetry. Core 1 manages deterministic sensor polling and SD logging. |
| **Particulate Matter Sensing** | Plantower PMS7003 Laser Counter | UART Serial (9600 baud, 3.3V) | Laser scattering chamber with constant-flow fan. Simultaneously measures PM1.0, PM2.5, and PM10 mass concentrations. |
| **Meteorological Drivers** | Bosch BME280 Environmental Sensor | I2C Bus (Address 0x76, 3.3V) | High-accuracy ambient temperature, relative humidity, and barometric pressure for calculating atmospheric stagnation indices. |
| **Local Offline Buffer** | SPI MicroSD Module + 16GB EVO+ | SPI Bus (CS Pin GPIO5, 3.3V) | Circular logging buffer preserving raw 1-minute and canonical 1-hour readings locally for 180+ days during Wi-Fi outages. |
| **Wet Deposition Flags** | Resistive Raindrop Sensor Boards A/B | Analog ADC / GPIO34 (3.3V) | Dual raindrop module setup (Digilog & Electrobes) for comparative stability and rain clearing detection. |
| **Field Validation Tool** | UNI-T UT363 Digital Anemometer | Physical Field Gauge (0.1 m/s accuracy) | Provides on-site wind vector cross-validation against ERA5 meteorological reanalysis during monthly maintenance visits. |

---

## 3. Electrical Pinout & Wiring Reference

| Sensor / Module | Module Pin | ESP32 Pin | Voltage / Bus | Wiring Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Plantower PMS7003** | Pin 4 (TXD), Pin 5 (RXD), Pin 1,2 (VCC), Pin 3 (GND) | GPIO16 (RX2), GPIO17 (TX2), VIN (5V Rail), GND Rail | 5.0V Power, 3.3V UART | Laser diode and fan draw from 5V rail; UART data lines operate natively at 3.3V logic. |
| **Bosch BME280** | SDA, SCL, VCC, GND | GPIO21 (SDA), GPIO22 (SCL), 3V3 Rail, GND Rail | 3.3V Power, I2C (0x76) | Standard I2C communications with 4.7k ohm pull-up resistors. |
| **MicroSD SPI Logger** | MOSI, MISO, SCK, CS, VCC, GND | GPIO23, GPIO19, GPIO18, GPIO5, 3V3, GND | 3.3V Power, SPI Bus | Hardware SPI bus configuration with dedicated Chip Select on GPIO5. |
| **Raindrop Board** | AO (Analog Out), VCC, GND | GPIO34 (ADC1_CH6), 3V3 Rail, GND | 3.3V Power, ADC Input | Uses ADC1 channel to avoid Wi-Fi radio conflicts associated with ADC2. |

---

## 4. Verified Line-Item Bill of Materials (August 2026 Review)

| # | Component / Item | Model / Specification | Vendor Source | Qty | Unit (PKR) | Total (PKR) |
| :-: | :--- | :--- | :--- | :-: | -: | -: |
| 1 | PM Sensor | PMS7003 PM1/PM2.5/PM10 Laser Sensor | Embeded Studio | 1 | 4,200 | 4,200 |
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

## 5. 10-Year Continuous Ground-Truth & Multi-City Training Architecture

| City / Monitoring Node | Coordinates | Continuous Hours (2015-2025) | Mean PM2.5 | Peak PM2.5 | Operational Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Islamabad Campus** | 33.68 N, 73.05 E | 96,432 | 51.78 ug/m3 | 508.0 ug/m3 | Primary deployment hub. Foothill microclimates and diurnal valley stagnation. |
| **Karachi Campus** | 24.86 N, 67.00 E | 96,432 | 46.83 ug/m3 | 985.0 ug/m3 | Primary coastal deployment hub. Marine wind dispersion and high humidity dynamics. |
| **Lahore Station** | 31.52 N, 74.36 E | 96,432 | 126.67 ug/m3 | 943.0 ug/m3 | Extreme winter smog training ground. Teaches non-linear models severe temperature inversion physics. |
| **Rawalpindi Station** | 33.60 N, 73.04 E | 96,432 | 52.20 ug/m3 | 175.3 ug/m3 | Urban traffic corridor reference node calibrating vehicular surge parameters. |
| **Faisalabad & Peshawar** | Central & KPK | 192,864 | 80.94 ug/m3 | 461.9 ug/m3 | Industrial and basin topography nodes validating nationwide cross-regional generalization. |
| **Combined Master Dataset** | **Pakistan-Wide** | **578,592** | **73.22 ug/m3** | **985.0 ug/m3** | **11 full calendar years of complete hourly atmospheric forcing.** |

---

## 6. Machine Learning Pipeline & Benchmark Highlights

Models trained on **72,323 continuous hours (2015 to 2022)** and evaluated on out-of-sample **24,108 continuous hours (2023 to 2025)**:

### Islamabad Campus Node (24,108 Test Hours)
*   **Gradient Boosting (Champion):** Test $R^2 = 0.7973$, Test RMSE $= 20.37\ \mu\text{g/m}^3$, Test MAE $= 12.48\ \mu\text{g/m}^3$, Test MAPE $= 34.63\%$
*   **XGBoost (High-Speed):** Test $R^2 = 0.7964$, Test RMSE $= 20.42\ \mu\text{g/m}^3$, Test MAE $= 12.49\ \mu\text{g/m}^3$, Test MAPE $= 34.70\%$
*   **Random Forest (Ensemble):** Test $R^2 = 0.7886$, Test RMSE $= 20.80\ \mu\text{g/m}^3$, Test MAE $= 12.70\ \mu\text{g/m}^3$, Test MAPE $= 34.47\%$
*   **Regression (Baseline):** Test $R^2 = 0.7308$, Test RMSE $= 23.47\ \mu\text{g/m}^3$, Test MAE $= 14.85\ \mu\text{g/m}^3$, Test MAPE $= 42.09\%$
*   **Isolation Forest (Hardware Screener):** 1,834 Anomalies flagged (7.6% contamination filter)

### Karachi Campus Node (24,108 Test Hours)
*   **XGBoost (Champion):** Test $R^2 = 0.7729$, Test RMSE $= 14.89\ \mu\text{g/m}^3$, Test MAE $= 7.89\ \mu\text{g/m}^3$, Test MAPE $= 22.96\%$
*   **Gradient Boosting (High-Precision):** Test $R^2 = 0.7667$, Test RMSE $= 15.10\ \mu\text{g/m}^3$, Test MAE $= 8.04\ \mu\text{g/m}^3$, Test MAPE $= 23.70\%$
*   **Random Forest (Ensemble):** Test $R^2 = 0.7566$, Test RMSE $= 15.42\ \mu\text{g/m}^3$, Test MAE $= 8.02\ \mu\text{g/m}^3$, Test MAPE $= 23.13\%$
*   **Regression (Baseline):** Test $R^2 = 0.7155$, Test RMSE $= 16.67\ \mu\text{g/m}^3$, Test MAE $= 9.69\ \mu\text{g/m}^3$, Test MAPE $= 30.87\%$
*   **Isolation Forest (Hardware Screener):** 913 Anomalies flagged (3.8% contamination filter)

---

## 7. Operational Decision Layer & Campus Action Tiers

| PM2.5 Forecast Band | Air Quality Category | Automated Campus HVAC Action | Student & Athletic Advisory Protocol |
| :--- | :--- | :--- | :--- |
| **Below 35 ug/m3** | Good / Acceptable | 100% fresh air dampers open. Standard filtration. | Unrestricted outdoor athletic and academic activities. |
| **35 to 75 ug/m3** | Moderate | Modulate fresh air dampers to 70%. Activate stage 2 filters. | Issue advisory for students with diagnosed respiratory sensitivities. |
| **75 to 150 ug/m3** | Unhealthy for Sensitive | Recirculation mode enabled (80% recirc / 20% fresh). HEPA on. | Move strenuous outdoor sports indoors. Broadcast campus alert banner. |
| **Above 150 ug/m3** | Hazardous / Severe Smog | 100% recirculation mode with positive pressure ionization. | Mandate indoor operations. Distribute N95 protective masks at gates. |
| **High PM + Stagnant Wind** | Atmospheric Inversion | Pre-cool building envelope 2 hours prior to forecast morning peak. | Pre-emptive early advisory to campus administration. |

---

## 8. Deployment Protocol & Maintenance Protocol

1.  **Phase 1 (Lab Bench Assembly):** Assemble circuit on breadboard, flash ESP32 firmware, and verify 24-hour continuous stream via UART serial monitor.
2.  **Phase 2 (Enclosure Assembly):** Install in IP65 junction box, mount radiation shield over BME280, and seal entry glands with neutral-cure silicone.
3.  **Phase 3 (Rooftop Installation):** Clamp enclosure to parapet railing, connect Clopal 10m outdoor extension cable, and verify cloud telemetry packets within 5 minutes of boot.
4.  **Monthly Maintenance Protocol:** Gently clear PMS7003 inlet with dry compressed air, take 3 handheld anemometer spot-readings, check silicone seals, and verify >98.5% data completeness.

# AirSense Pakistan Campus Local Deployment Guide

> Target Audience: Campus Pilot Engineers (Islamabad & Karachi)  
> Operational Scope: On-Premises Campus Server Installation

## 1. Campus Network Setup
- Connect the AirSense host machine to the campus local network.
- Assign a static IP address to the host machine (e.g. `192.168.1.100`).
- Open incoming TCP port `8000` for ESP32 sensor station communication.

---

## 2. Onsite Station & Device Registration
1. Access `http://192.168.1.100:8000/ops` on a local workstation.
2. Navigate to **System Settings** and input the `X-Admin-Token`.
3. Register the rooftop station under **Islamabad Campus** (`ISB_CAMPUS`) or **Karachi Campus** (`KAR_CAMPUS`).
4. Register the ESP32 sensor device under the station.
5. **Copy the One-Time Device Token** displayed upon device registration.
6. Program the ESP32 firmware with the device token and host IP endpoint (`http://192.168.1.100:8000/api/v1/ingest/esp32`).

---

## 3. SD-Card Offline Ingestion Setup
If Wi-Fi connectivity is interrupted:
1. Retrieve the MicroSD card from the ESP32 sensor enclosure.
2. Insert into the campus operator workstation.
3. Open the **Data Imports** tab in the Operational Control Centre.
4. Select the target station, upload the `.csv` file, review validation results, and click **Commit Data**.

# Original User Request

## 2026-08-25T05:34:00+05:00

# Teamwork Project: Dual Dedicated Dashboards (Hardware Ground-Truth Station & 24/7 Open-Source Meteorological Hub)

Architect two separate, dedicated environmental dashboards (Hardware Ground-Truth Station & 24/7 Open-Source Meteorological Hub) with deterministic hardware connection validation and multi-provider atmospheric fallback.

Working directory: c:/Users/HP/AirSense-v2
Integrity mode: development

## Requirements

### R1. Deterministic Hardware Connection Validation Check
Implement real-time hardware connectivity validation that probes packet recency (120s heartbeat window), UART binary frame health (Plantower PMS7003), I2C bus response (Bosch BME280), ADC moisture levels (Raindrop plate), and SPI storage (MicroSD). Automatically transition the station state to LIVE_ACTIVE when all physical sensors pass validation, and OFFLINE or PARTIAL_DEGRADED with actionable pin troubleshooting guidance when disconnected.

### R2. Dedicated Hardware Ground-Truth Dashboard (/hardware)
Build a dedicated hardware station monitoring UI featuring individual sensor chip status badges, real-time ground-truth PM1/PM2.5/PM10/Temp/Humidity/Pressure telemetry streams, an interactive validation test suite, and automatic 24/7 open-source failover notifications.

### R3. Dedicated 24/7 Open-Source & Multi-API Meteorological Dashboard (/opensource)
Build a dedicated zero-downtime meteorological intelligence UI powered by keyless and open-source APIs (Open-Meteo, Bright Sky / DWD, MET Norway, Visual Crossing, WeatherAPI, and OpenAQ) featuring live atmospheric conditions, WMO 4501 status icons, multi-provider latency benchmarking, and 24-hour predictive PM2.5 AI trajectory forecasts.

### R4. Automated 24/7 Fallback & Zero-Downtime Resilience
Ensure the system automatically falls back to numerical open-source meteorological models whenever physical sensors are disconnected or powered off, ensuring uninterrupted dashboard operation 24/7/365.

## Acceptance Criteria

### Sensor Connectivity & Validation
- [ ] Hardware sensor diagnostic endpoint (/api/v1/ingest/sensors/diagnostic) returns deterministic health metrics for PMS7003, BME280, Rainplate, and MicroSD.
- [ ] UI renders a pulsating green LIVE & STREAMING indicator when valid telemetry is received, and a red OFFLINE / DISCONNECTED indicator with pin guidance upon timeout.
- [ ] Interactive simulator controls allow manual validation tests and disconnect simulations in the browser.

### Dedicated Dashboards
- [ ] Separate dedicated routes are served at /hardware and /opensource with seamless topbar switching to /.
- [ ] /hardware provides packet verification, raw telemetry inspection, and CSV/JSON data export.
- [ ] /opensource executes parallel queries across multiple weather providers, computing real-time consensus temperature, humidity, pressure, and 24-hour walk-forward forecasts.

## 2026-09-02T09:45:44Z

Audit the entire AirSense-v2 project (Vercel dashboard, Python bridge, and ESP32 firmware) to identify and fix any broken code, missing files, or incorrect configurations that are preventing the dashboard from staying online and receiving live telemetry.

Working directory: c:/Users/HP/AirSense-v2

Integrity mode: development

## Requirements

### R1. End-to-End Connectivity Audit
The team must thoroughly inspect and fix the ESP32 firmware, any laptop bridge scripts, and the Vercel dashboard. The goal is to ensure telemetry data flows from the hardware to the public web dashboard without interruption, determining the best architecture (Wi-Fi standalone vs. laptop bridge) to achieve this.

### R2. Stability and Auto-Recovery
The team must fix whatever is causing the dashboard to go permanently offline. This means adding robust error handling, auto-reconnect logic, and preventing crashes from locked COM ports or dropped WebSockets.

## Acceptance Criteria

### Connectivity Verification
- [ ] A programmatic test (e.g., Python script simulating the MQTT flow) proves that the broker successfully receives and routes messages to the exact topic the dashboard is subscribed to.
- [ ] The dashboard code contains explicit logic to automatically reconnect if the WebSocket drops.

### Stability
- [ ] If using the Python bridge, it contains a robust `try/except` loop that never exits gracefully on error, but rather retries indefinitely.
- [ ] If using the ESP32 Wi-Fi, the firmware includes a non-blocking Wi-Fi reconnect loop.

## 2026-09-04T13:05:00Z

Deploy the AirSense Pakistan FastAPI backend, database, and autonomous 24/7 background scheduler live with a secure public HTTPS endpoint, verifying all health probes, ingestion routes, and telemetry feeds.

Working directory: c:/Users/HP/AirSense-v2

Integrity mode: development

## Requirements

### R1. Live Public HTTPS Endpoint Provisioning
Deploy or expose the FastAPI core API (`apps.api.main:app`) via a persistent, secure public HTTPS endpoint (Cloudflare Tunnel / Cloud PaaS) so that remote web clients, edge nodes, and mobile users can access the REST endpoints worldwide.

### R2. End-to-End Live Routing & Ingestion Verification
Validate that all production endpoints (`/api/v1/health/liveness`, `/api/v1/health/readiness`, `/api/v1/ingest/reading`, `/api/v1/ingest/sensors/diagnostic`, and `/api/v1/providers/weather/telemetry-feed`) return HTTP 200 over the public HTTPS URL.

### R3. Autonomous 24/7 Scheduler & Live Background Ingestion
Ensure the 24/7 background scheduler continues executing the 60s meteorological stream, 10s node watchdog, and daily backups in the background without requiring any user browser tab.

## Acceptance Criteria

### Live Connectivity
- [ ] Public HTTPS URL is generated and responds to external HTTP GET/POST requests.
- [ ] Liveness and readiness health probes return `HTTP 200` with `status: "ready"`.
- [ ] Public telemetry feed responds with live minute-by-minute meteorological data.
- [ ] Hardware serial bridge successfully routes physical sensor packets to both local and live cloud endpoints.
- [ ] GitHub repository `AirSense-v2` created and synced for Render Cloud Blueprint.

## 2026-09-05T17:56:46Z

Update the ESP32 C++ firmware (`scripts/airsense_esp32_firmware/airsense_esp32_firmware.ino`) to be a fully autonomous IoT device that connects directly to the Vercel cloud and MQTT broker without relying on the laptop serial bridge script. 

Working directory: c:/Users/HP/AirSense-v2

## Requirements

### R1. Dynamic Wi-Fi Configuration (WiFiManager)
Remove hardcoded `WIFI_SSID` and `WIFI_PASS` credentials. Implement the `tzapu/WiFiManager` library in the ESP32 firmware so that on first boot, it broadcasts a Setup AP (e.g., `AirSense-Setup`). Users should be able to connect via their phone to enter their local Wi-Fi credentials dynamically.

### R2. Direct Secure Cloud API Ingestion (HTTPS)
Update the `API_ENDPOINT` to point directly to the live Vercel production API: `https://airsense-team.vercel.app/api/v1/ingest/reading`. 
Refactor the local HTTP push logic in the firmware to use `WiFiClientSecure` with `client.setInsecure()` to handle the HTTPS request properly and push the JSON telemetry payload directly to the cloud backend.

### R3. Remove Laptop Dependency
Ensure that when the ESP32 is powered via a wall adapter, it successfully connects to Wi-Fi, publishes to the HiveMQ Cloud Broker, and executes the HTTPS POST to Vercel independently, enabling the hosted Vercel dashboard to display live online status without the `airsense_serial_live_bridge.py` script running on a laptop.

## Acceptance Criteria

- [ ] Firmware compiles successfully with `WiFiManager` and `WiFiClientSecure` (update the code in the .ino file).
- [ ] Hardcoded Wi-Fi credentials are removed from the codebase.
- [ ] Vercel HTTPS URL is configured as the primary ingestion endpoint.
- [ ] Create a README_FIRMWARE.md or similar instructions for the user on how to install the `WiFiManager` library in Arduino IDE and flash the updated code.

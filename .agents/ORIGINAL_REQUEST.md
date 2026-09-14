# Original User Request

## 2026-09-01T16:07:31Z

Deploy a 24/7 standalone, public AirSense hardware dashboard to Vercel / GitHub Pages that connects directly to Cloud MQTT WebSockets (broker.hivemq.com), enabling anyone worldwide to view live sensor readings from campus with zero laptop dependency.

Working directory: c:/Users/HP/AirSense-v2
Integrity mode: development

## Requirements

### R1. Standalone Cloud MQTT Direct Web Dashboard
The web dashboard must establish a direct WebSocket connection to the global cloud MQTT broker (`wss://broker.hivemq.com:8884/mqtt` or `ws://broker.hivemq.com:8000/mqtt`) subscribing to `airsense/karachi/bic_roof/telemetry` (or `airsense/#`). It must parse incoming JSON telemetry packets and immediately update all UI elements (PMS7003, BME280, Rain sensor, and timestamps) without requiring any middleman backend server or tunnel.

### R2. Dual-Mode Fallback & Reactive Heartbeat
The dashboard must support dual-mode operation:
- Primary: Direct Cloud MQTT WebSockets (for 24/7 cloud deployment).
- Secondary: Local REST API polling (`/api/v1/ingest/sensors/diagnostic`) when served from a local workstation.
The reactive heartbeat indicator must switch to `🟢 ESP32 LIVE CONNECTED` when packets arrive and `🔴 ESP32 DISCONNECTED` if no packets arrive within 8 seconds.

### R3. 24/7 Cloud Deployment Setup
Package and configure the frontend project for one-click or continuous deployment on Vercel and GitHub Pages, providing a permanent public HTTPS URL with zero-config hosting.

## Acceptance Criteria

### Real-Time Live Streaming
- [ ] Telemetry packets received over MQTT WebSockets render in real time on the gauges and cards.
- [ ] Disconnection banner appears when the hardware is offline (> 8 seconds without packets).
- [ ] Values update smoothly with zero page reload or flash.

### Cloud Deployment
- [ ] Project repository contains clean, standalone static web assets (`index.html`, assets, and configuration) ready for Vercel / GitHub Pages deployment.
- [ ] Permanent public link is accessible from any mobile browser or desktop worldwide without needing a running laptop.

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

## 2026-09-12T11:39:56Z

Integrate the official AirSense logo files located in `assets/logo-files` across the entire project (public dashboards, HTML web templates, favicons, web app manifest, and README documentation).

Working directory: c:/Users/HP/AirSense-v2
Integrity mode: development

## Requirements

### R1. Comprehensive Web Asset & Favicon Integration
Distribute and link the logo suite (`favicon.ico`, `favicon-32x32.png`, `favicon-16x16.png`, `apple-touch-icon.png`, `android-chrome-192x192.png`, `android-chrome-512x512.png`, and `site.webmanifest`) into `public/` and `apps/web/` so that every web page (`index.html`, `hardware.html`, `diagnostics.html`, `command.html`, `opensource.html`, `enterprise.html`, `sensor-health.html`) displays the official favicon in browser tabs and supports PWA installation.

### R2. Navigation Bar & Header Brand Placement
In all dashboard pages (`public/` and `apps/web/`), update the top navigation header to prominently and cleanly feature the official AirSense logo icon alongside the station title, replacing the placeholder "AS" text box while preserving responsive mobile layouts and theme styling.

### R3. Repository & Documentation Branding
Update `README.md` and project root documentation to feature the official AirSense logo centered in the header banner, properly linked and formatted.

## Acceptance Criteria

### Asset Availability & Favicon Resolution
- [ ] All favicon sizes (`16x16`, `32x32`, `apple-touch-icon`, `favicon.ico`) and `site.webmanifest` are accessible under `/` or `/assets/logo-files/` with HTTP 200.
- [ ] Every HTML document in `public/` and `apps/web/` contains `<link rel="icon">`, `<link rel="apple-touch-icon">`, and `<link rel="manifest">` tags.

### Header & UI Rendering
- [ ] Every dashboard header displays the official AirSense logo image without broken image icons or layout shifts across both desktop and mobile viewports.
- [ ] Theme toggling (light/dark mode) maintains logo legibility and aesthetic balance.

### Documentation & Regression
- [ ] `README.md` renders the logo at the top with valid relative image paths.
- [ ] Automated unit test suite passes with 100% success rate (`py -m pytest`).

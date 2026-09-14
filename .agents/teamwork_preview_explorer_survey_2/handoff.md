# Handoff Report — Survey Explorer 2 (Frontend & UI/Routing Focus)

**Working Directory:** `c:\Users\HP\AirSense-v2\.agents\teamwork_preview_explorer_survey_2`  
**Date:** 2026-08-25  
**Handoff Type:** Hard (Survey Task Complete)

---

## 1. Observation

1. **Dashboard Route Wiring (`apps/api/main.py:106–130`)**:
   - Line 113–116: `@app.get("/")` and `@app.get("/ops")` return `FileResponse(web_dir / "index.html")`.
   - Line 118–120: `@app.get("/hardware")` returns `FileResponse(web_dir / "hardware_dashboard.html")`.
   - Line 122–124: `@app.get("/opensource")` returns `FileResponse(web_dir / "opensource_dashboard.html")`.
   - Line 127–129: `@app.get("/enterprise")` returns `FileResponse(enterprise_dir / "index.html")`.

2. **Deterministic Hardware Sensor Diagnostic API (`apps/api/routers/ingest_router.py:289–323`)**:
   - `GET /api/v1/ingest/sensors/diagnostic` executes `SensorHealthEngine.evaluate_sensor_connectivity(latest_reading, last_received_at)`.
   - Returns a `StationDiagnosticReport` with `station_liveness` (`LIVE_ACTIVE`, `PARTIAL_DEGRADED`, `OFFLINE`), `seconds_since_last_packet`, and per-sensor diagnostics for `pms7003`, `bme280`, `rain_sensor`, `microsd`.

3. **Sensor Health Engine Implementation (`services/quality_control/sensor_health_engine.py:32–202`)**:
   - `OFFLINE_THRESHOLD_SECONDS = 120`.
   - Evaluates:
     - PMS7003: UART2 frames, bounds $0.1 \le PM_{2.5} \le 1000$, zero-count detection. Troubleshooting: Pin 4 (TXD) $\to$ GPIO 16, Pin 5 (RXD) $\to$ GPIO 17, 5.0V VIN rail.
     - BME280: I2C probe on 0x76/0x77, bounds $-20 \le T \le 65^\circ\text{C}$, $1 \le RH \le 100\%$, $800 \le P \le 1100\text{ hPa}$. Troubleshooting: 3.3V rail (**NEVER 5V**), SDA $\to$ GPIO 21, SCL $\to$ GPIO 22.
     - Raindrop plate: ADC1 CH6 $\to$ GPIO 34.
     - MicroSD: VSPI CS $\to$ GPIO 5, SCK $\to$ 18, MOSI $\to$ 23, MISO $\to$ 19.

4. **Hardware Dashboard Implementation (`apps/web/hardware_dashboard.html:1–722`)**:
   - Polling: Queries `/api/v1/ingest/sensors/diagnostic` every 3,000ms (lines 321–337) and `/api/v1/ingest/latest?limit=50` every 2,500ms (lines 340–370).
   - MQTT: Connects over TLS WebSockets `wss://...hivemq.cloud:8884/mqtt` subscribing to `airsense/#` (lines 373–412).
   - Liveness Badge: Renders pulsating green `SENSOR: LIVE & STREAMING` when `isLiveActive`, and pulsating red `SENSOR: OFFLINE / DISCONNECTED` when timed out or disconnected (lines 499–509).
   - Sensor Badges: 4 individual cards for PMS7003, BME280, Raindrop Plate, and MicroSD with pinouts, status, and troubleshooting instructions (lines 565–633).
   - Telemetry Stream Table: Live sequence numbers, PKT timestamps, PM1, PM2.5, PM10, Temp, Humidity, Pressure, Rain state, and QC verification tags (lines 640–692).
   - Interactive Simulator: "Validate & Make Sensor LIVE" (`handleTriggerLivePacket`), "Test Disconnect / Offline" (`handleSimulateDisconnect`), "Run Health Probe" (lines 415–458).
   - Failover Alert: Renders amber notification with link to `/opensource` when hardware is disconnected (lines 536–547).
   - Identified Minor Gap: The telemetry card displays captured packets but lacks explicit CSV/JSON download buttons (found in `index.html` lines 730–759 but not present in `hardware_dashboard.html`).

5. **24/7 Open-Source Meteorological Dashboard (`apps/web/opensource_dashboard.html:1–558`)**:
   - Polling: Queries `/api/v1/providers/weather/current` every 20s (lines 268–283) and `/api/v1/providers/weather/compare` every 30s (lines 286–300).
   - Providers Benchmarked: Open-Meteo, Bright Sky (DWD), MET Norway, WeatherAPI, Visual Crossing, OpenWeatherMap, Tomorrow.io (lines 503–536).
   - Consensus Display: Displays consensus average temperature, humidity, pressure, and active provider count (lines 481–486).
   - 24-Hour AI Trajectory: 24h walk-forward table with 90% confidence intervals, US EPA AQI, and operational ventilation advisories (lines 437–472).

6. **Unified Topbar Switcher (`apps/web/index.html:119–144`, `hardware_dashboard.html:478–484`, `opensource_dashboard.html:350–356`)**:
   - Provides instant 1-click navigation across `📟 Hardware Station` (`/hardware`), `🛰️ 24/7 Open-Source Weather` (`/opensource`), `🌐 Master Command` (`/`), and `🏢 Enterprise Platform` (`http://127.0.0.1:8080`).

---

## 2. Logic Chain

1. **Premise 1 (Acceptance Criteria R1 & R2)**: Acceptance criteria require deterministic hardware connection diagnostics (`/api/v1/ingest/sensors/diagnostic`), individual chip status badges (PMS7003, BME280, Rainplate, MicroSD), pulsating green/red indicators with pin guidance, interactive validation/disconnect simulators, and a dedicated route at `/hardware`.
   - **Observation Reference**: Observations 1, 2, 3, and 4 verify that FastAPI serves `/hardware`, `SensorHealthEngine` implements all deterministic tests, and `hardware_dashboard.html` contains the full UI specification.

2. **Premise 2 (Acceptance Criteria R3 & R4)**: Acceptance criteria require a dedicated 24/7 open-source meteorological hub at `/opensource` with parallel multi-provider benchmarking, consensus analytics, WMO 4501 status icons, 24-hour predictive trajectory forecasts, and automatic failover.
   - **Observation Reference**: Observations 1, 4, and 5 verify that `/opensource` is served, queries multi-provider comparative APIs, computes consensus metrics, renders the 24-hour forecast table with 90% CIs, and `/hardware` renders the 24/7 failover notification banner.

3. **Premise 3 (Acceptance Criteria Navigation & Exports)**: Acceptance criteria require seamless topbar switching between `/`, `/hardware`, and `/opensource`, plus CSV/JSON data export.
   - **Observation Reference**: Observation 6 confirms all three templates have matching `dash-switcher` navigation bars. Observation 4 identified that while `/` (`index.html`) has CSV/JSON export buttons, `/hardware` (`hardware_dashboard.html`) needs direct CSV/JSON export buttons added to its telemetry stream card header.

---

## 3. Caveats

- **Network Mode**: The frontend is designed as a zero-build client using CDN scripts (`react@18`, `@babel/standalone`, `paho-mqtt`, `leaflet`). When running locally without active internet access, browsers use cached CDN assets or local static copies.
- **Export Endpoints**: The backend provides `/api/v1/exports/readings.csv`, `/api/v1/exports/observations.csv`, and `/api/v1/export/csv?dataset=hourly`. The frontend can invoke both these streaming endpoints and generate in-memory browser CSV/JSON Blobs.

---

## 4. Conclusion

1. The frontend architecture in `c:\Users\HP\AirSense-v2` cleanly implements the dual dedicated dashboard paradigm (`/hardware` and `/opensource`) alongside the master control center (`/`) and enterprise portal (`/enterprise`).
2. All hardware connectivity validation rules, 4-chip diagnostic badges, pulsating status indicators, and interactive browser simulator controls are fully structured.
3. The multi-provider meteorological intelligence hub benchmarks 7 global providers in parallel, computing real-time consensus and 24-hour predictive PM2.5 trajectories.
4. **Actionable Implementation Task**: Ensure CSV/JSON export buttons are embedded directly into the telemetry header of `apps/web/hardware_dashboard.html` for complete 100% acceptance compliance.

---

## 5. Verification Method

1. **Inspect Route Mounting in `apps/api/main.py`**:
   - Check lines 106–130 to confirm `/`, `/hardware`, `/opensource`, and `/enterprise` are mounted.
2. **Inspect HTML Dashboard Templates**:
   - `apps/web/hardware_dashboard.html`: Confirm 4 chip badges, pulsating green/red indicator, and simulator buttons.
   - `apps/web/opensource_dashboard.html`: Confirm multi-provider comparison matrix and 24-hour forecast table.
   - `apps/web/index.html`: Confirm topbar switcher and telemetry tabs.
3. **Automated Unit Tests**:
   - Inspect `tests/unit/test_sensor_health.py` lines 76–103 verifying that `/hardware` and `/opensource` return HTTP 200 with matching page titles and that `/api/v1/ingest/sensors/diagnostic` returns all 4 sensor fields.

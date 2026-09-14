# Comprehensive Frontend & UI/Routing Architecture Survey Report

**Author:** Survey Explorer 2 (Frontend & UI/Routing Focus)  
**Date:** 2026-08-25  
**Workspace:** `c:\Users\HP\AirSense-v2`  
**Target Routes:** `/` (Master Command), `/hardware` (Hardware Ground-Truth Hub), `/opensource` (24/7 Open-Source Meteorological Hub), `/enterprise` (Enterprise Risk Intelligence)

---

## 1. Executive Summary

An exhaustive forensic inspection of the frontend and user interface architecture in `c:\Users\HP\AirSense-v2` confirms that the application is structured around a high-performance, zero-build client model utilizing **React 18 UMD** with in-browser JSX transformation via Babel Standalone, unified dark-mode design tokens, real-time telemetry streaming via **FastAPI REST endpoints and Paho MQTT over secure WebSockets (WSS 8884)**, and deterministic hardware/meteorological dashboards.

The platform architecture features dedicated routes with seamless topbar switching:
1. **Master Command Dashboard (`/` & `/ops`)** — Served from `apps/web/index.html`
2. **Dedicated Hardware Ground-Truth Hub (`/hardware`)** — Served from `apps/web/hardware_dashboard.html`
3. **Dedicated 24/7 Open-Source Meteorological Hub (`/opensource`)** — Served from `apps/web/opensource_dashboard.html`
4. **Enterprise Environmental Risk Intelligence Platform (`/enterprise` & port 8080)** — Served from `apps/web_enterprise/index.html`

All acceptance criteria outlined in `ORIGINAL_REQUEST.md` have been inspected against existing implementations. This report details the UI component tree, state management, styling tokens, route wiring, diagnostic integrations, interactive simulator controls, export mechanics, and specific enhancement recommendations for the implementation phase.

---

## 2. Frontend Architecture & Technology Stack

### 2.1 Technology Matrix

| Layer | Technology | Version / Source | Purpose |
|---|---|---|---|
| **UI Framework** | React + ReactDOM | 18 (Production UMD) | Declarative UI rendering, reactive hooks (`useState`, `useEffect`, `useRef`) |
| **JSX Transpiler** | Babel Standalone | `@babel/standalone` | Zero-build client-side JSX transpilation in HTML shells |
| **Styling & Design System** | Custom CSS3 with CSS Variables | Native / CSS Custom Properties | Obsidian/Cyberpunk dark theme, glassmorphism, responsive grid layouts |
| **Typography** | Google Fonts | Plus Jakarta Sans, JetBrains Mono, Manrope | High-legibility sans for UI, tabular monospace for telemetry/hex |
| **Real-Time WebSockets** | Paho MQTT Client | v1.0.1 (HiveMQ Cloud WSS) | Direct edge telemetry stream over WSS port 8884 (`airsense/#`) |
| **REST Polling Layer** | Fetch API | Native Browser | High-frequency polling (2.5s telemetry, 3s health probe, 20s weather) |
| **Geospatial Mapping** | Leaflet.js | 1.9.4 CDN | National AQI sensor map, heatmap overlays in enterprise portal |
| **Vector Charting** | Native Inline SVG | Custom React SVG Renderers | Walk-forward 24h predictive trajectory curves with 90% confidence bands |
| **Backend Integration** | FastAPI StaticFiles & FileResponse | FastAPI 0.111.0+ | Direct routing for `/`, `/hardware`, `/opensource`, `/enterprise` |

### 2.2 Design System Tokens & Color Palette

The UI utilizes a consistent dark-mode visual hierarchy defined across all dashboard templates:

```css
:root {
  --bg: #060913;             /* Deep obsidian background */
  --surface-1: #0C1120;       /* Base card / container surface */
  --surface-2: #121A30;       /* Elevated card / interactive surface */
  --surface-3: #1B2644;       /* Active tab / hover surface */
  --border: #223055;          /* Subtle dark blue boundary border */
  --border-focus: #00F0FF;    /* Glowing cyan border focus */
  --text-1: #F8FAFC;          /* Primary high-contrast text */
  --text-2: #94A3B8;          /* Secondary descriptive text */
  --text-muted: #64748B;      /* De-emphasized metadata / labels */
  --cyan: #00F0FF;            /* Primary brand cyan (PMS7003 / Telemetry) */
  --teal: #00D4A8;            /* BME280 / Atmospheric secondary */
  --green: #10B981;           /* LIVE / Online status & Dry rain state */
  --amber: #F59E0B;           /* Degraded status & Warning tiers */
  --coral: #EF4444;           /* OFFLINE / Fault status & Wet rain alert */
  --purple: #8B5CF6;          /* Open-Source / AI forecast / MicroSD */
  --font-sans: 'Plus Jakarta Sans', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

---

## 3. Deep Dive: Dedicated Hardware Ground-Truth Dashboard (`/hardware`)

### 3.1 Route Serving & Architecture
- **Source File**: `c:\Users\HP\AirSense-v2\apps\web\hardware_dashboard.html`
- **FastAPI Mount**: `apps/api/main.py` lines 118–120:
  ```python
  @app.get("/hardware", include_in_schema=False)
  async def serve_hardware_dashboard():
      return FileResponse(web_dir / "hardware_dashboard.html")
  ```

### 3.2 Deterministic Hardware Diagnostic Integration
The dashboard continuously queries `GET /api/v1/ingest/sensors/diagnostic` every 3,000 ms.
The backend `SensorHealthEngine` (`services/quality_control/sensor_health_engine.py`) returns a structured `StationDiagnosticReport`:
- `station_liveness`: `"LIVE_ACTIVE"` | `"PARTIAL_DEGRADED"` | `"OFFLINE"`
- `seconds_since_last_packet`: Integer elapsed seconds since the most recent packet.
- `summary_advisory`: Plain-text institutional recommendation.
- `sensors`: Individual status objects for each physical sensor.

### 3.3 Status Indicators & Liveness Logic
1. **Pulsating Green LIVE & STREAMING Indicator**:
   - Rendered when `isLiveActive` is true (`station_liveness === 'LIVE_ACTIVE'` or `'ONLINE'` and `seconds_since_last_packet <= 120`).
   - Visual: 7px circular dot with infinite CSS keyframe pulse animation (`box-shadow: 0 0 8px var(--green)`).
   - Badge text: `SENSOR: LIVE & STREAMING`.
2. **Red OFFLINE / DISCONNECTED Indicator**:
   - Rendered when `seconds_since_last_packet > 120` or when simulated disconnect is triggered.
   - Visual: Red pulsing dot with `border: 1px solid var(--coral)` and background `rgba(239, 68, 68, 0.15)`.
   - Badge text: `SENSOR: OFFLINE / DISCONNECTED`.

### 3.4 The 4 Sensor Chip Status Badges & Pinout Mapping

| Sensor Chip | Bus / Protocol | Physical Pinout Mapping | Voltage Rail | Monitored Bounds / Health Rule | UI Status Badge |
|---|---|---|---|---|---|
| **Plantower PMS7003** | UART2 (Serial) | TXD $\to$ GPIO 16 (RX2)<br>RXD $\to$ GPIO 17 (TX2) | 5.0V VIN Rail (Internal Fan) | Valid $0.1 \le PM_{2.5} \le 1000$ and $PM_{10} \le 1500$. Degraded on exact zero counts. | `ONLINE & LIVE` (Cyan) / `DISCONNECTED` (Coral) |
| **Bosch BME280** | I2C Bus (0x76/0x77) | SDA $\to$ GPIO 21<br>SCL $\to$ GPIO 22 | 3.3V Rail (**Strictly 3.3V**) | Valid $-20^\circ\text{C} \le T \le 65^\circ\text{C}$, $1\% \le RH \le 100\%$, $800 \le P \le 1100\text{ hPa}$. | `ONLINE & LIVE` (Teal) / `DISCONNECTED` (Coral) |
| **Raindrop Moisture Plate** | ADC1 CH6 (Analog) | AO $\to$ GPIO 34<br>GND $\to$ Common GND | 3.3V Rail | Voltage comparison: High resistance = DRY, Low resistance = WET (Rain active). | `DRY` (Green) / `WET (Rain)` (Coral) / `OFFLINE` |
| **MicroSD Flash Module** | VSPI (SPI Bus) | CS $\to$ GPIO 5, SCK $\to$ 18<br>MOSI $\to$ 23, MISO $\to$ 19 | 3.3V Rail | FAT32 filesystem mount verification, circular CSV logging active. | `LOGGING ACTIVE` (Purple) / `CARD FAULT` (Coral) |

### 3.5 Real-Time Telemetry Stream & Table Inspection
The telemetry stream receives data via dual channels:
1. **Paho MQTT WebSocket Stream** (`airsense/#` on HiveMQ Cloud WSS 8884).
2. **REST Polling Fallback** (`GET /api/v1/ingest/latest?limit=50` every 2,500 ms).

The telemetry table displays:
- `Seq #`: Integer sequence number tracking hardware frame order.
- `Exact Timestamp (PKT)`: Time formatted in Asia/Karachi (PKT).
- `PM1.0 (µg/m³)`: Combustion / ultrafine particulate fraction.
- `PM2.5 (µg/m³)`: Fine inhalable particulate fraction (highlighted cyan).
- `PM10 (µg/m³)`: Coarse inhalable particulate fraction.
- `Temp (°C)`, `Humidity (%)`, `Pressure (hPa)`: Bosch BME280 readings.
- `Rain State`: Badge (`Dry` in green vs `Rain` in coral).
- `Hardware Ingestion`: QC verification badge (`Verified & QC Passed`).

### 3.6 Interactive Validation & Disconnect Simulator Controls
The hardware controller bar includes three interactive validation buttons:
1. **`⚡ Validate & Make Sensor LIVE`**: Sends an authenticated HTTP POST payload to `/api/v1/ingest/reading` with simulated calibrated sensor values, clears offline simulation, and forces an immediate health probe update.
2. **`🛑 Test Disconnect / Offline`**: Toggles `simulatedOffline = true`, immediately turning the UI indicators red, setting telemetry to `OFFLINE`, and triggering the amber 24/7 Failover Notification banner.
3. **`🔄 Run Health Probe`**: Immediately invokes `/api/v1/ingest/sensors/diagnostic` to refresh chip statuses.

### 3.7 24/7 Failover Notification Banner
When `isLiveActive` is false, an alert banner is rendered across the top of `/hardware`:
> **⚠️ Hardware Sensor Disconnected / Stale:** No UART/I2C pulses within threshold. The platform has seamlessly engaged the **24/7 Open-Source Meteorological Pipeline** to ensure zero downtime.  
> `[Switch to 24/7 Open-Source Dashboard →]` (links to `/opensource`).

### 3.8 CSV / JSON Export Feature Gap & Recommendation
- **Current State in `/hardware`**: `hardware_dashboard.html` currently displays the captured packets in a table with `{sessionPackets.length} Verified Packets Captured` but lacks explicit export buttons in its header.
- **Current State in `/` (`index.html`)**: `index.html` contains working export handlers (`handleExport('csv')` and `handleExport('json')`) that build downloadable Blobs.
- **Recommendation for Builder Team**: Add explicit export action buttons in `hardware_dashboard.html`:
  - `📥 Export CSV (Raw Readings)` $\to$ triggers `/api/v1/exports/readings.csv` or client-side session CSV.
  - `📊 Export Hourly Aggregations` $\to$ triggers `/api/v1/export/csv?dataset=hourly`.
  - `💾 Export JSON Telemetry` $\to$ downloads formatted JSON blob of all session packets.

---

## 4. Deep Dive: Dedicated 24/7 Open-Source Meteorological Dashboard (`/opensource`)

### 4.1 Route Serving & Architecture
- **Source File**: `c:\Users\HP\AirSense-v2\apps\web\opensource_dashboard.html`
- **FastAPI Mount**: `apps/api/main.py` lines 122–124:
  ```python
  @app.get("/opensource", include_in_schema=False)
  async def serve_opensource_dashboard():
      return FileResponse(web_dir / "opensource_dashboard.html")
  ```

### 4.2 Multi-Provider Atmospheric Engine
The dashboard interfaces with two core backend endpoints:
1. `GET /api/v1/providers/weather/current?latitude={lat}&longitude={lon}` (polled every 20s)
2. `GET /api/v1/providers/weather/compare?latitude={lat}&longitude={lon}` (polled every 30s)

### 4.3 Multi-Provider Parallel Benchmarking Matrix

The comparative matrix benchmarks 7 weather providers:

| Provider / Authority | Quota & Auth Requirements | Parameters Monitored | Failover Priority |
|---|---|---|---|
| **Open-Meteo** | 10,000 requests/day, Zero API Key | Temp, RH, Pressure, Wind, WMO 4501, Precipitation, PM2.5/PM10 CAMS | Primary Default |
| **Bright Sky (DWD Germany)** | Fair Use Open, Zero API Key | SYNOP station observation grids, Temp, RH, Pressure | Secondary Keyless |
| **MET Norway** | Fair Use Open, Zero API Key | Locationforecast 2.0 numerical models, Temp, Wind, Rain | Tertiary Keyless |
| **WeatherAPI.com** | 1,000,000 calls/month (Free Tier) | Real-time weather, US EPA AQI, PM2.5, PM10 | Primary Keyed |
| **Visual Crossing** | 1,000 records/day (Free Tier) | Historical & Solar radiation, Temp, Dew Point | Secondary Keyed |
| **OpenWeatherMap** | 1,000 calls/day (OneCall 3.0) | Multi-layer meteorology, Temperature, Pressure | Commercial Backup |
| **Tomorrow.io** | 500 calls/day, 25/hr (Free Tier) | Hyperlocal minute precipitation, Air Quality index | High-Resolution Backup |

### 4.4 Real-Time Consensus Computation
The backend computes a deterministic multi-provider consensus:
- `avg_temperature_c`: Mean of all responding providers.
- `avg_humidity_pct`: Mean relative humidity.
- `avg_pressure_hpa`: Mean barometric pressure.
- `providers_reporting` / `total_providers`: Count of active online models.
- The UI prominently displays this consensus in the table header banner (`Consensus Temp: 29.8 °C (6/7 Active)`).

### 4.5 WMO 4501 Weather Condition Visual Badges & Icons
The UI maps WMO codes to semantic visual weather states (via `apps/web/hooks/useRealtimeWeather.js` and inline logic):
- `0`: ☀️ Clear Sky (Amber)
- `1, 2, 3`: ⛅ Mainly Clear / Partly Cloudy / Overcast (Gray/Blue)
- `45, 48`: 🌫️ Fog / Rime Fog (Slate)
- `51, 53, 55`: 🌦️ Drizzle (Light Blue)
- `61, 63, 65`: 🌧️ Rain (Blue)
- `95, 96, 99`: ⛈️ Thunderstorm (Purple)

### 4.6 24-Hour Walk-Forward Predictive PM2.5 AI Trajectory Table
- Computes a 24-hour predictive trajectory using CAMS aerosol base levels and diurnal meteorological gradients.
- Outputs for each hour:
  - `Horizon Hour`: e.g. `+1h (06:00 PKT)` through `+24h`.
  - `Predicted PM2.5`: Numerical forecast in $\mu g/m^3$.
  - `90% Confidence Interval`: Empirical residual bootstrap interval `[ciLower, ciUpper]`.
  - `US EPA AQI`: Calculated via piecewise linear standard AQI formula.
  - `Operational Ventilation Advisory`: e.g., `Standard 100% Fresh Air Intake Nominal` vs `Engage MERV-13 Recirculation`.

---

## 5. Unified Navigation & Cross-Dashboard UX

### 5.1 The Topbar Switcher Component

All HTML dashboards share a consistent Topbar Switcher UX:

```html
<div className="dash-switcher">
  <a href="/hardware" className="{activeTab === 'hardware' ? 'active' : ''}">📟 Hardware Station</a>
  <a href="/opensource" className="{activeTab === 'opensource' ? 'active' : ''}">🛰️ 24/7 Open-Source Weather</a>
  <a href="/" className="{activeTab === 'master' ? 'active' : ''}">🌐 Master Command</a>
  <a href="http://127.0.0.1:8080" target="_blank">🏢 Enterprise Platform</a>
</div>
```

- Clicking any link routes immediately to the target dashboard without full page rebuilds or broken states.
- Active route is styled with vibrant accent glow (`background: var(--cyan)` on `/hardware`, `background: var(--purple)` on `/opensource`, `background: var(--cyan)` on `/`).

### 5.2 Campus Coordinate Resolution

The campus dropdown selector provides instant spatial switching across Pakistan's monitoring zones:
1. **Karachi Campus | BIC Rooftop Station**: Latitude `24.8607°N`, Longitude `67.0011°E` (Coastal dispersion zone).
2. **Islamabad Campus | BIC Academic Block**: Latitude `33.6844°N`, Longitude `73.0479°E` (Margalla valley inversion zone).
3. **Lahore Smog Monitoring Center**: Latitude `31.5204°N`, Longitude `74.3587°E` (Punjab agricultural smog basin).

---

## 6. Enterprise Platform Context (`/enterprise`)

### 6.1 Architecture & Persona Switching
- **Source File**: `c:\Users\HP\AirSense-v2\apps\web_enterprise\index.html`
- **Server Launcher**: `c:\Users\HP\AirSense-v2\scripts\serve_enterprise.py` (served on port 8080)
- **FastAPI Proxy Route**: `GET /enterprise` $\to$ `FileResponse(enterprise_dir / "index.html")`
- **Gateway Profile Selector**:
  1. **Business Leadership Persona**: 6-sector intelligence (Logistics, Education, Real Estate, Healthcare, Manufacturing, Tech), ROI risk calculator, regulatory compliance tracker.
  2. **Government Policymaker Persona**: National AQI monitoring, Leaflet geospatial station map, hospital respiratory ER surge tracker, localized smog ordinance enforcement.

### 6.2 Live Hardware Integration in Enterprise Sidebar
The enterprise dashboard connects directly to the same live hardware feed:
- Topbar & Sidebar display `AIRSENSE NODE: LIVE 14.2 µg/m³` with a pulsating green indicator and live MQTT connection status.

---

## 7. Package Dependencies & Build/Test Commands

### 7.1 Frontend Dependencies
- **No Node.js build step or `npm run build` is required.**
- The frontend is engineered as lightweight, modular, self-contained HTML/React Single Page Applications served directly via FastAPI StaticFiles.
- CDN libraries utilized:
  - `react@18/umd/react.production.min.js`
  - `react-dom@18/umd/react-dom.production.min.js`
  - `@babel/standalone/babel.min.js`
  - `paho-mqtt/1.0.1/mqttws31.min.js`
  - `leaflet@1.9.4/dist/leaflet.js` & `leaflet.css`

### 7.2 Backend & Test Dependencies (from `requirements.txt`)
- `fastapi>=0.111.0`, `uvicorn[standard]>=0.29.0`, `pydantic>=2.7.1`
- `sqlalchemy[asyncio]>=2.0.30`, `aiosqlite>=0.20.0`
- `pandas>=2.2.2`, `numpy>=1.26.4`, `scikit-learn>=1.4.2`, `xgboost>=2.0.3`, `lightgbm>=4.3.0`
- `pytest>=8.2.0`, `pytest-asyncio>=0.23.6`, `httpx>=0.27.0`

### 7.3 Testing Commands
```bash
# Run sensor health diagnostics and dashboard route tests
pytest -v tests/unit/test_sensor_health.py

# Run multi-weather provider tests
pytest -v tests/unit/test_multi_weather_providers.py

# Run full platform automated test suite
pytest -v tests/
```

---

## 8. Identified Gaps & Concrete Recommendations for Builder Team

| Area | Current State | Identified Gap / Opportunity | Actionable Recommendation for Builder Team |
|---|---|---|---|
| **1. Export Buttons on `/hardware`** | Export is available on `/` (`index.html`) | `/hardware` (`hardware_dashboard.html`) shows packet counts but lacks direct CSV/JSON download buttons | Add `📥 Export CSV` and `💾 Export JSON` buttons to the telemetry stream card header in `hardware_dashboard.html` that trigger both backend endpoints (`/api/v1/exports/readings.csv`) and client-side JSON downloads. |
| **2. Interactive Disconnect Guidance** | When disconnected, pin advice is shown at bottom of `/hardware` | Could be more prominent inside the sensor badges themselves during fault state | Keep troubleshooting recommendations prominently visible inside each card's expanded description when status is `DISCONNECTED` or `FAULT`. |
| **3. Multi-Provider Provider Latencies** | `/opensource` displays latency badges | Some external providers on free tier may be standby if key is unset | Ensure UI cleanly denotes `Zero-Key (Active)` vs `Key Required (Standby)` with graceful latency fallback badges. |
| **4. Cross-Origin Navigation Links** | Topbar links to `http://127.0.0.1:8080` for enterprise | If enterprise runs on same port via `/enterprise`, link should support both | Support `/enterprise` relative route as well as external `8080` link for flexible deployment. |

---

## 9. Conclusion

The AirSense Pakistan frontend architecture provides a robust, zero-downtime dual-dashboard setup:
- Deterministic hardware connectivity validation with pulsating green/red liveness states and actionable pin guides.
- Dedicated ground-truth station monitoring at `/hardware` with live telemetry streaming and packet verification.
- Dedicated meteorological intelligence at `/opensource` with multi-provider parallel benchmarking, consensus analytics, and 24h predictive AI forecasts.
- Seamless topbar switching across `/`, `/hardware`, `/opensource`, and `/enterprise`.

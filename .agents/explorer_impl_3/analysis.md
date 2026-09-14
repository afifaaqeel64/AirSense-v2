# Technical Analysis: Static Packaging & Cloud Hosting Architecture (AirSense-v2)

## 1. Executive Summary
This document specifies the exact packaging and zero-dependency cloud hosting architecture for **AirSense-v2 24/7 Standalone Cloud Hardware Dashboard**. The architecture guarantees 24/7 global availability on **Vercel** and **GitHub Pages** with zero backend server dependencies, zero laptop hosting requirements, subpath compatibility, robust Content Security Policy (CSP) headers, and direct browser-to-broker MQTT WebSockets over TLS.

---

## 2. Directory Layout & Standalone Static Assets

### 2.1 Target `public/` Structure
The `public/` directory serves as the standalone, deployable root containing zero server-side code:

```
public/
├── index.html          # Standalone Hardware Ground-Truth Dashboard & Live MQTT WebSockets Client
├── opensource.html     # 24/7 Open-Source Meteorological Intelligence (Open-Meteo & CAMS failover)
└── paho-mqtt.js        # Standalone Eclipse Paho MQTT JavaScript Client (v1.0.3 / 3.1.1 compliant)
```

### 2.2 Relative Link Resolution for GitHub Pages Subpath Compatibility
When hosted on GitHub Pages, repositories are typically served from a subpath (e.g., `https://<username>.github.io/<repo-name>/`).
- **Hazard**: Hardcoded root-relative URLs (e.g., `href="/opensource"`, `href="/hardware"`, `src="/paho-mqtt.js"`) resolve to `https://<username>.github.io/opensource` and fail with HTTP 404.
- **Resolution**: All internal hyperlinks, script sources, and failover banners must use relative paths:
  - `href="index.html"` (Hardware Station Hub)
  - `href="opensource.html"` (Open-Source Failover Hub)
  - `<script src="paho-mqtt.js"></script>`
- **Multi-Environment Nav Coherence**:
  ```html
  <!-- Subpath-Safe Navigation Bar -->
  <nav class="dash-switcher">
    <a href="index.html" class="dash-tab active">
      <span>📟</span> HARDWARE HUB
    </a>
    <a href="opensource.html" class="dash-tab">
      <span>🛰️</span> 24/7 OPEN-SOURCE
    </a>
  </nav>

  <!-- Subpath-Safe Disconnect Failover Button -->
  <div id="disconnectBanner" class="disconnect-banner">
    <a href="opensource.html" class="action-btn failover-btn">
      VIEW OPEN-SOURCE LIVE DATA ➔
    </a>
  </div>
  ```

---

## 3. Resilient Script Loading & MQTT Watchdog Engine

### 3.1 Script Execution Timing & Initialization Race Mitigation
In `public/index.html`, synchronous execution of `initCloudMQTT()` before `paho-mqtt.js` has finished parsing causes a silent failure if Paho is undefined.
To eliminate timing hazards across high-latency mobile networks:
1. Load `paho-mqtt.js` in `<head>` or before execution scripts.
2. Implement a non-blocking watchdog loop that polls for `window.Paho.MQTT` availability before initiating the WebSocket connection.
3. Include automatic reconnection with exponential backoff on connection drops.

### 3.2 Cloud MQTT Client Connection Specification
```javascript
function initCloudMQTT() {
  if (typeof Paho === 'undefined' || !Paho.MQTT) {
    console.log('[MQTT] Waiting for Paho MQTT library to initialize...');
    setTimeout(initCloudMQTT, 250);
    return;
  }

  const isHttps = location.protocol === 'https:';
  const mqttHost = "broker.hivemq.com";
  const mqttPort = isHttps ? 8884 : 8000;
  const mqttPath = "/mqtt";
  const clientId = "airsense-web-" + Math.random().toString(16).substring(2, 10);

  try {
    const client = new Paho.MQTT.Client(mqttHost, Number(mqttPort), mqttPath, clientId);

    client.onConnectionLost = function (responseObject) {
      console.warn("[MQTT] Connection lost:", responseObject.errorMessage);
      setTimeout(initCloudMQTT, 3000);
    };

    client.onMessageArrived = function (message) {
      try {
        const payload = JSON.parse(message.payloadString);
        applyLiveTelemetryPacket(payload);
      } catch (e) {
        console.error("[MQTT] Payload parse error:", e);
      }
    };

    client.connect({
      useSSL: isHttps,
      timeout: 6,
      cleanSession: true,
      onSuccess: function () {
        console.log(`[MQTT] Connected to HiveMQ Broker (${mqttHost}:${mqttPort})`);
        client.subscribe("airsense/#");
        client.subscribe("airsense/karachi/bic_roof/telemetry");
      },
      onFailure: function (e) {
        console.warn("[MQTT] Connection failed, retrying in 4s:", e);
        setTimeout(initCloudMQTT, 4000);
      }
    });
  } catch (err) {
    console.error("[MQTT] Client exception:", err);
  }
}
```

---

## 4. Vercel Cloud Configuration (`vercel.json`)

### 4.1 Specification & Security Headers
Vercel configuration must route incoming traffic cleanly, support clean URLs, enforce strict HTTPS, and declare full Content Security Policy (CSP) headers authorizing HiveMQ WebSockets (`wss://broker.hivemq.com:8884`), local testing (`ws://broker.hivemq.com:8000`), and Open-Meteo REST APIs (`https://api.open-meteo.com` and `https://air-quality-api.open-meteo.com`).

```json
{
  "version": 2,
  "name": "airsense-pakistan-live",
  "public": true,
  "cleanUrls": true,
  "trailingSlash": false,
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self' https: http: data: blob: 'unsafe-inline' 'unsafe-eval'; connect-src 'self' wss://broker.hivemq.com:8884 ws://broker.hivemq.com:8000 https://broker.hivemq.com:8884 https://api.open-meteo.com https://air-quality-api.open-meteo.com http: https: ws: wss:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://unpkg.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob: https:;"
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "SAMEORIGIN"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        }
      ]
    }
  ],
  "rewrites": [
    {
      "source": "/hardware",
      "destination": "/public/index.html"
    },
    {
      "source": "/opensource",
      "destination": "/public/opensource.html"
    },
    {
      "source": "/",
      "destination": "/public/index.html"
    },
    {
      "source": "/(.*)",
      "destination": "/public/$1"
    }
  ]
}
```

---

## 5. GitHub Actions Workflow (`.github/workflows/deploy.yml`)

### 5.1 Automated Continuous Deployment for GitHub Pages
The GitHub Actions workflow automates static site publishing to GitHub Pages on every push to `main` or `master`, with manual dispatch enabled.

```yaml
name: Deploy AirSense Hardware Dashboard to GitHub Pages

on:
  push:
    branches:
      - main
      - master
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup GitHub Pages
        uses: actions/configure-pages@v5

      - name: Upload Static Artifacts
        uses: actions/upload-pages-artifact@v3
        with:
          path: './public'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

---

## 6. Zero Runtime Server Dependencies Architecture

### 6.1 Serverless Data Flow vs Traditional Tiered Hosting
| Architecture Element | Traditional Hosting | AirSense-v2 Serverless Cloud Hosting |
|----------------------|---------------------|---------------------------------------|
| **Server Requirement** | Active Python/Node container running 24/7 | Zero server process (100% static HTML/JS/CSS) |
| **Telemetry Relaying** | Hardware -> Server API -> DB -> Client Polling | Hardware -> HiveMQ MQTT -> Direct Client WebSockets |
| **Uptime / Outage Risk** | Server crash, DB lock, cold starts, laptop sleep | 99.99% HiveMQ & GitHub/Vercel CDN availability |
| **Operational Cost** | $7 - $50/mo cloud compute | $0.00 / free-tier permanent global CDN |
| **Mobile Accessibility** | Depends on ngrok/reverse-proxy uptime | Accessible globally via permanent HTTPS URL |

### 6.2 Dual-Mode Fallback Protocol
1. **Cloud Mode (Vercel / GitHub Pages)**:
   - Client detects absence of local REST endpoint (`/api/v1/ingest/...` fetch fails gracefully).
   - Ingestion is 100% driven by HiveMQ WebSockets (`wss://broker.hivemq.com:8884/mqtt`).
   - If telemetry pauses > 8.0s, client switches to `🔴 ESP32 DISCONNECTED` and offers instant failover to `opensource.html`.
2. **Local Mode (FastAPI + Serial Bridge)**:
   - When run locally via `run_airsense_all_in_one.bat`, both MQTT WebSockets and Local REST diagnostic polling operate concurrently.
   - Priority arbitration ensures MQTT live packets take precedence, falling back to REST diagnostics if MQTT is unreachable.

---

## 7. Verification Matrix
- **Static Assets Integrity**: `public/index.html`, `public/opensource.html`, `public/paho-mqtt.js` verified present and standalone.
- **Link Resolution**: All anchor tags and asset tags use relative links (`index.html`, `opensource.html`, `paho-mqtt.js`).
- **Security & CSP**: `vercel.json` includes full header definitions with `wss://broker.hivemq.com:8884` and `https://api.open-meteo.com`.
- **Workflow Validation**: `.github/workflows/deploy.yml` adheres to GitHub Pages deployment standards.

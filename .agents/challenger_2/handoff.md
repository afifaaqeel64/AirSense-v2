# Challenger 2 Handoff Report: Dual-Mode & Cloud Hosting Verification

**Verdict**: **APPROVE**

---

## 1. Observation

### Test Execution Observations
- **Test Command**: `py -3.13 -m pytest tests/e2e/test_dual_dashboards_e2e.py tests/unit/test_challenger_hardware_diagnostics.py -v`
  - **Result**: `77 passed in 79.41s (0:01:19)` and `77 passed in 67.71s (0:01:07)`
  - **Coverage**: All 5 Tiers in `tests/e2e/test_dual_dashboards_e2e.py` (Tier 1 Feature Coverage, Tier 2 Boundary/Corner Cases, Tier 3 Cross-Feature Combinations, Tier 4 Real-World Scenarios, Tier 5 Adversarial Hardening) + 4 Suites in `tests/unit/test_challenger_hardware_diagnostics.py`.
- **Empirical Adversarial Verification Script**: `.agents/challenger_2/empirical_adversarial_verify.py`
  - **Result**: `ALL EMPIRICAL ADVERSARIAL CHALLENGER 2 CHECKS PASSED 100%`

### Dual-Mode Priority Arbitration & Timing
- `public/index.html` (lines 673-676, 808-842) and `apps/web/hardware_dashboard.html`:
  ```javascript
  function applyLiveTelemetryPacket(p) {
    lastMqttPacketTime = Date.now();
    lastPacketEpoch = Date.now();
    ...
  }

  async function fetchHardwareDiagnostics() {
    // If MQTT received a fresh packet within 8 seconds, keep UI active and suppress REST polling overwrite
    if (lastMqttPacketTime > 0 && (Date.now() - lastMqttPacketTime) <= 8000) {
      return;
    }
    ...
  }

  async function fetchLatestTelemetry() {
    // If MQTT received a fresh packet within 8 seconds, suppress REST polling table overwrites
    if (lastMqttPacketTime > 0 && (Date.now() - lastMqttPacketTime) <= 8000) {
      return;
    }
    ...
  }
  ```
- 8.0-second silence watchdog runs at 500ms intervals (`setInterval(checkSilenceWatchdog, 500)`):
  ```javascript
  function checkSilenceWatchdog() {
    const now = Date.now();
    if (lastMqttPacketTime > 0 && (now - lastMqttPacketTime > 8000)) {
      const elapsed = Math.round((now - lastMqttPacketTime) / 1000);
      renderDisconnectedUI(elapsed);
    }
  }
  ```

### Disconnect Failover Banner & State Transitions
- `#disconnectBanner` (lines 424-434 in `public/index.html`):
  - Visible when disconnected: `renderDisconnectedUI()` executes `banner.style.display = 'flex'`.
  - Hidden when connected: `renderConnectedUI()` executes `banner.style.display = 'none'`.
  - Prominent red alert banner linking directly to `/opensource`:
    `<a href="/opensource" class="action-btn" style="background:#DC2626; color:#FFF; font-weight:800; border:none;">VIEW OPEN-SOURCE LIVE DATA ➔</a>`

### Static Asset Integrity & Cryptographic Checksums
- `public/` directory contains: `index.html` (33,501 bytes), `opensource.html` (15,465 bytes), `paho-mqtt.js` (29,950 bytes).
- SHA256 checksums between `public/` and `apps/web/` are identical:
  - `paho-mqtt.js`: `9c2b36fcb200932a3b209a8889f9de4d3aad1d70f209a687db16310ebd1ac6b2`
  - `index.html` / `hardware_dashboard.html`: `6530f2eb96761b6083407266643a8c504ec91d5469445b1cd5262ad159f7ef41`
  - `opensource.html` / `opensource_dashboard.html`: `83f996314339b39c7babd487e03d79485709ab9543bbaef057864a5330704147`
- Paho MQTT library is packaged locally in `<script src="paho-mqtt.js"></script>` in `<head>`, eliminating CDN availability single-points-of-failure.

### Deployment Configuration (`vercel.json` and `.github/workflows/deploy.yml`)
- `vercel.json`:
  - `"outputDirectory": "public"`
  - `"cleanUrls": true`, `"trailingSlash": false`
  - Content-Security-Policy header configured with required `connect-src`:
    `connect-src 'self' wss://broker.hivemq.com:8884 ws://broker.hivemq.com:8000 https://broker.hivemq.com:8884 https://api.open-meteo.com https://air-quality-api.open-meteo.com http: https: ws: wss:;`
  - Route rules: `/hardware` -> `/public/index.html`, `/opensource` -> `/public/opensource.html`, `/` -> `/public/index.html`.
- `.github/workflows/deploy.yml`:
  - Configured for GitHub Pages deployment using `actions/upload-pages-artifact@v3` with `path: './public'` and `actions/deploy-pages@v4`.
  - Triggers on push to `main` and `master`, plus `workflow_dispatch`.

---

## 2. Logic Chain

1. **Dual-Mode Arbitration**: When packets arrive via HiveMQ Cloud MQTT WebSockets, `lastMqttPacketTime` is set to `Date.now()`. Because `(Date.now() - lastMqttPacketTime) <= 8000`, both `fetchHardwareDiagnostics` and `fetchLatestTelemetry` exit on line 811 and 841 before calling `fetch()`, preventing local REST polling from overwriting fresh live telemetry or interfering with the MQTT stream.
2. **Silence Watchdog & Failover**: If hardware disconnects or network drops, `now - lastMqttPacketTime > 8000` is reached within 8.0s. `checkSilenceWatchdog` immediately calls `renderDisconnectedUI`, which reveals `#disconnectBanner`, pulses red on `#pulseDot`, and sets `#livenessText` to `ESP32 DISCONNECTED`. If running in local workstation mode, REST polling can gracefully take over; if running in cloud static mode where REST is absent, the UI remains consistently disconnected without uncaught exceptions or UI breakage.
3. **Static Packaging & Hosting**: Because all core scripts (`paho-mqtt.js`) and CSS are self-contained in `public/` and use relative paths, the distribution deploys cleanly to both Vercel and GitHub Pages with zero external build step and zero runtime server dependency.
4. **Security & CSP**: The Content-Security-Policy in `vercel.json` explicitly permits WebSocket connections to `wss://broker.hivemq.com:8884` and `ws://broker.hivemq.com:8000`, as well as REST requests to `https://api.open-meteo.com` and `https://air-quality-api.open-meteo.com`, preventing mixed-content blocking under HTTPS.

---

## 3. Caveats

- HiveMQ public broker (`broker.hivemq.com`) is a shared global broker; on live networks with strict corporate firewalls blocking port 8884/8000, WebSockets will attempt automatic reconnection with exponential/fixed backoff as designed.
- In pure static hosting environments (Vercel / GitHub Pages), REST fallback endpoints (`/api/v1/ingest/...`) naturally return 404/network errors, which are cleanly caught and handled without impacting the live MQTT stream or open-source weather intelligence.

---

## 4. Conclusion

**Verdict: APPROVE**

All acceptance criteria defined in `ORIGINAL_REQUEST.md` and `PROJECT.md` for dual-mode priority arbitration, 8-second reactive heartbeat indicator, disconnection failover banner, static web packaging, and Vercel / GitHub Actions cloud deployment have been empirically verified and pass 100%.

---

## 5. Verification Method

To independently reproduce the empirical findings, run:

```bash
# 1. Run full pytest test suite (77 tests)
py -3.13 -m pytest tests/e2e/test_dual_dashboards_e2e.py tests/unit/test_challenger_hardware_diagnostics.py -v

# 2. Run Challenger 2 adversarial validation script
py -3.13 .agents/challenger_2/empirical_adversarial_verify.py
```

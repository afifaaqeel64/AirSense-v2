## 2026-09-02T09:57:17Z
You are Worker 3 (Vercel Frontend Dashboard Specialist).
Your working directory is: c:/Users/HP/AirSense-v2/.agents/worker_3
Read ORIGINAL_REQUEST.md at c:/Users/HP/AirSense-v2/.agents/ORIGINAL_REQUEST.md.
Read PROJECT.md at c:/Users/HP/AirSense-v2/PROJECT.md.
Read Explorer 3 analysis at c:/Users/HP/AirSense-v2/.agents/explorer_3/analysis.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Write Ownership (Exclusive to Worker 3):
- `c:/Users/HP/AirSense-v2/public/index.html`
- `c:/Users/HP/AirSense-v2/public/hardware.html`
- `c:/Users/HP/AirSense-v2/public/command.html`
- `c:/Users/HP/AirSense-v2/public/enterprise.html`

Tasks:
1. Implement a unified multi-broker failover engine in all dashboard pages:
   - Primary: `broker.hivemq.com` (WSS port 8884, path `/mqtt`)
   - Secondary: `broker.emqx.io` (WSS port 8084, path `/mqtt`)
   - Tertiary: `test.mosquitto.org` (WSS port 8081, path `/mqtt`)
   - If connection fails or drops, automatically cycle to the next broker with exponential backoff.
2. Fix Silence Watchdog & Loading State:
   - On page load, show `🟡 CONNECTING / AWAITING TELEMETRY...` instead of immediately flashing `🔴 ESP32 DISCONNECTED`.
   - Allow a generous 30s grace period before transitioning to disconnected state.
   - Implement a Zombie Socket Watchdog: If the WebSocket reports connected but zero packets arrive for 30s, automatically recycle/reconnect the client.
3. Add Browser Lifecycle Listeners:
   - Listen to `window.addEventListener('online', ...)` and `document.addEventListener('visibilitychange', ...)` to immediately test and revive the connection when network returns or tab comes into focus.
4. Implement `safeNum()` parsing:
   - Sanitize all incoming telemetry fields so `null`, undefined, `--`, or invalid strings never produce `NaN` in UI cards, gauge meters, or CSV exports.
5. Ensure 100% zero-build static compliance for Vercel and GitHub Pages.
6. Verify and document all changes in `c:/Users/HP/AirSense-v2/.agents/worker_3/handoff.md` and notify parent.

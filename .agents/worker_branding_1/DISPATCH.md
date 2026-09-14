## 2026-09-12T11:57:32Z

You are an expert full-stack implementation worker. Your working directory is `c:\Users\HP\AirSense-v2\.agents\worker_branding_1`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You MUST read the following files before taking action:
- `c:\Users\HP\AirSense-v2\ORIGINAL_REQUEST.md` (specifically section ## 2026-09-12T11:39:56Z)
- `c:\Users\HP\AirSense-v2\.agents\orchestrator_5\plan.md`
- `c:\Users\HP\AirSense-v2\.agents\orchestrator_5\SCOPE.md`
- `c:\Users\HP\AirSense-v2\.agents\explorer_branding_1\handoff.md`
- `c:\Users\HP\AirSense-v2\.agents\explorer_branding_2\handoff.md`
- `c:\Users\HP\AirSense-v2\.agents\explorer_branding_3\handoff.md`

Your Tasks:

1. Asset Distribution & Manifest Enhancement (Milestone 1):
   - Copy all 7 files from `assets/logo-files/` (`favicon.ico`, `favicon-16x16.png`, `favicon-32x32.png`, `apple-touch-icon.png`, `android-chrome-192x192.png`, `android-chrome-512x512.png`, `site.webmanifest`) into `public/` AND `apps/web/`.
   - Update `site.webmanifest` in `assets/logo-files/`, `public/`, and `apps/web/` so `name` is `"AirSense Pakistan"` and `short_name` is `"AirSense"`.
   - In `apps/api/main.py`, ensure that:
     a) `/assets/logo-files` is mounted via StaticFiles pointing to `assets/logo-files` (or appropriately routed).
     b) Dedicated routes or file responses exist for `/favicon.ico`, `/favicon-16x16.png`, `/favicon-32x32.png`, `/apple-touch-icon.png`, `/android-chrome-192x192.png`, `/android-chrome-512x512.png`, and `/site.webmanifest` returning HTTP 200 with appropriate media types.
     c) All favicon sizes and `site.webmanifest` resolve with HTTP 200 whether requested at `/` or `/assets/logo-files/`.

2. HTML Head & Navigation Header Brand Placement (Milestone 2):
   - In all HTML files in `public/` AND `apps/web/` (`index.html`, `hardware.html`, `diagnostics.html`, `command.html`, `opensource.html`, `enterprise.html`, `sensor-health.html`):
     a) Add standardized `<head>` tags:
        <link rel="icon" type="image/x-icon" href="/favicon.ico">
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
        <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
        <link rel="manifest" href="/site.webmanifest">
     b) In the top navigation header, replace the placeholder `<div class="brand-mark">AS</div>` with:
        <img src="/apple-touch-icon.png" alt="AirSense Logo" class="brand-logo" width="38" height="38">
     c) In the CSS files (`public/css/style.css`, `apps/web/static/css/style.css`, and any inline header styles where `.brand-mark` was styled):
        Style `.brand-logo` with:
        `border-radius: var(--radius-md, 8px); background: #FFFFFF; border: 1px solid var(--border); object-fit: contain; display: block;`
        Ensure zero layout shifts, crisp 38x38 rendering, and flawless contrast on both dark (`#0C1A30`) and light themes. Retain `.brand-mark` styling rules to ensure no regression or breakage.
     d) CRITICAL SAFETY: DO NOT modify, delete, or alter any existing CSS custom properties (like `--blue-600: #0284C7;`, `--font-sans:`) or JavaScript variables/functions (like `hydrateHistoricalTelemetry`, `/api/v1/hardware/daily-csv`, etc.) that existing tests assert.

3. README & Documentation Branding (Milestone 3):
   - Update `README.md` at root to feature the centered official AirSense logo in the header banner using the clean relative path `assets/logo-files/android-chrome-192x192.png`, with centered title and description, as recommended by `explorer_branding_3`.

4. Comprehensive Automated Tests & Verification (Milestone 4):
   - Create `tests/unit/test_branding_and_static_assets.py` to systematically test:
     a) File existence for all 7 assets in `assets/logo-files/`, `public/`, and `apps/web/`.
     b) `site.webmanifest` JSON validation (`name`, `short_name`, icons).
     c) FastAPI route testing via `httpx.AsyncClient` or `TestClient`: verify HTTP 200 on `/favicon.ico`, `/favicon-16x16.png`, `/favicon-32x32.png`, `/apple-touch-icon.png`, `/android-chrome-192x192.png`, `/android-chrome-512x512.png`, `/site.webmanifest`, and `/assets/logo-files/...`.
     d) HTML head link verification for all HTML files in `public/` and `apps/web/`.
     e) Navbar branding verification (`brand-logo` present, placeholder `brand-mark` AS text replaced).
     f) `README.md` logo link resolution verification.
   - Run the full test suite (`py -m pytest`) and confirm 100% pass rate.

5. Report:
   - Document all changes, files modified, test commands executed, and test results in `c:\Users\HP\AirSense-v2\.agents\worker_branding_1\handoff.md`.
   - Update `c:\Users\HP\AirSense-v2\.agents\worker_branding_1\progress.md`.
   - Send completion message to parent via send_message when done.

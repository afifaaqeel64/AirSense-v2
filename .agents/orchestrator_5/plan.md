# Execution Plan — AirSense Official Branding & Asset Integration

## Objective
Integrate the official AirSense logo files located in `assets/logo-files` across the entire project (public dashboards, HTML web templates, favicons, web app manifest, and README documentation).

## Requirements
- R1: Comprehensive Web Asset & Favicon Integration (`public/`, `apps/web/`, all HTML pages)
- R2: Navigation Bar & Header Brand Placement (replace "AS" placeholder with official logo, responsive, light/dark mode)
- R3: Repository & Documentation Branding (`README.md` banner)
- Quality & Verification: 100% test pass on `py -m pytest`, Reviewer APPROVE, Challenger verification, Forensic Auditor CLEAN.

## Phases
1. Phase 0: Survey
   - Explorer 1: Inspect `assets/logo-files` (files, formats, dimensions), find all HTML files in `public/` and `apps/web/`, check current `<head>` links and manifest references.
   - Explorer 2: Inspect existing navbar/header markup, CSS classes, light/dark mode styles, "AS" placeholder implementations.
   - Explorer 3: Inspect existing pytest test suite, test files, web routes/static file mounts in FastAPI backend (`main.py` / `routes`).
2. Phase 1: Implementation
   - Milestone 1: Distribute assets to `public/` and `apps/web/`, ensure FastAPI static mounting serves them correctly under `/` and `/assets/logo-files/`.
   - Milestone 2: Update all HTML pages in `public/` and `apps/web/` (`index.html`, `hardware.html`, `diagnostics.html`, `command.html`, `opensource.html`, `enterprise.html`, `sensor-health.html`) with `<link rel="icon">`, `<link rel="apple-touch-icon">`, `<link rel="manifest">`.
   - Milestone 3: Replace placeholder "AS" with the official logo in top nav headers across all pages, preserving mobile responsiveness and dark/light mode legibility.
   - Milestone 4: Update `README.md` with centered header banner featuring the official AirSense logo.
3. Phase 2: Testing & Multi-Agent Gate
   - Worker runs `py -m pytest` and any new unit/regression tests for asset accessibility.
   - Reviewer 1 & Reviewer 2: Rigorous review of HTML, CSS, responsiveness, and asset paths.
   - Challenger: Empirical validation of HTTP endpoints, file existence, favicon headers.
   - Forensic Auditor: Check for authentic implementation and zero integrity violations.
4. Phase 3: Final Synthesis & Sentinel Handoff.

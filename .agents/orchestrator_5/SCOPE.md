# Scope: AirSense Official Branding & Asset Integration

## Architecture
- Assets: `assets/logo-files/` contains official logo files, icons, and site.webmanifest.
- Public directory: `public/` contains static HTML pages, dashboards, CSS, and JS served by FastAPI at root `/`.
- Apps web directory: `apps/web/` contains web dashboard files/templates.
- Backend: FastAPI serves static files (`public/` and `apps/web/`).
- Docs: `README.md` at root.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | Asset Distribution | Distribute favicon suite & site.webmanifest to public/ and apps/web/ | M1 | ORIGINAL_REQUEST §R1 | DONE |
| 2 | HTML Head Link Integration | Add favicon and manifest link tags to all 14+ HTML pages | M1 | ORIGINAL_REQUEST §R1 | DONE |
| 3 | Static Asset Serving | Ensure FastAPI static mount serves favicons at `/` and `/assets/logo-files/` with HTTP 200 | M1 | ORIGINAL_REQUEST §Acceptance | DONE |
| 4 | Header Brand Placement | Replace "AS" placeholder with official logo in navbar across all dashboards | M2 | ORIGINAL_REQUEST §R2 | DONE |
| 5 | Mobile & Theme Responsiveness | Ensure navbar logo renders crisply in light & dark modes on all viewports | M2 | ORIGINAL_REQUEST §R2 | DONE |
| 6 | Documentation Branding | Center official AirSense logo in README.md header banner | M3 | ORIGINAL_REQUEST §R3 | DONE |
| 7 | Automated Testing & QA | Pytest test suite passes 100%, E2E checks confirm HTTP 200 on all assets | M4 | ORIGINAL_REQUEST §Acceptance | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Asset & Head Tag Integration | Distribute favicons/manifest to public/ & apps/web/, update HTML head tags, ensure static serving | None | DONE |
| 2 | M2: Header Brand Placement | Replace "AS" text with logo image across all dashboards | M1 | DONE |
| 3 | M3: Documentation Branding | Update README.md header banner | None | DONE |
| 4 | M4: Verification & Gate | Pytest, Reviewers, Challenger, Forensic Auditor | M1, M2, M3 | DONE |

# AirSense Pakistan Risk Register

This risk register tracks technical, operational, and architectural risks for the AirSense Pakistan Campus Pilot Phase 1.

| Risk ID | Description | Category | Probability | Impact | Severity | Mitigation Strategy | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RSK-001 | Dependency on unavailable Docker / PostgreSQL in local environment | Environment | High | High | High | Implement local SQLite driver compatibility (Mode A) as primary baseline. | Tech Lead | Active |
| RSK-002 | Accidental leakage of time-series future features during ML feature engineering | ML / Data | Medium | High | High | Enforce chronological walk-forward validation and strict lag calculation after train-test split. | ML Engineer | Active |
| RSK-003 | Hardcoded fake data generation in legacy prototype files | System Integrity | Medium | High | High | Strip all `Math.random()` and `np.random.normal()` logic from dashboard and prediction code. | Developer | Active |
| RSK-004 | Incomplete or unverified campus rooftop GPS coordinates | Data / Ops | Medium | Medium | Medium | Mark missing coordinates as `configuration_required` in `.env.example` and database defaults. | Field Ops | Active |
| RSK-005 | Third-party external API rate limits or outages (OpenAQ, Open-Meteo, WAQI) | API | High | Medium | Medium | Implement Tier 1 provider baseline (Open-Meteo), response caching, and exponential backoff. | Backend Lead | Active |
| RSK-006 | Git repository uninitialized, raising risk of uncommitted file tracking | Ops / Version Control | Medium | Medium | Medium | Prepare comprehensive `.gitignore` before initializing Git repository. | DevOps | Active |
| RSK-007 | Cloud hosting cost overrun on free-tier services | Infrastructure | Low | High | Medium | Use Mode B local campus server baseline (Docker Compose) and zero-cost free tiers. | DevOps | Active |
| RSK-008 | Secret exposure via `.env` or plain text configuration | Security | Low | High | Medium | Add secret scanning checks, `.env` to `.gitignore`, and provide redacted `.env.example`. | Security Lead | Active |

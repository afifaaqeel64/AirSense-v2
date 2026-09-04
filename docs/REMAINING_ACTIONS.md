# AirSense Pakistan Remaining Actions for Phase 4+

This document outlines the required configuration inputs from the AirSense team and the exact command to begin Phase 4 development.

## 1. Required Configuration Inputs from AirSense Team

Before executing Phase 4 (Full Ingestion & Core Features), the following inputs are required from project contacts (Muhammad M. Qureshi for Islamabad, Areesha for Karachi):

1. **Islamabad Campus Rooftop Coordinates**:
   - `ISLAMABAD_LATITUDE` (e.g. `33.7294`)
   - `ISLAMABAD_LONGITUDE` (e.g. `73.0931`)
2. **Karachi Campus Rooftop Coordinates**:
   - `KARACHI_LATITUDE` (e.g. `24.8607`)
   - `KARACHI_LONGITUDE` (e.g. `67.0011`)
3. **ESP32 Device Secret Tokens**:
   - Secret key string for HMAC payload signing / token verification.
4. **Third-Party API Keys (Optional)**:
   - `OPENAQ_API_KEY` (if non-rate-limited OpenAQ access is desired).
   - `OPENWEATHER_API_KEY` (if secondary weather validation is desired).

## 2. Pending Implementation Tasks (Phases 4 through 7)

- **Phase 4**: Full ESP32 sensor HTTP ingestion endpoint, CSV file upload parser, and automated quality control rules (spike, range, stuck sensor).
- **Phase 5**: Tier 1 Open-Meteo weather and air quality background fetcher service.
- **Phase 6**: Feature store, walk-forward cross-validation splitter, multi-model trainer (Linear Regression, Random Forest, XGBoost, LightGBM), prediction interval generation, and SHAP explainability.
- **Phase 7**: Production-grade Environmental Intelligence React dashboard for Islamabad and Karachi campuses.

## 3. Exact Recommended Command to Begin Phase 4

To begin Phase 4 implementation immediately, run:

```bash
py -m pytest && py -m uvicorn apps.api.main:app --port 8000
```

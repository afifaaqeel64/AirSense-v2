## 2026-08-19T14:40:41Z
You are a Codebase Explorer investigating the AirSense platform.
Your Working Directory is: c:\Users\HP\AirSense-v2\.agents\explorer_survey_qc_ml_1\
Please create and maintain your progress.md and write your final findings to c:\Users\HP\AirSense-v2\.agents\explorer_survey_qc_ml_1\handoff.md.

MANDATORY FIRST STEP: Read the original user request at:
c:\Users\HP\AirSense-v2\.agents\ORIGINAL_REQUEST.md

YOUR MISSION:
Investigate and survey:
1. R2: Sensory Quality Control & Auto-Calibration Pipeline:
   - The 6-stage sensory QC engine implementation:
     Stage 1: Range validation (EPA/WHO physical limits, negative reading handling).
     Stage 2: Spike/jump detection (rate-of-change limits).
     Stage 3: Stuck/flatline detection (variance over sliding windows).
     Stage 4: Co-located sensor cross-check (inter-sensor correlation/agreement).
     Stage 5: Meteorological plausibility (e.g. humidity, pressure, temp consistency).
     Stage 6: Moisture/rain flag cross-referencing & temperature/humidity bias correction.
   - QC flags, error codes, and calibration models.
2. R3: Multi-City ML Smog & Air Quality Forecasting:
   - Model architectures (XGBoost, LightGBM, Random Forest, Gradient Boosting).
   - Dataset ingestion & multi-year historical training data for Pakistan urban centers (Karachi, Islamabad, Lahore).
   - Model training, walk-forward cross-validation, feature engineering, lag features, meteorological covariates.
   - Inference pipeline, forecast API endpoints (`/api/v1/forecast/...`), prediction confidence intervals, and explainability/feature importance metrics.
   - Model artifact persistence (`models/` or similar) and runtime loading.

Deliver a structured report in your handoff.md with verified evidence chains, concrete file paths, line references, algorithm specifics, and identified gaps or risks.
When complete, send a message to your caller (parent) with your summary and handoff path.

# AirSense Pakistan Existing Model Audit

This audit evaluates all legacy model artifacts, training scripts, estimators, and historical benchmarks found in the AirSense repository.

## 1. Inventory of Existing Model Artifacts & Code

| Artifact / File | Model Family | Scope / Location | Target / Horizon | Status | Reuse Decision | Audit Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `backend/app/ml/predictor.py` | PyFunc / MLflow | Lahore (Legacy) | AQI / 24-72h | Obsolete / Unsafe | Replace | Hardcoded MLflow URI (`http://mlflow:5000`) and random noise generation (`np.random.normal(0, 5)`). Replaced by Phase 5 local ML registry. |
| `historical_islamabad_benchmark` | Multiple Linear Regression | Islamabad | PM2.5 / 24h | Historical Context | Documented Reference | Based on 123,134 records (August 2021 - June 2024). Reported MAE: 49.27 $\mu g/m^3$, $R^2$: 0.412, Pressure correlation: 0.342. |
| `AirSenseDashboard-try.jsx` | Static Mockup | Lahore | 72h Forecast | Obsolete UI Prototype | Refactor | Prototype frontend using `Math.random()` simulation. Replaced by operational control interface. |

---

## 2. Leakage and Quality Audit

- **Random Train-Test Split**: Legacy scripts in previous scaffolds used random train-test splitting without respecting time-series ordering.
- **Centred Rolling Windows**: Previous feature scripts used centred rolling windows, causing future data leakage into historical feature vectors.
- **Phase 5 Remediation**: All Phase 5 models strictly enforce **expanding-window chronological walk-forward validation** with past-only rolling windows (`.rolling(win, min_periods=1).mean()`).

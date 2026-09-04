# AirSense Pakistan Data Quality Rules & Thresholds

This document specifies the data-quality rules, physical boundaries, penalty scoring, and validation logic enforced by the AirSense Quality Control (QC) Engine (`services/quality_control/qc_engine.py`).

## 1. Quality Score Range & Statuses

- **Quality Score**: Bounded float from `0.0` (unusable/rejected) to `1.0` (perfect quality).
- **Statuses**:
  - `accepted`: Score = `1.0` (all checks passed)
  - `accepted_with_warning`: `0.70 <= Score < 1.0` (minor issues such as high humidity)
  - `review_required`: `0.40 <= Score < 0.70` (particulate ordering violation or rate-of-change spike)
  - `rejected`: `Score < 0.40` or physical impossibility flag

---

## 2. Physical Limits (Hard Validation Boundaries)

| Parameter | Min Value | Max Value | Unit | Action on Violation |
| --- | --- | --- | --- | --- |
| PM1 Concentration | 0.0 | 1000.0 | $\mu g/m^3$ | Flag impossible value, reject record |
| PM2.5 Concentration | 0.0 | 1000.0 | $\mu g/m^3$ | Flag impossible value, reject record |
| PM10 Concentration | 0.0 | 1000.0 | $\mu g/m^3$ | Flag impossible value, reject record |
| Temperature | -20.0 | 60.0 | $^\circ C$ | Flag impossible value, reject record |
| Relative Humidity | 0.0 | 100.0 | $\%$ | Flag impossible value, reject record |
| Atmospheric Pressure | 800.0 | 1100.0 | $\text{hPa}$ | Flag impossible value, reject record |
| Wind Speed | 0.0 | 100.0 | $\text{m/s}$ | Flag impossible value, reject record |
| Wind Direction | 0.0 | 360.0 | degrees | Flag impossible value, reject record |

---

## 3. Physical Ordering Consistency Check

- **Expectation**: $PM1 \le PM2.5 \le PM10$
- **Rule**: If $PM1 > PM2.5$ or $PM2.5 > PM10$:
  - Raw values are **preserved exactly**.
  - `ordering_consistency_flag` is set to `True`.
  - Quality score penalty: `-0.25`.
  - Record marked for operator review.

---

## 4. High Humidity Adjustment ($RH > 90\%$)

- **Background**: At relative humidity above 90%, ambient moisture causes hygroscopic growth of particulate matter, artificially inflating optical PM sensor readings.
- **Rule**: When relative humidity exceeds 90.0%:
  - Raw values are **preserved exactly** (never overwritten or discarded).
  - `high_humidity_flag` is set to `True`.
  - Quality score penalty: `-0.15`.
  - Marked with warning: *"High humidity - potential particulate hygroscopic growth."*

---

## 5. Spike Review Detection

- **Rule**: If consecutive readings for a station exhibit a $PM2.5$ jump $> 150 \mu g/m^3$:
  - `spike_review_flag` is set to `True`.
  - Quality score penalty: `-0.20`.
  - Value is preserved and flagged for operator review (never deleted automatically).

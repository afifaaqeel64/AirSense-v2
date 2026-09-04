# AirSense Pakistan Prediction Interval Methodology

## 1. Overview
AirSense Pakistan quantifies forecasting uncertainty by generating **90% empirical prediction intervals** for every point forecast.

The primary Phase 5 method is **Out-of-Fold Residual Bootstrap Resampling**.

---

## 2. Resampling Algorithm

1. **Residual Collection**: During walk-forward validation, historical out-of-fold residuals $e_i = y_i - \hat{y}_i$ are saved per campus and forecast horizon.
2. **Bootstrap Resampling**: For a new point forecast $\hat{y}_{T+h}$, $B = 500$ residual samples are drawn with replacement using a fixed random seed.
3. **Simulated Distribution**: $y^{(b)} = \hat{y}_{T+h} + e^{(b)}$ for $b = 1 \dots B$.
4. **Quantile Boundaries**:
   - Lower bound: $CI_{lower} = \max(0.0, P_{5.0}(y^{(b)}))$
   - Upper bound: $CI_{upper} = P_{95.0}(y^{(b)})$
5. **Non-Negativity Constraint**: Lower PM2.5 bounds are strictly clamped to $0.0 \mu g/m^3$ since physical particulate mass cannot be negative.

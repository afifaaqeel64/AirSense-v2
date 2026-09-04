# AirSense Pakistan Walk-Forward Validation Specification

## 1. Overview
To prevent future-data leakage and accurately estimate real-world forecasting accuracy, AirSense Pakistan strictly enforces **expanding-window chronological walk-forward validation**.

Random train-test splitting and data shuffling are non-negotiably forbidden for time-series forecasting.

---

## 2. Validation Protocol

```
Fold 1: |========= Train Window (T0 to T1) =========|--- Val Window (T1 to T2) ---|
Fold 2: |================ Train Window (T0 to T2) ================|--- Val Window (T2 to T3) ---|
Fold 3: |======================= Train Window (T0 to T3) =======================|--- Val Window (T3 to T4) ---|
```

- **Expanding Window Origin**: The training dataset starts at $T_0$ and expands forward in time for each fold.
- **Strict Chronological Sequence**: Training end timestamp $\le$ Validation start timestamp.
- **Preprocessing Isolation**: Imputers, scalers, and encoders are fitted strictly inside each training fold and applied to the validation fold without refitting.

---

## 3. Metrics Evaluated Per Fold

1. **Mean Absolute Error (MAE)**: $\frac{1}{N}\sum |y_i - \hat{y}_i|$
2. **Root Mean Squared Error (RMSE)**: $\sqrt{\frac{1}{N}\sum (y_i - \hat{y}_i)^2}$
3. **Median Absolute Error (MedAE)**: $\text{median}(|y_i - \hat{y}_i|)$
4. **Coefficient of Determination ($R^2$)**: $1 - \frac{SS_{res}}{SS_{tot}}$
5. **Mean Absolute Percentage Error (MAPE)**: $\frac{100}{N}\sum \frac{|y_i - \hat{y}_i|}{\max(|y_i|, 1.0)}$
6. **Threshold Exceedance Metrics**: Precision, Recall, and F1-score for PM2.5 $> 35.0 \mu g/m^3$.

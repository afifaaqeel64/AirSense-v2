# AirSense Pakistan External Benchmarking Methodology

## 1. Overview
AirSense Pakistan evaluates its campus PM2.5 forecasts against external weather & AQI providers (e.g. Open-Meteo) using honest, un-biased metrics.

---

## 2. Benchmarking Rules & Alignment

1. **Ground Truth Standard**: Absolute errors are calculated strictly against **accepted onsite PM2.5 ground truth** observations.
2. **Time Window Matching**: Timestamp alignment matches external readings within a $\pm 30$ minute window.
3. **Unit Preservation**: External AQI index values (e.g. WAQI, IQAir) are kept as index values and are NEVER directly subtracted from PM2.5 mass concentrations ($\mu g/m^3$).
4. **Honest Reporting**: If AirSense candidate models perform worse than external model grids, the platform displays the higher error transparently without suppressing or fabricating data.

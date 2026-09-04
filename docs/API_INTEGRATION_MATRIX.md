# AirSense Pakistan API Integration Matrix

This matrix documents external air-quality and meteorological data providers evaluated for AirSense Pakistan.

| Provider | Tier | Auth Required | Endpoint URL | Key Variables | Frequency | Rate Limit | Licence & Attribution | Status | Caching Strategy | Failure Behavior |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Open-Meteo Weather | Tier 1 | None (Free) | `https://api.open-meteo.com/v1/forecast` | Temperature, Relative Humidity, Wind Speed, Wind Direction, Surface Pressure | Hourly | 10,000 calls/day | Open Database License (ODbL), Attribution Required | Primary Weather | 1 Hour Local Cache | Fallback to historical seasonal averages |
| Open-Meteo Air Quality | Tier 1 | None (Free) | `https://air-quality-api.open-meteo.com/v1/air-quality` | PM2.5, PM10, NO2, SO2, O3, Dust, AOD | Hourly | 10,000 calls/day | ODbL, Attribution Required | Primary External AQI | 1 Hour Local Cache | Graceful degradation to sensor data only |
| OpenAQ | Tier 2 | API Key (`OPENAQ_API_KEY`) | `https://api.openaq.org/v2/measurements` | PM2.5, PM10 | Real-time / Hourly | 1,000 calls/hour | CC BY 4.0 | Optional Secondary | 30 Min Local Cache | Skip fetch, log provider warning |
| WAQI (AQICN) | Tier 2 | Token (`WAQI_TOKEN`) | `https://api.waqi.info/feed/geo:` | AQI, PM2.5, Temperature | Real-time | 1,000 calls/minute | Free for non-commercial | Optional Secondary | 15 Min Local Cache | Skip fetch, log provider warning |
| OpenWeatherMap | Tier 2 | Key (`OWM_API_KEY`) | `https://api.openweathermap.org/data/2.5/air_pollution` | PM2.5, PM10, NO2, SO2 | Hourly | 60 calls/minute | Proprietary Free Tier | Optional Secondary | 1 Hour Local Cache | Skip fetch, log provider warning |
| NASA FIRMS | Tier 3 | MAP Key (`NASA_FIRMS_KEY`) | `https://firms.modaps.eosdis.nasa.gov/api/country/csv/` | Thermal Anomalies, FRP (Fire Radiative Power) | Daily | Free Tier | Public Domain | Experimental Biomass Burning | 6 Hour Local Cache | Ignore non-critical fire layer |

## Provider Principles

1. AirSense can operate fully using onsite ESP32 sensor data alone or combined with Tier 1 free providers (Open-Meteo).
2. All external provider requests must use asynchronous HTTP clients (`httpx`) with a 10-second timeout.
3. Errors or rate limits from external APIs must never crash the main AirSense backend or block local sensor ingestion.

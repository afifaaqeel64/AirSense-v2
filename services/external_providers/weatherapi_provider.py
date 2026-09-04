"""AirSense Pakistan WeatherAPI.com Adapter.
Free Tier: 1,000,000 calls / month.
Provides Real-Time Weather, Forecast, Air Quality (PM2.5, PM10, AQI), Astro Data.
"""

import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from apps.api.core.config import settings
from services.external_providers.wmo_models import StandardizedWeatherResponse, get_wmo_metadata


def weatherapi_condition_to_wmo(code: int) -> int:
    """Maps WeatherAPI.com condition codes to standard WMO 4501 codes."""
    # Mapping reference: https://www.weatherapi.com/docs/weather_conditions.json
    mapping = {
        1000: 0,   # Sunny / Clear -> Clear Sky
        1003: 2,   # Partly cloudy -> Partly Cloudy
        1006: 3,   # Cloudy -> Overcast
        1009: 3,   # Overcast -> Overcast
        1030: 45,  # Mist -> Fog
        1063: 51,  # Patchy rain possible -> Light Drizzle
        1066: 71,  # Patchy snow possible -> Slight Snow
        1069: 71,  # Patchy sleet possible -> Snow/Sleet
        1072: 51,  # Patchy freezing drizzle -> Drizzle
        1087: 95,  # Thundery outbreaks -> Thunderstorm
        1114: 73,  # Blowing snow -> Moderate Snow
        1117: 75,  # Blizzard -> Heavy Snow
        1135: 45,  # Fog -> Fog
        1147: 48,  # Freezing fog -> Depositing Rime Fog
        1150: 51,  # Patchy light drizzle -> Light Drizzle
        1153: 51,  # Light drizzle -> Light Drizzle
        1168: 53,  # Freezing drizzle -> Moderate Drizzle
        1171: 55,  # Heavy freezing drizzle -> Dense Drizzle
        1180: 61,  # Patchy light rain -> Slight Rain
        1183: 61,  # Light rain -> Slight Rain
        1186: 63,  # Moderate rain at times -> Moderate Rain
        1189: 63,  # Moderate rain -> Moderate Rain
        1192: 65,  # Heavy rain at times -> Heavy Rain
        1195: 65,  # Heavy rain -> Heavy Rain
        1240: 80,  # Light rain shower -> Slight Rain Showers
        1243: 81,  # Moderate or heavy rain shower -> Moderate Rain Showers
        1246: 82,  # Torrential rain shower -> Violent Rain Showers
        1273: 95,  # Patchy light rain with thunder -> Thunderstorm
        1276: 95,  # Moderate or heavy rain with thunder -> Thunderstorm
        1279: 96,  # Patchy light snow with thunder -> Thunderstorm with Hail
        1282: 99,  # Moderate or heavy snow with thunder -> Heavy Thunderstorm
    }
    return mapping.get(code, 1)


class WeatherAPIProvider:
    PROVIDER_NAME = "weatherapi_com"
    BASE_URL = "https://api.weatherapi.com/v1/current.json"

    @classmethod
    async def fetch_current(cls, latitude: float, longitude: float, api_key: Optional[str] = None) -> Optional[StandardizedWeatherResponse]:
        """Fetches current weather and air quality from WeatherAPI.com."""
        key = api_key or getattr(settings, "WEATHERAPI_KEY", "") or getattr(settings, "WEATHER_API_KEY", "")
        if not key:
            return None

        params = {
            "key": key,
            "q": f"{latitude},{longitude}",
            "aqi": "yes"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(cls.BASE_URL, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                current = data.get("current", {})
                condition = current.get("condition", {})
                code = condition.get("code", 1000)
                wmo_code = weatherapi_condition_to_wmo(code)
                meta = get_wmo_metadata(wmo_code)
                
                # Air quality sub-object
                aq = current.get("air_quality", {})
                pm25 = aq.get("pm2_5")
                pm10 = aq.get("pm10")
                aqi_us = aq.get("us-epa-index")

                # Precip & rain flag
                precip_mm = current.get("precip_mm", 0.0)
                is_raining = (precip_mm or 0.0) > 0.0 or wmo_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]

                # Wind conversion kph to m/s
                wind_kph = current.get("wind_kph", 0.0)
                wind_ms = round(wind_kph / 3.6, 2) if wind_kph is not None else None

                return StandardizedWeatherResponse(
                    provider=cls.PROVIDER_NAME,
                    latitude=latitude,
                    longitude=longitude,
                    timestamp_utc=current.get("last_updated", datetime.now(timezone.utc).isoformat()),
                    temperature_c=current.get("temp_c"),
                    humidity_pct=float(current.get("humidity")) if current.get("humidity") is not None else None,
                    pressure_hpa=current.get("pressure_mb"),
                    wind_speed_ms=wind_ms,
                    wind_direction_deg=float(current.get("wind_degree")) if current.get("wind_degree") is not None else None,
                    precipitation_mm=precip_mm,
                    is_raining=is_raining,
                    wmo_code=wmo_code,
                    weather_description=meta["description"],
                    icon=meta["icon"],
                    lucide_icon=meta["lucide"],
                    status_color=meta["color"],
                    air_quality_pm25=pm25,
                    air_quality_pm10=pm10,
                    aqi=aqi_us,
                    uv_index=current.get("uv")
                )
        except Exception:
            return None

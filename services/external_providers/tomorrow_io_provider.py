"""AirSense Pakistan Tomorrow.io Adapter.
Free Tier: 500 calls / day (25 calls / hour).
Provides Hyperlocal minute-by-minute precipitation and atmospheric indices.
"""

import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from apps.api.core.config import settings
from services.external_providers.wmo_models import StandardizedWeatherResponse, get_wmo_metadata


def tomorrow_weather_code_to_wmo(code: int) -> int:
    """Maps Tomorrow.io weatherCode to standard WMO 4501 code."""
    # Tomorrow.io codes: https://docs.tomorrow.io/reference/data-layers-weather-codes
    mapping = {
        1000: 0,   # Clear, Sunny
        1100: 1,   # Mostly Clear
        1101: 2,   # Partly Cloudy
        1102: 3,   # Mostly Cloudy
        1001: 3,   # Cloudy
        2000: 45,  # Fog
        2100: 45,  # Light Fog
        4000: 51,  # Drizzle
        4001: 61,  # Rain
        4200: 61,  # Light Rain
        4201: 65,  # Heavy Rain
        5000: 71,  # Snow
        5001: 71,  # Flurries
        5100: 71,  # Light Snow
        5101: 75,  # Heavy Snow
        6000: 51,  # Freezing Drizzle
        6001: 61,  # Freezing Rain
        7000: 71,  # Ice Pellets
        8000: 95,  # Thunderstorm
    }
    return mapping.get(code, 0)


class TomorrowIOProvider:
    PROVIDER_NAME = "tomorrow_io"
    BASE_URL = "https://api.tomorrow.io/v4/weather/realtime"

    @classmethod
    async def fetch_current(cls, latitude: float, longitude: float, api_key: Optional[str] = None) -> Optional[StandardizedWeatherResponse]:
        """Fetches realtime weather and air quality from Tomorrow.io."""
        key = api_key or getattr(settings, "TOMORROW_IO_KEY", "") or getattr(settings, "TOMORROW_API_KEY", "")
        if not key:
            return None

        params = {
            "location": f"{latitude},{longitude}",
            "apikey": key,
            "units": "metric"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(cls.BASE_URL, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                data_obj = data.get("data", {})
                values = data_obj.get("values", {})

                w_code = values.get("weatherCode", 1000)
                wmo_code = tomorrow_weather_code_to_wmo(w_code)
                meta = get_wmo_metadata(wmo_code)

                rain_intensity = values.get("rainIntensity", 0.0)
                is_raining = (rain_intensity or 0.0) > 0.0 or wmo_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95]

                return StandardizedWeatherResponse(
                    provider=cls.PROVIDER_NAME,
                    latitude=latitude,
                    longitude=longitude,
                    timestamp_utc=data_obj.get("time", datetime.now(timezone.utc).isoformat()),
                    temperature_c=values.get("temperature"),
                    humidity_pct=float(values.get("humidity")) if values.get("humidity") is not None else None,
                    pressure_hpa=values.get("pressureSurfaceLevel"),
                    wind_speed_ms=values.get("windSpeed"),
                    wind_direction_deg=float(values.get("windDirection")) if values.get("windDirection") is not None else None,
                    precipitation_mm=rain_intensity,
                    is_raining=is_raining,
                    wmo_code=wmo_code,
                    weather_description=meta["description"],
                    icon=meta["icon"],
                    lucide_icon=meta["lucide"],
                    status_color=meta["color"],
                    air_quality_pm25=values.get("particulateMatter25"),
                    air_quality_pm10=values.get("particulateMatter10"),
                    aqi=values.get("epaIndex"),
                    uv_index=values.get("uvIndex")
                )
        except Exception:
            return None

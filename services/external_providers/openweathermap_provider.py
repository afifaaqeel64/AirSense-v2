"""AirSense Pakistan OpenWeatherMap Adapter.
Free Tier: 1,000 calls / day.
Provides Current Weather, Air Pollution API, Forecast data.
"""

import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from apps.api.core.config import settings
from services.external_providers.wmo_models import StandardizedWeatherResponse, get_wmo_metadata


def openweathermap_id_to_wmo(weather_id: int) -> int:
    """Maps OpenWeatherMap weather ID (2xx-8xx) to standard WMO 4501 code."""
    # OWM Weather condition codes: https://openweathermap.org/weather-conditions
    if 200 <= weather_id <= 232:
        return 95  # Thunderstorm
    elif 300 <= weather_id <= 321:
        return 51  # Drizzle
    elif 500 <= weather_id <= 504:
        return 61 if weather_id in (500, 501) else 65  # Rain
    elif weather_id == 511:
        return 61  # Freezing rain
    elif 520 <= weather_id <= 531:
        return 80  # Rain showers
    elif 600 <= weather_id <= 622:
        return 71  # Snow
    elif 701 <= weather_id <= 781:
        return 45  # Atmosphere (Mist, Smoke, Haze, Fog)
    elif weather_id == 800:
        return 0   # Clear
    elif weather_id == 801:
        return 1   # Few clouds
    elif weather_id == 802:
        return 2   # Scattered clouds
    elif weather_id in (803, 804):
        return 3   # Broken / Overcast clouds
    return 0


class OpenWeatherMapProvider:
    PROVIDER_NAME = "openweathermap"
    WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
    AIR_POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

    @classmethod
    async def fetch_current(cls, latitude: float, longitude: float, api_key: Optional[str] = None) -> Optional[StandardizedWeatherResponse]:
        """Fetches current weather and air pollution from OpenWeatherMap."""
        key = api_key or getattr(settings, "OPENWEATHER_API_KEY", "") or getattr(settings, "OPENWEATHERMAP_API_KEY", "")
        if not key:
            return None

        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": key,
            "units": "metric"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                # 1. Fetch current weather
                w_resp = await client.get(cls.WEATHER_URL, params=params)
                if w_resp.status_code != 200:
                    return None
                w_data = w_resp.json()

                main = w_data.get("main", {})
                wind = w_data.get("wind", {})
                weather_arr = w_data.get("weather", [{}])
                first_weather = weather_arr[0] if weather_arr else {}
                owm_id = first_weather.get("id", 800)

                wmo_code = openweathermap_id_to_wmo(owm_id)
                meta = get_wmo_metadata(wmo_code)

                rain_obj = w_data.get("rain", {})
                rain_1h = rain_obj.get("1h", 0.0) if isinstance(rain_obj, dict) else 0.0
                is_raining = (rain_1h or 0.0) > 0.0 or wmo_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]

                # 2. Fetch air pollution (if available)
                pm25 = None
                pm10 = None
                aqi = None
                try:
                    aq_resp = await client.get(cls.AIR_POLLUTION_URL, params=params)
                    if aq_resp.status_code == 200:
                        aq_data = aq_resp.json()
                        aq_list = aq_data.get("list", [{}])
                        if aq_list:
                            first_aq = aq_list[0]
                            components = first_aq.get("components", {})
                            pm25 = components.get("pm2_5")
                            pm10 = components.get("pm10")
                            aqi = first_aq.get("main", {}).get("aqi")
                except Exception:
                    pass

                ts = w_data.get("dt")
                ts_str = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else datetime.now(timezone.utc).isoformat()

                return StandardizedWeatherResponse(
                    provider=cls.PROVIDER_NAME,
                    latitude=latitude,
                    longitude=longitude,
                    timestamp_utc=ts_str,
                    temperature_c=main.get("temp"),
                    humidity_pct=float(main.get("humidity")) if main.get("humidity") is not None else None,
                    pressure_hpa=float(main.get("pressure")) if main.get("pressure") is not None else None,
                    wind_speed_ms=wind.get("speed"),
                    wind_direction_deg=float(wind.get("deg")) if wind.get("deg") is not None else None,
                    precipitation_mm=rain_1h,
                    is_raining=is_raining,
                    wmo_code=wmo_code,
                    weather_description=first_weather.get("description", meta["description"]).title(),
                    icon=meta["icon"],
                    lucide_icon=meta["lucide"],
                    status_color=meta["color"],
                    air_quality_pm25=pm25,
                    air_quality_pm10=pm10,
                    aqi=aqi
                )
        except Exception:
            return None

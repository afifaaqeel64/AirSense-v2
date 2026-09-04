"""AirSense Pakistan Bright Sky (DWD German Weather Service) Adapter.
Open-Source API, MIT Licensed, Zero API Keys Required.
"""

import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from services.external_providers.wmo_models import StandardizedWeatherResponse, get_wmo_metadata


def brightsky_condition_to_wmo(condition: Optional[str], icon: Optional[str]) -> int:
    """Maps Bright Sky condition text / icon to standard WMO 4501 code."""
    cond = (condition or "").lower()
    ic = (icon or "").lower()

    if "thunderstorm" in cond or "thunder" in ic:
        return 95
    elif "snow" in cond or "snow" in ic:
        return 71
    elif "rain" in cond or "rain" in ic:
        return 61
    elif "drizzle" in cond:
        return 51
    elif "fog" in cond or "fog" in ic:
        return 45
    elif "overcast" in cond or "cloudy" in ic:
        return 3
    elif "partly-cloudy" in cond or "partly-cloudy" in ic:
        return 2
    elif "clear" in cond or "clear" in ic:
        return 0
    return 1


class BrightSkyProvider:
    PROVIDER_NAME = "bright_sky"
    BASE_URL = "https://api.brightsky.dev/current_weather"

    @classmethod
    async def fetch_current(cls, latitude: float, longitude: float) -> Optional[StandardizedWeatherResponse]:
        """Fetches current weather from Bright Sky DWD."""
        params = {
            "lat": latitude,
            "lon": longitude,
            "tz": "UTC"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(cls.BASE_URL, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                weather = data.get("weather", {})
                if not weather:
                    return None

                condition = weather.get("condition")
                icon = weather.get("icon")
                wmo_code = brightsky_condition_to_wmo(condition, icon)
                meta = get_wmo_metadata(wmo_code)

                precip = weather.get("precipitation", 0.0)
                is_raining = (precip or 0.0) > 0.0 or wmo_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95]

                # Wind speed in km/h -> m/s
                w_speed_kmh = weather.get("wind_speed")
                w_speed_ms = round(w_speed_kmh / 3.6, 2) if w_speed_kmh is not None else None

                return StandardizedWeatherResponse(
                    provider=cls.PROVIDER_NAME,
                    latitude=latitude,
                    longitude=longitude,
                    timestamp_utc=weather.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    temperature_c=weather.get("temperature"),
                    humidity_pct=float(weather.get("relative_humidity")) if weather.get("relative_humidity") is not None else None,
                    pressure_hpa=weather.get("pressure_msl"),
                    wind_speed_ms=w_speed_ms,
                    wind_direction_deg=float(weather.get("wind_direction")) if weather.get("wind_direction") is not None else None,
                    precipitation_mm=precip,
                    is_raining=is_raining,
                    wmo_code=wmo_code,
                    weather_description=(condition or meta["description"]).title(),
                    icon=meta["icon"],
                    lucide_icon=meta["lucide"],
                    status_color=meta["color"]
                )
        except Exception:
            return None

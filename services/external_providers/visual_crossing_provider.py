"""AirSense Pakistan Visual Crossing Weather Provider Adapter.
Integrates Visual Crossing timeline REST API for current conditions, solar data, and forecast.
"""

import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from apps.api.core.config import settings
from services.external_providers.wmo_models import StandardizedWeatherResponse, get_wmo_metadata


def visual_crossing_icon_to_wmo(icon: Optional[str], conditions: Optional[str]) -> int:
    """Translates Visual Crossing condition/icon strings into standard WMO 4501 code."""
    ic = (icon or "").lower()
    cond = (conditions or "").lower()

    if "thunder" in ic or "thunder" in cond:
        return 95
    elif "snow" in ic or "snow" in cond or "blizzard" in cond:
        return 71
    elif "rain" in ic or "rain" in cond or "shower" in cond:
        return 61
    elif "drizzle" in cond:
        return 51
    elif "fog" in ic or "fog" in cond or "mist" in cond:
        return 45
    elif "cloudy" in ic or "overcast" in cond:
        return 3
    elif "partly-cloudy" in ic:
        return 2
    elif "clear" in ic or "clear" in cond or "sunny" in ic:
        return 0
    return 1


class VisualCrossingProvider:
    PROVIDER_NAME = "visual_crossing"
    BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

    @classmethod
    async def fetch_current(cls, latitude: float, longitude: float) -> Optional[StandardizedWeatherResponse]:
        """Fetches current weather and atmospheric data from Visual Crossing."""
        api_key = getattr(settings, "VISUAL_CROSSING_KEY", "") or getattr(settings, "VISUAL_CROSSING_API_KEY", "")
        if not api_key:
            return None

        url = f"{cls.BASE_URL}/{latitude},{longitude}"
        params = {
            "unitGroup": "metric",
            "include": "current",
            "key": api_key,
            "contentType": "json"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                current = data.get("currentConditions", {})
                if not current:
                    return None

                conditions = current.get("conditions")
                icon_str = current.get("icon")
                wmo_code = visual_crossing_icon_to_wmo(icon_str, conditions)
                meta = get_wmo_metadata(wmo_code)

                precip = current.get("precip", 0.0)
                is_raining = (precip or 0.0) > 0.0 or wmo_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95]

                # Wind speed in km/h -> m/s
                w_speed_kmh = current.get("windspeed")
                w_speed_ms = round(w_speed_kmh / 3.6, 2) if w_speed_kmh is not None else None

                return StandardizedWeatherResponse(
                    provider=cls.PROVIDER_NAME,
                    latitude=latitude,
                    longitude=longitude,
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),
                    temperature_c=current.get("temp"),
                    humidity_pct=float(current.get("humidity")) if current.get("humidity") is not None else None,
                    pressure_hpa=current.get("pressure"),
                    wind_speed_ms=w_speed_ms,
                    wind_direction_deg=float(current.get("winddir")) if current.get("winddir") is not None else None,
                    precipitation_mm=precip,
                    is_raining=is_raining,
                    wmo_code=wmo_code,
                    weather_description=(conditions or meta["description"]).title(),
                    icon=meta["icon"],
                    lucide_icon=meta["lucide"],
                    status_color=meta["color"],
                    uv_index=current.get("uvindex")
                )
        except Exception:
            return None

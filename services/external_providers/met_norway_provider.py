"""AirSense Pakistan MET Norway (Locationforecast 2.0) Adapter.
Open meteorological forecast API by Norwegian Meteorological Institute.
Zero API Keys Required. Requires User-Agent header.
"""

import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from services.external_providers.wmo_models import StandardizedWeatherResponse, get_wmo_metadata


def met_norway_symbol_to_wmo(symbol_code: Optional[str]) -> int:
    """Maps MET Norway symbol_code string to standard WMO 4501 code."""
    sym = (symbol_code or "").lower()
    if "clearsky" in sym:
        return 0
    elif "fair" in sym:
        return 1
    elif "partlycloudy" in sym:
        return 2
    elif "cloudy" in sym or "overcast" in sym:
        return 3
    elif "fog" in sym:
        return 45
    elif "drizzle" in sym:
        return 51
    elif "heavyrain" in sym or "heavyrainshowers" in sym:
        return 65
    elif "rain" in sym:
        return 61
    elif "snow" in sym:
        return 71
    elif "thunder" in sym or "lightning" in sym:
        return 95
    return 1


class METNorwayProvider:
    PROVIDER_NAME = "met_norway"
    BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
    USER_AGENT = "AirSensePakistan/1.0 (airsense.pakistan@beaconhouse.edu.pk)"

    @classmethod
    async def fetch_current(cls, latitude: float, longitude: float) -> Optional[StandardizedWeatherResponse]:
        """Fetches current weather telemetry from MET Norway."""
        params = {
            "lat": round(latitude, 4),
            "lon": round(longitude, 4)
        }
        headers = {
            "User-Agent": cls.USER_AGENT
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(cls.BASE_URL, params=params, headers=headers)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                properties = data.get("properties", {})
                timeseries = properties.get("timeseries", [])
                if not timeseries:
                    return None

                first_entry = timeseries[0]
                data_entry = first_entry.get("data", {})
                instant_details = data_entry.get("instant", {}).get("details", {})
                next_1h = data_entry.get("next_1_hours", {})
                summary = next_1h.get("summary", {})
                sym_code = summary.get("symbol_code", "")
                
                precip_1h = next_1h.get("details", {}).get("precipitation_amount", 0.0)

                wmo_code = met_norway_symbol_to_wmo(sym_code)
                meta = get_wmo_metadata(wmo_code)
                is_raining = (precip_1h or 0.0) > 0.0 or wmo_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95]

                return StandardizedWeatherResponse(
                    provider=cls.PROVIDER_NAME,
                    latitude=latitude,
                    longitude=longitude,
                    timestamp_utc=first_entry.get("time", datetime.now(timezone.utc).isoformat()),
                    temperature_c=instant_details.get("air_temperature"),
                    humidity_pct=float(instant_details.get("relative_humidity")) if instant_details.get("relative_humidity") is not None else None,
                    pressure_hpa=instant_details.get("air_pressure_at_sea_level"),
                    wind_speed_ms=instant_details.get("wind_speed"),
                    wind_direction_deg=float(instant_details.get("wind_from_direction")) if instant_details.get("wind_from_direction") is not None else None,
                    precipitation_mm=precip_1h,
                    is_raining=is_raining,
                    wmo_code=wmo_code,
                    weather_description=sym_code.replace("_", " ").title() if sym_code else meta["description"],
                    icon=meta["icon"],
                    lucide_icon=meta["lucide"],
                    status_color=meta["color"]
                )
        except Exception:
            return None

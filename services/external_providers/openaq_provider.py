"""AirSense Pakistan OpenAQ Ground-Truth Air Quality Provider Adapter.
Integrates the OpenAQ open-source global air quality platform for ground reference data.
"""

import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from apps.api.core.config import settings


class OpenAQProvider:
    PROVIDER_NAME = "openaq"
    BASE_URL = "https://api.openaq.org/v3/locations"

    @classmethod
    async def fetch_latest_by_coords(cls, latitude: float, longitude: float, radius_meters: int = 25000) -> Optional[Dict[str, Any]]:
        """Fetches latest real-time ground-truth air quality measurements near coordinates from OpenAQ."""
        api_key = getattr(settings, "OPENAQ_API_KEY", "")
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key

        params = {
            "coordinates": f"{latitude},{longitude}",
            "radius": radius_meters,
            "limit": 1
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(cls.BASE_URL, params=params, headers=headers)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    return None

                loc = results[0]
                sensors = loc.get("sensors", [])
                
                measurements = {
                    "location_name": loc.get("name"),
                    "locality": loc.get("locality"),
                    "country": loc.get("country", {}).get("name") if isinstance(loc.get("country"), dict) else loc.get("country"),
                    "distance_km": round((loc.get("distance", 0) or 0) / 1000, 1),
                    "coordinates": loc.get("coordinates"),
                    "pm25": None,
                    "pm10": None,
                    "no2": None,
                    "o3": None,
                    "so2": None,
                    "co": None,
                    "last_updated": loc.get("datetimeLast", {}).get("utc") if isinstance(loc.get("datetimeLast"), dict) else datetime.now(timezone.utc).isoformat()
                }

                # Extract sensor values
                for s in sensors:
                    param_name = s.get("parameter", {}).get("name", "").lower() if isinstance(s.get("parameter"), dict) else ""
                    last_val = s.get("latest", {}).get("value") if isinstance(s.get("latest"), dict) else None
                    if last_val is not None:
                        if param_name in ["pm25", "pm2.5", "pm2_5"]:
                            measurements["pm25"] = float(last_val)
                        elif param_name == "pm10":
                            measurements["pm10"] = float(last_val)
                        elif param_name == "no2":
                            measurements["no2"] = float(last_val)
                        elif param_name == "o3":
                            measurements["o3"] = float(last_val)
                        elif param_name == "so2":
                            measurements["so2"] = float(last_val)
                        elif param_name == "co":
                            measurements["co"] = float(last_val)

                return measurements
        except Exception:
            return None

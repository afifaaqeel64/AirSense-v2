"""AirSense Pakistan WMO Weather Codes and Unified Atmospheric Data Models."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


# WMO 4501 Weather Code Definitions, Descriptions, Icons, and Status Colors
WMO_CODE_REGISTRY: Dict[int, Dict[str, str]] = {
    0: {
        "description": "Clear Sky",
        "icon": "fa-sun",
        "lucide": "Sun",
        "color": "#F59E0B",
        "category": "clear"
    },
    1: {
        "description": "Mainly Clear",
        "icon": "fa-cloud-sun",
        "lucide": "CloudSun",
        "color": "#64748B",
        "category": "cloudy"
    },
    2: {
        "description": "Partly Cloudy",
        "icon": "fa-cloud-sun",
        "lucide": "CloudSun",
        "color": "#64748B",
        "category": "cloudy"
    },
    3: {
        "description": "Overcast",
        "icon": "fa-cloud",
        "lucide": "Cloud",
        "color": "#64748B",
        "category": "cloudy"
    },
    45: {
        "description": "Fog",
        "icon": "fa-smog",
        "lucide": "CloudFog",
        "color": "#94A3B8",
        "category": "fog"
    },
    48: {
        "description": "Depositing Rime Fog",
        "icon": "fa-smog",
        "lucide": "CloudFog",
        "color": "#94A3B8",
        "category": "fog"
    },
    51: {
        "description": "Light Drizzle",
        "icon": "fa-cloud-rain",
        "lucide": "CloudDrizzle",
        "color": "#38BDF8",
        "category": "drizzle"
    },
    53: {
        "description": "Moderate Drizzle",
        "icon": "fa-cloud-rain",
        "lucide": "CloudDrizzle",
        "color": "#38BDF8",
        "category": "drizzle"
    },
    55: {
        "description": "Dense Drizzle",
        "icon": "fa-cloud-rain",
        "lucide": "CloudDrizzle",
        "color": "#38BDF8",
        "category": "drizzle"
    },
    61: {
        "description": "Slight Rain",
        "icon": "fa-cloud-showers-heavy",
        "lucide": "CloudRain",
        "color": "#2563EB",
        "category": "rain"
    },
    63: {
        "description": "Moderate Rain",
        "icon": "fa-cloud-showers-heavy",
        "lucide": "CloudRain",
        "color": "#2563EB",
        "category": "rain"
    },
    65: {
        "description": "Heavy Rain",
        "icon": "fa-cloud-showers-heavy",
        "lucide": "CloudRain",
        "color": "#2563EB",
        "category": "rain"
    },
    71: {
        "description": "Slight Snow Fall",
        "icon": "fa-snowflake",
        "lucide": "CloudSnow",
        "color": "#E2E8F0",
        "category": "snow"
    },
    73: {
        "description": "Moderate Snow Fall",
        "icon": "fa-snowflake",
        "lucide": "CloudSnow",
        "color": "#E2E8F0",
        "category": "snow"
    },
    75: {
        "description": "Heavy Snow Fall",
        "icon": "fa-snowflake",
        "lucide": "CloudSnow",
        "color": "#E2E8F0",
        "category": "snow"
    },
    80: {
        "description": "Slight Rain Showers",
        "icon": "fa-cloud-showers-heavy",
        "lucide": "CloudRain",
        "color": "#1D4ED8",
        "category": "rain"
    },
    81: {
        "description": "Moderate Rain Showers",
        "icon": "fa-cloud-showers-heavy",
        "lucide": "CloudRain",
        "color": "#1D4ED8",
        "category": "rain"
    },
    82: {
        "description": "Violent Rain Showers",
        "icon": "fa-cloud-showers-heavy",
        "lucide": "CloudRain",
        "color": "#1D4ED8",
        "category": "rain"
    },
    95: {
        "description": "Thunderstorm",
        "icon": "fa-bolt",
        "lucide": "CloudLightning",
        "color": "#7C3AED",
        "category": "thunderstorm"
    },
    96: {
        "description": "Thunderstorm with Slight Hail",
        "icon": "fa-bolt",
        "lucide": "CloudLightning",
        "color": "#7C3AED",
        "category": "thunderstorm"
    },
    99: {
        "description": "Thunderstorm with Heavy Hail",
        "icon": "fa-bolt",
        "lucide": "CloudLightning",
        "color": "#7C3AED",
        "category": "thunderstorm"
    }
}


def get_wmo_metadata(wmo_code: Optional[int]) -> Dict[str, str]:
    """Resolves WMO code to standardized UI metadata."""
    if wmo_code is None or wmo_code not in WMO_CODE_REGISTRY:
        return {
            "description": "Unknown Weather State",
            "icon": "fa-cloud",
            "lucide": "Cloud",
            "color": "#64748B",
            "category": "unknown"
        }
    return WMO_CODE_REGISTRY[wmo_code]


class StandardizedWeatherResponse(BaseModel):
    provider: str
    latitude: float
    longitude: float
    timestamp_utc: str
    timestamp_pkt: Optional[str] = None
    display_time: Optional[str] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    precipitation_mm: Optional[float] = 0.0
    is_raining: bool = False
    wmo_code: Optional[int] = 0
    weather_description: str = "Clear Sky"
    icon: str = "fa-sun"
    lucide_icon: str = "Sun"
    status_color: str = "#F59E0B"
    air_quality_pm25: Optional[float] = None
    air_quality_pm10: Optional[float] = None
    aqi: Optional[int] = None
    uv_index: Optional[float] = None
    is_cached: bool = False

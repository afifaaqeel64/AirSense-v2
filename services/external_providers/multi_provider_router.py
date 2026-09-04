"""AirSense Pakistan Multi-Provider Weather & Atmospheric Orchestration Engine.
Integrates 8 Weather & Air Quality Providers with Automated Failover & Benchmarking:
1. Open-Meteo (Primary Zero-Key Provider)
2. WeatherAPI.com (1M calls/month, AQI + Astro)
3. OpenWeatherMap (1K calls/day, Air Pollution)
4. Tomorrow.io (500 calls/day, Hyperlocal Precipitation)
5. Bright Sky / DWD (Zero-Key German Weather Service)
6. MET Norway (Zero-Key Nordic Meteorological Institute)
7. Visual Crossing (1K records/day, Historical & Solar)
8. OpenAQ (Global Reference Monitor Aggregator)
"""

import httpx
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from services.external_providers.wmo_models import StandardizedWeatherResponse, get_wmo_metadata
from services.external_providers.weatherapi_provider import WeatherAPIProvider
from services.external_providers.openweathermap_provider import OpenWeatherMapProvider
from services.external_providers.tomorrow_io_provider import TomorrowIOProvider
from services.external_providers.brightsky_provider import BrightSkyProvider
from services.external_providers.met_norway_provider import METNorwayProvider
from services.external_providers.visual_crossing_provider import VisualCrossingProvider
from services.external_providers.openaq_provider import OpenAQProvider


class MultiProviderWeatherEngine:
    """Unified Orchestrator for Real-Time Weather and Air Quality Providers."""

    _CACHE: Dict[str, Dict[str, Any]] = {}
    CACHE_TTL_SECONDS: int = 60

    @classmethod
    async def fetch_from_open_meteo(cls, latitude: float, longitude: float) -> Optional[StandardizedWeatherResponse]:
        """Fetches from Open-Meteo (Primary zero-key provider)."""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
                "rain",
                "weather_code"
            ],
            "timezone": "UTC"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                current = data.get("current", {})
                wmo = current.get("weather_code", 0)
                meta = get_wmo_metadata(wmo)
                rain_val = current.get("rain", 0.0)
                is_raining = (rain_val or 0.0) > 0.0 or wmo in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95]

                return StandardizedWeatherResponse(
                    provider="open_meteo",
                    latitude=latitude,
                    longitude=longitude,
                    timestamp_utc=current.get("time", datetime.now(timezone.utc).isoformat()),
                    temperature_c=current.get("temperature_2m"),
                    humidity_pct=float(current.get("relative_humidity_2m")) if current.get("relative_humidity_2m") is not None else None,
                    pressure_hpa=current.get("surface_pressure"),
                    wind_speed_ms=current.get("wind_speed_10m"),
                    wind_direction_deg=float(current.get("wind_direction_10m")) if current.get("wind_direction_10m") is not None else None,
                    precipitation_mm=rain_val,
                    is_raining=is_raining,
                    wmo_code=wmo,
                    weather_description=meta["description"],
                    icon=meta["icon"],
                    lucide_icon=meta["lucide"],
                    status_color=meta["color"]
                )
        except Exception:
            return None

    @classmethod
    async def get_current_weather(
        cls,
        latitude: float,
        longitude: float,
        preferred_provider: Optional[str] = None,
        use_cache: bool = True
    ) -> StandardizedWeatherResponse:
        """Fetches current weather with intelligent multi-provider fallback hierarchy."""
        cache_key = f"{round(latitude, 3)}_{round(longitude, 3)}_{preferred_provider or 'auto'}"
        now_ts = time.time()

        if use_cache and cache_key in cls._CACHE:
            cached_entry = cls._CACHE[cache_key]
            if now_ts - cached_entry["cached_at"] < cls.CACHE_TTL_SECONDS:
                resp = cached_entry["data"].model_copy()
                resp.is_cached = True
                return resp

        # Provider evaluation sequence
        provider_map = {
            "open_meteo": cls.fetch_from_open_meteo,
            "weatherapi": WeatherAPIProvider.fetch_current,
            "bright_sky": BrightSkyProvider.fetch_current,
            "met_norway": METNorwayProvider.fetch_current,
            "visual_crossing": VisualCrossingProvider.fetch_current,
            "openweathermap": OpenWeatherMapProvider.fetch_current,
            "tomorrow_io": TomorrowIOProvider.fetch_current,
        }

        # Build fallback execution order
        execution_order = []
        if preferred_provider and preferred_provider in provider_map:
            execution_order.append(preferred_provider)

        default_sequence = ["open_meteo", "weatherapi", "bright_sky", "met_norway", "visual_crossing", "openweathermap", "tomorrow_io"]
        for p in default_sequence:
            if p not in execution_order:
                execution_order.append(p)

        # Attempt fetch across sequence
        result: Optional[StandardizedWeatherResponse] = None
        for p_name in execution_order:
            handler = provider_map[p_name]
            try:
                result = await handler(latitude, longitude)
                if result is not None and result.temperature_c is not None:
                    break
            except Exception:
                continue

        # If all external APIs fail, synthesize a safe default
        if result is None:
            meta = get_wmo_metadata(0)
            result = StandardizedWeatherResponse(
                provider="fallback_offline",
                latitude=latitude,
                longitude=longitude,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                temperature_c=28.0,
                humidity_pct=50.0,
                pressure_hpa=1013.25,
                wind_speed_ms=2.5,
                wind_direction_deg=180.0,
                precipitation_mm=0.0,
                is_raining=False,
                wmo_code=0,
                weather_description="Clear Sky (Estimated)",
                icon=meta["icon"],
                lucide_icon=meta["lucide"],
                status_color=meta["color"]
            )

        # Cache result
        cls._CACHE[cache_key] = {
            "cached_at": now_ts,
            "data": result
        }

        return result

    @classmethod
    async def compare_all_providers(cls, latitude: float, longitude: float) -> Dict[str, Any]:
        """Queries all providers in parallel and returns side-by-side comparative benchmarks."""
        providers = [
            ("open_meteo", cls.fetch_from_open_meteo),
            ("weatherapi", WeatherAPIProvider.fetch_current),
            ("bright_sky", BrightSkyProvider.fetch_current),
            ("met_norway", METNorwayProvider.fetch_current),
            ("visual_crossing", VisualCrossingProvider.fetch_current),
            ("openweathermap", OpenWeatherMapProvider.fetch_current),
            ("tomorrow_io", TomorrowIOProvider.fetch_current),
        ]

        results = {}
        successful_count = 0
        temperatures = []
        humidities = []
        pressures = []

        async def fetch_timed(name, handler):
            start = time.time()
            try:
                data = await handler(latitude, longitude)
                elapsed_ms = round((time.time() - start) * 1000, 1)
                return name, data, elapsed_ms, None
            except Exception as e:
                elapsed_ms = round((time.time() - start) * 1000, 1)
                return name, None, elapsed_ms, str(e)

        tasks = [fetch_timed(name, handler) for name, handler in providers]
        responses = await asyncio.gather(*tasks)

        for name, data, elapsed_ms, err in responses:
            if data is not None and data.temperature_c is not None:
                successful_count += 1
                temperatures.append(data.temperature_c)
                if data.humidity_pct is not None:
                    humidities.append(data.humidity_pct)
                if data.pressure_hpa is not None:
                    pressures.append(data.pressure_hpa)

                results[name] = {
                    "status": "available",
                    "latency_ms": elapsed_ms,
                    "temperature_c": data.temperature_c,
                    "humidity_pct": data.humidity_pct,
                    "pressure_hpa": data.pressure_hpa,
                    "wind_speed_ms": data.wind_speed_ms,
                    "is_raining": data.is_raining,
                    "precipitation_mm": data.precipitation_mm,
                    "wmo_code": data.wmo_code,
                    "weather_description": data.weather_description,
                    "icon": data.icon,
                    "status_color": data.status_color,
                    "pm25": data.air_quality_pm25,
                    "pm10": data.air_quality_pm10,
                    "aqi": data.aqi,
                    "uv_index": data.uv_index
                }
            else:
                results[name] = {
                    "status": "unavailable_or_unconfigured",
                    "latency_ms": elapsed_ms,
                    "error": err or "API key missing or provider timed out"
                }

        # Also attempt OpenAQ ground-truth fetch
        openaq_data = await OpenAQProvider.fetch_latest_by_coords(latitude, longitude)
        if openaq_data:
            results["openaq_reference"] = {
                "status": "available",
                "location": openaq_data.get("location_name"),
                "locality": openaq_data.get("locality"),
                "distance_km": openaq_data.get("distance_km"),
                "pm25": openaq_data.get("pm25"),
                "pm10": openaq_data.get("pm10"),
                "no2": openaq_data.get("no2"),
                "o3": openaq_data.get("o3"),
                "last_updated": openaq_data.get("last_updated")
            }

        # Compute consensus averages
        consensus = {
            "avg_temperature_c": round(sum(temperatures) / len(temperatures), 2) if temperatures else None,
            "avg_humidity_pct": round(sum(humidities) / len(humidities), 2) if humidities else None,
            "avg_pressure_hpa": round(sum(pressures) / len(pressures), 2) if pressures else None,
            "providers_reporting": successful_count,
            "total_providers": len(providers)
        }

        return {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "consensus": consensus,
            "providers": results
        }

"""Core AQI business logic."""
from datetime import datetime, timedelta
from typing import List, Optional
from scipy.interpolate import RBFInterpolator
import numpy as np
from app.db import timescale
from app.core.validator import categorize_aqi
from app.db.redis_client import cached
from app.core.config import settings
import structlog

log = structlog.get_logger()

class AQIService:

    @staticmethod
    @cached(ttl=120, prefix="aqi:current")
    async def get_current(city: str, station_id: Optional[str] = None) -> dict:
        readings = await timescale.get_current_aqi(city, station_id)
        summary  = await timescale.get_city_summary(city)
        if not readings:
            return {"city": city, "status": "no_data", "stations": []}
        avg_aqi = summary.get("avg_aqi") or int(np.mean([r["aqi"] for r in readings if r.get("aqi")] or [0]))
        cat_data = categorize_aqi(avg_aqi)
        return {
            "city": city,
            "timestamp": datetime.utcnow().isoformat(),
            "aqi": avg_aqi,
            "aqi_max": summary.get("max_aqi", avg_aqi),
            **cat_data,
            "pm25": summary.get("avg_pm25"),
            "active_stations": summary.get("active_stations", len(readings)),
            "stations": [
                {
                    "station_id": r["station_id"],
                    "source": r["source"],
                    "aqi": r.get("aqi"),
                    "pm25": r.get("pm25"),
                    "pm10": r.get("pm10"),
                    "no2": r.get("no2"),
                    "temperature": r.get("temperature"),
                    "humidity": r.get("humidity"),
                    "lat": r.get("lat"),
                    "lon": r.get("lon"),
                    "last_updated": r["timestamp"].isoformat() if r.get("timestamp") else None,
                    **(categorize_aqi(r["aqi"]) if r.get("aqi") else {}),
                }
                for r in readings
            ],
        }

    @staticmethod
    @cached(ttl=600, prefix="aqi:heatmap")
    async def get_spatial_grid(city: str, resolution: float = 0.01, parameter: str = "aqi") -> dict:
        readings = await timescale.get_current_aqi(city)
        valid = [r for r in readings if r.get(parameter) and r.get("lat") and r.get("lon")]
        if len(valid) < 3:
            return {"type": "FeatureCollection", "features": [], "metadata": {"station_count": len(valid)}}
        bbox = settings.LAHORE_BBOX
        points = np.array([[r["lon"], r["lat"]] for r in valid])
        values = np.array([float(r[parameter]) for r in valid])
        lon_range = np.arange(bbox["lon_min"], bbox["lon_max"], resolution)
        lat_range = np.arange(bbox["lat_min"], bbox["lat_max"], resolution)
        glon, glat = np.meshgrid(lon_range, lat_range)
        grid_pts = np.column_stack([glon.ravel(), glat.ravel()])
        try:
            interp = RBFInterpolator(points, values, kernel="thin_plate_spline", smoothing=0.5)
            grid_vals = np.clip(interp(grid_pts).reshape(glon.shape), 0, 999)
        except Exception as e:
            log.error("interpolation_failed", error=str(e))
            return {"type": "FeatureCollection", "features": []}
        features = [
            {"type": "Feature",
             "geometry": {"type": "Point", "coordinates": [float(lon_range[j]), float(lat_range[i])]},
             "properties": {parameter: float(grid_vals[i, j]), **categorize_aqi(int(grid_vals[i, j]))}}
            for i in range(len(lat_range)) for j in range(len(lon_range))
        ]
        return {"type": "FeatureCollection", "features": features,
                "metadata": {"parameter": parameter, "city": city,
                             "station_count": len(valid), "timestamp": datetime.utcnow().isoformat()}}

    @staticmethod
    @cached(ttl=1800, prefix="aqi:forecast")
    async def get_forecast(city: str, hours: int = 24) -> dict:
        from app.ml.predictor import ModelPredictor
        try:
            return await ModelPredictor.predict_forecast(city=city, hours=hours)
        except Exception as e:
            log.error("forecast_failed", error=str(e))
            return {"city": city, "error": "Forecast unavailable", "forecast": []}

    @staticmethod
    async def get_historical_series(city: str, start: datetime, end: datetime,
                                    parameter: str = "aqi", aggregation: str = "hourly",
                                    station_id: Optional[str] = None) -> dict:
        data = await timescale.get_historical(city, start, end, parameter, aggregation, station_id)
        return {"city": city, "parameter": parameter, "aggregation": aggregation,
                "data_points": len(data), "series": data}

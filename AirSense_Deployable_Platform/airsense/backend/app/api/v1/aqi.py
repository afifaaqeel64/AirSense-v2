from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, Depends
from datetime import datetime, timedelta
from typing import Optional
from app.services.aqi_service import AQIService
from app.core.validator import get_health_assessment
from app.core.metrics import ACTIVE_WS_CONNECTIONS
import asyncio

router = APIRouter(prefix="/aqi", tags=["AQI"])

@router.get("/current/{city}")
async def current_aqi(
    city: str,
    station: Optional[str] = Query(None, description="Filter by station ID")
):
    """Real-time AQI for a city — city-wide average + all station readings."""
    return await AQIService.get_current(city=city.lower(), station_id=station)

@router.get("/heatmap/{city}")
async def aqi_heatmap(
    city: str,
    resolution: float = Query(0.01, ge=0.005, le=0.05),
    parameter: str = Query("aqi", enum=["aqi","pm25","pm10","no2","so2","o3"])
):
    """Interpolated spatial grid for heatmap rendering (GeoJSON FeatureCollection)."""
    return await AQIService.get_spatial_grid(city=city.lower(), resolution=resolution, parameter=parameter)

@router.get("/forecast/{city}")
async def aqi_forecast(
    city: str,
    hours: int = Query(24, ge=1, le=72),
    station: Optional[str] = Query(None)
):
    """ML-powered AQI forecast (1–72 hours ahead)."""
    return await AQIService.get_forecast(city=city.lower(), hours=hours)

@router.get("/historical/{city}")
async def historical_aqi(
    city: str,
    start_date: str = Query(..., description="ISO date e.g. 2024-01-01"),
    end_date:   str = Query(..., description="ISO date e.g. 2024-12-31"),
    parameter:  str = Query("aqi", enum=["aqi","pm25","pm10","no2","so2","co","o3","temperature","humidity"]),
    aggregation:str = Query("hourly", enum=["raw","hourly","daily","monthly"]),
    station:    Optional[str] = Query(None)
):
    """Historical AQI data with flexible time aggregation."""
    start = datetime.fromisoformat(start_date)
    end   = datetime.fromisoformat(end_date)
    if (end - start).days > 365:
        end = start + timedelta(days=365)
    return await AQIService.get_historical_series(
        city=city.lower(), start=start, end=end,
        parameter=parameter, aggregation=aggregation, station_id=station
    )

@router.get("/compare")
async def compare_cities(
    cities: str = Query(..., description="Comma-separated city names e.g. lahore,islamabad"),
    parameter: str = Query("aqi"),
    days: int = Query(7, ge=1, le=30)
):
    """Compare AQI trends across multiple cities."""
    city_list = [c.strip().lower() for c in cities.split(",")[:5]]
    return await AQIService.get_comparison(cities=city_list, parameter=parameter, days=days)

@router.get("/health/{city}")
async def health_risk(
    city: str,
    sensitive: bool = Query(False, description="Elevated risk groups (children, elderly, asthma)")
):
    """Health risk assessment and actionable recommendations based on current AQI."""
    current = await AQIService.get_current(city=city.lower())
    aqi = current.get("aqi", 0)
    health = get_health_assessment(aqi, sensitive)
    return {
        **current,
        **health,
        "sensitive_group": sensitive,
        "who_daily_pm25_limit": 15.0,
        "pakistan_neqs_pm25": 35.0,
    }

@router.websocket("/live/{city}")
async def live_aqi_stream(websocket: WebSocket, city: str):
    """WebSocket — pushes live AQI data every 30 seconds."""
    await websocket.accept()
    ACTIVE_WS_CONNECTIONS.inc()
    try:
        while True:
            data = await AQIService.get_current(city=city.lower())
            await websocket.send_json(data)
            await asyncio.sleep(30)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        ACTIVE_WS_CONNECTIONS.dec()

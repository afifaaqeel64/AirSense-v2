"""AirSense Pakistan Weather Router Compatibility Module.
Re-exports the real-time weather and external provider telemetry endpoints
from provider_router to guarantee compatibility with callers and tests referencing weather_router.
"""

from apps.api.routers.provider_router import (
    router,
    ensure_open_source_minute_records,
    get_weather_telemetry_feed,
    export_weather_telemetry_csv,
    PKT_TZ,
    PROVIDER_DISPLAY_NAMES,
    _build_minute_telemetry_record,
    _OPEN_SOURCE_MINUTE_HISTORY,
)

__all__ = [
    "router",
    "ensure_open_source_minute_records",
    "get_weather_telemetry_feed",
    "export_weather_telemetry_csv",
    "PKT_TZ",
    "PROVIDER_DISPLAY_NAMES",
    "_build_minute_telemetry_record",
    "_OPEN_SOURCE_MINUTE_HISTORY",
]

"""Data validation and normalization for incoming measurements."""
from datetime import datetime
from typing import Optional
import numpy as np

PARAMETER_LIMITS = {
    "pm25":        {"min": 0,  "max": 1000},
    "pm10":        {"min": 0,  "max": 2000},
    "no2":         {"min": 0,  "max": 5000},
    "so2":         {"min": 0,  "max": 3000},
    "co":          {"min": 0,  "max": 50000},
    "o3":          {"min": 0,  "max": 1000},
    "nh3":         {"min": 0,  "max": 1000},
    "aqi":         {"min": 0,  "max": 999},
    "temperature": {"min": -30,"max": 60},
    "humidity":    {"min": 0,  "max": 100},
    "wind_speed":  {"min": 0,  "max": 150},
    "pressure":    {"min": 800,"max": 1100},
}

def validate_and_normalize(raw: dict) -> dict:
    cleaned = {}
    for param, limits in PARAMETER_LIMITS.items():
        val = raw.get(param)
        if val is None:
            continue
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue
        if not (limits["min"] <= val <= limits["max"]):
            cleaned[f"{param}_flagged"] = True
            val = float(np.clip(val, limits["min"], limits["max"]))
        cleaned[param] = val

    # Unit conversions: ppb → µg/m³
    if "no2_ppb" in raw:
        cleaned["no2"] = float(raw["no2_ppb"]) * 1.88
    if "so2_ppb" in raw:
        cleaned["so2"] = float(raw["so2_ppb"]) * 2.62
    if "o3_ppb" in raw:
        cleaned["o3"] = float(raw["o3_ppb"]) * 1.96

    cleaned["source"]    = raw.get("source", "unknown")
    cleaned["station_id"]= raw.get("station_id") or raw.get("station")
    cleaned["city"]      = raw.get("city", "lahore").lower().strip()
    cleaned["lat"]       = raw.get("lat")
    cleaned["lon"]       = raw.get("lon")
    cleaned["timestamp"] = _parse_timestamp(raw.get("timestamp"))
    cleaned["data_quality_score"] = _quality_score(cleaned)
    return cleaned

def _parse_timestamp(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
                    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S+00:00"]:
            try:
                return datetime.strptime(ts.replace("+00:00", "Z").rstrip("Z"), fmt.rstrip("Z"))
            except ValueError:
                continue
    return datetime.utcnow()

def _quality_score(m: dict) -> float:
    key_params = ["pm25", "pm10", "aqi", "temperature", "humidity"]
    present = sum(1 for p in key_params if m.get(p) is not None)
    flagged = sum(1 for k in m if k.endswith("_flagged"))
    return max(0.0, min(1.0, (present / len(key_params)) - flagged * 0.1))

AQI_CATEGORIES = [
    (0,   50,  "Good",                          "#00E400", "#001a00"),
    (51,  100, "Moderate",                       "#FFFF00", "#1a1a00"),
    (101, 150, "Unhealthy for Sensitive Groups", "#FF7E00", "#1a0d00"),
    (151, 200, "Unhealthy",                      "#FF0000", "#1a0000"),
    (201, 300, "Very Unhealthy",                 "#8F3F97", "#150013"),
    (301, 500, "Hazardous",                      "#7E0023", "#1a0007"),
]

def categorize_aqi(aqi: int) -> dict:
    for lo, hi, cat, color, bg in AQI_CATEGORIES:
        if lo <= aqi <= hi:
            return {"category": cat, "color": color, "bg_color": bg,
                    "aqi_lo": lo, "aqi_hi": hi}
    return {"category": "Beyond Index", "color": "#000000", "bg_color": "#000000"}

HEALTH_MESSAGES = {
    "Good": {
        "message": "Air quality is satisfactory. Enjoy outdoor activities.",
        "recommendations": ["Ideal for outdoor exercise", "Open your windows"],
        "outdoor_ok": True, "mask_needed": False,
        "sensitive_message": "Air quality is excellent for everyone."
    },
    "Moderate": {
        "message": "Air quality is acceptable. Some pollutants may affect very sensitive people.",
        "recommendations": ["Sensitive people should limit prolonged outdoor exertion"],
        "outdoor_ok": True, "mask_needed": False,
        "sensitive_message": "Consider reducing intense outdoor activities."
    },
    "Unhealthy for Sensitive Groups": {
        "message": "Children, elderly, and people with heart/lung disease should reduce outdoor activity.",
        "recommendations": ["Wear N95 mask outdoors","Keep windows closed","Run air purifier indoors"],
        "outdoor_ok": True, "mask_needed": True,
        "sensitive_message": "Avoid prolonged outdoor exertion. Stay indoors if possible."
    },
    "Unhealthy": {
        "message": "Everyone may begin to experience health effects. Sensitive groups at serious risk.",
        "recommendations": ["Wear N95/KN95 mask","Avoid outdoor exercise","Keep windows sealed","Check on vulnerable neighbors"],
        "outdoor_ok": False, "mask_needed": True,
        "sensitive_message": "Stay indoors. Seek medical attention if experiencing symptoms."
    },
    "Very Unhealthy": {
        "message": "Health alert: Everyone should avoid outdoor exertion.",
        "recommendations": ["Stay indoors","Seal doors and windows","Use air purifier with HEPA filter","Avoid all outdoor activity"],
        "outdoor_ok": False, "mask_needed": True,
        "sensitive_message": "Emergency conditions for sensitive groups. Stay indoors."
    },
    "Hazardous": {
        "message": "EMERGENCY: Serious health effects for entire population.",
        "recommendations": ["Do not go outside","Seal all openings","Use highest-grade air purifier","Contact health authorities if feeling unwell"],
        "outdoor_ok": False, "mask_needed": True,
        "sensitive_message": "Life-threatening conditions. Do not leave indoors under any circumstances."
    },
}

def get_health_assessment(aqi: int, sensitive: bool = False) -> dict:
    cat_data = categorize_aqi(aqi)
    cat = cat_data["category"]
    health = HEALTH_MESSAGES.get(cat, HEALTH_MESSAGES["Hazardous"])
    return {
        **cat_data,
        "message": health["sensitive_message"] if sensitive else health["message"],
        "recommendations": health["recommendations"],
        "outdoor_ok": health["outdoor_ok"],
        "mask_needed": health["mask_needed"],
    }

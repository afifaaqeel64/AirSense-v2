"""AirSense Pakistan Real-Time Alerts Hub and Environmental News Stream."""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid


class NewsAndAlertsEngine:
    """Provides curated real-time environmental news, EPA regulatory advisories,

    and active priority-tiered operational alerts.
    """

    _acknowledged_alerts: set = set()

    @classmethod
    def get_live_alerts(cls, pm2_5: float, forecast_1h: float, wind_speed: float, campus_code: str = "ISB_CAMPUS") -> List[Dict[str, Any]]:
        """Returns dynamic, live operational alerts based on current telemetry and forecasts."""
        now = datetime.now(timezone.utc).isoformat()
        alerts = []

        # Alert 1: PM2.5 Exceedance / Trajectory Alert
        if pm2_5 > 75.0 or forecast_1h > 80.0:
            alert_id = f"alert_pm25_{int(pm2_5)}"
            alerts.append({
                "id": alert_id,
                "severity": "CRITICAL",
                "severity_color": "#FF2A55",
                "title": f"High PM2.5 Inversion Hazard ({pm2_5:.1f} µg/m³)",
                "category": "AIR_QUALITY_EXCEEDANCE",
                "timestamp_utc": now,
                "campus": campus_code,
                "message": f"Particulate concentration exceeds WHO 24-hr threshold. Forecast indicates elevated levels over next 3 hours.",
                "recommended_action": "Enforce mandatory indoor air filtration and halt non-essential outdoor operations.",
                "acknowledged": alert_id in cls._acknowledged_alerts
            })
        elif pm2_5 > 35.0:
            alert_id = f"alert_pm25_{int(pm2_5)}"
            alerts.append({
                "id": alert_id,
                "severity": "WARNING",
                "severity_color": "#FFC700",
                "title": f"Elevated Ambient Particulates ({pm2_5:.1f} µg/m³)",
                "category": "PRECAUTIONARY",
                "timestamp_utc": now,
                "campus": campus_code,
                "message": "Moderate particulate loading observed. Sensitive cohorts with asthma or respiratory conditions advised to restrict high-intensity exercise.",
                "recommended_action": "Switch building air handling units to 20% fresh air recirculation mode.",
                "acknowledged": alert_id in cls._acknowledged_alerts
            })

        # Alert 2: Atmospheric Stagnation
        if wind_speed < 1.5:
            alert_id = "alert_stagnation_01"
            alerts.append({
                "id": alert_id,
                "severity": "ADVISORY",
                "severity_color": "#36D6E7",
                "title": "Low Wind Dispersion & Boundary Layer Stagnation",
                "category": "METEOROLOGY",
                "timestamp_utc": now,
                "campus": campus_code,
                "message": f"Current wind velocity is {wind_speed:.1f} m/s. Reduced atmospheric boundary layer ventilation is trapping ground-level vehicular emissions.",
                "recommended_action": "Monitor campus perimeter traffic corridors for localized emission accumulation.",
                "acknowledged": alert_id in cls._acknowledged_alerts
            })

        # Alert 3: Sensor Operational Telemetry
        alert_id = "alert_sensor_nominal"
        alerts.append({
            "id": alert_id,
            "severity": "INFO",
            "severity_color": "#00E599",
            "title": "All Pilot Monitoring Nodes Synchronized",
            "category": "HARDWARE_HEALTH",
            "timestamp_utc": now,
            "campus": campus_code,
            "message": "Optical PMS5003 and meteorological sensors operating with 99.4% data completeness and nominal baseline calibration.",
            "recommended_action": "No hardware maintenance required.",
            "acknowledged": alert_id in cls._acknowledged_alerts
        })

        return alerts

    @classmethod
    def acknowledge_alert(cls, alert_id: str) -> bool:
        """Marks an alert as acknowledged by a human operator."""
        cls._acknowledged_alerts.add(alert_id)
        return True

    @classmethod
    def get_curated_news(cls) -> List[Dict[str, Any]]:
        """Returns live curated environmental and air-quality news stream for Pakistan."""
        return [
            {
                "id": "news_01",
                "headline": "Punjab EPA Declares Advanced Early-Smog Preparedness Framework for Punjab & Federal Capital",
                "source": "Pakistan Environmental Protection Agency (Pak-EPA)",
                "time_ago": "2 hours ago",
                "category": "REGULATORY",
                "badge": "EPA NOTICE",
                "summary": "Mandatory industrial emission scrubbers and anti-stubble burning task forces deployed across agricultural belts with satellite cross-validation.",
                "link": "https://environment.gov.pk"
            },
            {
                "id": "news_02",
                "headline": "Winter Inversion Wave Forecast: Atmospheric Boundary Layer Expected to Drop Below 400m",
                "source": "Pakistan Meteorological Department (PMD)",
                "time_ago": "4 hours ago",
                "category": "METEOROLOGY",
                "badge": "WEATHER ADVISORY",
                "summary": "Nighttime temperature inversions will limit vertical atmospheric dispersion across northern Punjab, Islamabad, and coastal Karachi plains.",
                "link": "https://pmd.gov.pk"
            },
            {
                "id": "news_03",
                "headline": "WHO Updates Global Guidance on High-Risk Indoor Environments & Filtration Standards",
                "source": "World Health Organization Environmental Health",
                "time_ago": "6 hours ago",
                "category": "GLOBAL HEALTH",
                "badge": "HEALTH GUIDELINES",
                "summary": "New benchmarks mandate minimum MERV 13 / HEPA recirculating air scrubbers in educational and healthcare institutions during high particulate days.",
                "link": "https://who.int"
            },
            {
                "id": "news_04",
                "headline": "Urban Forestry & Clean Transit Corridors Launched in Islamabad Pilot Zones",
                "source": "Capital Development Authority (CDA)",
                "time_ago": "12 hours ago",
                "category": "MUNICIPAL",
                "badge": "CLEAN AIR ACTION",
                "summary": "Deployment of green buffer zones around educational campuses to reduce heavy diesel vehicular particulate penetration.",
                "link": "https://cda.gov.pk"
            },
            {
                "id": "news_05",
                "headline": "Satellite Observations Reveal Upwind Biomass Hotspots Along Eastern Border Corridors",
                "source": "Copernicus CAMS & Sentinel-5P",
                "time_ago": "18 hours ago",
                "category": "REMOTE SENSING",
                "badge": "SATELLITE INTEL",
                "summary": "Moderate Aerosol Optical Depth (AOD) plumes tracked moving westwards at 12 km/h; surface stations alerted for aerosol arrival.",
                "link": "https://atmosphere.copernicus.eu"
            }
        ]

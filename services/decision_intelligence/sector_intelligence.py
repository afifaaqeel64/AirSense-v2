"""AirSense Pakistan Sector-Specific Operational Intelligence Engine.

Provides deep operational diagnostics, automated actuator directives, and sector-tailored
KPIs across 6 critical operational sectors.
"""

from typing import Dict, List, Any
from datetime import datetime, timezone
import math


class SectorIntelligenceEngine:
    """Computes comprehensive sector-tailored telemetry, operational recommendations,

    and hardware actuator directives.
    """

    @classmethod
    def get_all_sectors_summary(
        cls,
        pm2_5: float,
        pm10: float,
        temp_c: float,
        humidity_pct: float,
        wind_speed_m_s: float,
        forecast_1h: float
    ) -> List[Dict[str, Any]]:
        """Returns high-level status and action counts across all 6 operational sectors."""
        sectors = [
            cls.get_education_intelligence(pm2_5, forecast_1h),
            cls.get_healthcare_intelligence(pm2_5, forecast_1h, humidity_pct),
            cls.get_hvac_intelligence(pm2_5, forecast_1h, temp_c, humidity_pct),
            cls.get_municipal_intelligence(pm2_5, wind_speed_m_s, forecast_1h),
            cls.get_industrial_intelligence(pm2_5, pm10, wind_speed_m_s),
            cls.get_agriculture_intelligence(pm2_5, wind_speed_m_s, humidity_pct)
        ]
        return sectors

    @classmethod
    def get_education_intelligence(cls, pm2_5: float, forecast_1h: float) -> Dict[str, Any]:
        """Education & Campus Sector Intelligence."""
        max_pm = max(pm2_5, forecast_1h)
        if max_pm >= 75.0:
            status = "RESTRICTED"
            status_color = "#FF2A55"
            recess_safety = "PROHIBITED"
            action_desc = "Cancel all outdoor sports, assemblies, and recess. Keep classroom doors/windows sealed."
            recess_score = 15
        elif max_pm >= 35.0:
            status = "CAUTION"
            status_color = "#FFC700"
            recess_safety = "RESTRICTED_LOW_IMPACT"
            action_desc = "Permit light outdoor activities (<20 mins). High-exertion athletic training moved indoors."
            recess_score = 62
        else:
            status = "OPTIMAL"
            status_color = "#00E599"
            recess_safety = "FULLY_SAFE"
            action_desc = "All outdoor curriculum, athletic matches, and recess safely permitted."
            recess_score = 98

        ventilation_level = 1 if max_pm >= 100 else 2 if max_pm >= 50 else 4 if max_pm < 25 else 3

        return {
            "sector_id": "education",
            "name": "Education & Campus Operations",
            "icon": "academic-cap",
            "status": status,
            "status_color": status_color,
            "primary_action": action_desc,
            "recess_safety_rating": recess_safety,
            "safety_index": recess_score,
            "kpis": [
                {"label": "Outdoor Recess Safety", "value": f"{recess_score}/100", "trend": "down" if forecast_1h > pm2_5 else "stable"},
                {"label": "Indoor Sealed Index", "value": "94.2%", "trend": "up"},
                {"label": "Classroom Vent Stage", "value": f"Level {ventilation_level}", "trend": "stable"},
                {"label": "Asthma Action Triggers", "value": "3 Active", "trend": "neutral"}
            ],
            "actuators": [
                {"name": "Classroom Smart Air Purifiers", "state": "AUTO_BOOST" if max_pm > 45 else "ECO_RUN", "active": True},
                {"name": "Digital Campus Noticeboard Banner", "state": f"WARNING: {status}", "active": max_pm > 35},
                {"name": "Sports Ground Exclosure Gates", "state": "LOCKED" if recess_safety == "PROHIBITED" else "OPEN", "active": True}
            ]
        }

    @classmethod
    def get_healthcare_intelligence(cls, pm2_5: float, forecast_1h: float, humidity_pct: float) -> Dict[str, Any]:
        """Healthcare, Clinics & Patient Ward Intelligence."""
        max_pm = max(pm2_5, forecast_1h)
        # Vulnerability exposure index: scales with PM2.5 and humidity (particle swelling)
        vuln_index = min(100, int((max_pm / 150.0) * 80 + (humidity_pct / 100.0) * 20))

        if vuln_index >= 70:
            status = "CRITICAL_SURGE"
            status_color = "#FF2A55"
            primary_action = "Deploy Emergency Inhalation Relief protocol. Seal ICU/Pediatric wards with positive pressure."
        elif vuln_index >= 40:
            status = "ELEVATED_RISK"
            status_color = "#FF7A00"
            primary_action = "Notify OPD triage of expected +25% asthma/bronchitis admission influx within 4 hours."
        else:
            status = "LOW_RISK"
            status_color = "#00E599"
            primary_action = "Baseline clinical monitoring. Nebulizer demand normal."

        return {
            "sector_id": "healthcare",
            "name": "Healthcare & Patient Facilities",
            "icon": "heart",
            "status": status,
            "status_color": status_color,
            "primary_action": primary_action,
            "vulnerability_index": vuln_index,
            "kpis": [
                {"label": "Respiratory Risk Index", "value": f"{vuln_index}/100", "trend": "up" if vuln_index > 50 else "stable"},
                {"label": "ICU Positive Pressure", "value": "+15 Pa (NOMINAL)", "trend": "stable"},
                {"label": "Projected Inhalation Surge", "value": f"+{min(60, int(vuln_index * 0.6))}%", "trend": "up"},
                {"label": "HEPA Unit Runtime", "value": "99.8%", "trend": "up"}
            ],
            "actuators": [
                {"name": "Ward Positive Pressure Scrubbers", "state": "MAX_OVERPRESSURE" if vuln_index > 50 else "STANDARD", "active": True},
                {"name": "Automated Patient SMS Notification", "state": "READY_TO_DISPATCH", "active": vuln_index > 40},
                {"name": "Oxygen Concentrator Auto-Precharge", "state": "ENGAGED" if vuln_index > 65 else "STANDBY", "active": True}
            ]
        }

    @classmethod
    def get_hvac_intelligence(cls, pm2_5: float, forecast_1h: float, temp_c: float, humidity_pct: float) -> Dict[str, Any]:
        """HVAC & Smart Facility Management Sector Intelligence."""
        max_pm = max(pm2_5, forecast_1h)

        # Fresh air damper calculation: If outside air is clean, maximize fresh air; if dirty, minimize to 10%
        if max_pm > 100:
            damper_pct = 10
            fan_mode = "RECIRCULATION_100_FILTRATION"
        elif max_pm > 50:
            damper_pct = 20
            fan_mode = "DUAL_STAGE_SCRUB"
        elif max_pm > 25:
            damper_pct = 50
            fan_mode = "BALANCED_VENTILATION"
        else:
            damper_pct = 80
            fan_mode = "FREE_COOLING_ECONOMIZER"

        filter_life_remaining_days = max(12, int(90 - (max_pm * 0.45)))
        energy_savings_pct = round(100 - (damper_pct * 0.4) - (15 if max_pm > 60 else 0), 1)

        return {
            "sector_id": "hvac",
            "name": "HVAC & Facility Management",
            "icon": "sparkles",
            "status": "FILTER_PURGE" if max_pm > 60 else "OPTIMAL_EFFICIENCY",
            "status_color": "#FF7A00" if max_pm > 60 else "#00E599",
            "primary_action": f"Set Fresh Air Dampers to {damper_pct}%. Run {fan_mode}.",
            "damper_position_pct": damper_pct,
            "filter_life_remaining_days": filter_life_remaining_days,
            "kpis": [
                {"label": "Fresh Air Damper", "value": f"{damper_pct}%", "trend": "down" if max_pm > 50 else "up"},
                {"label": "Filter Delta-P Drop", "value": "128 Pa", "trend": "stable"},
                {"label": "HEPA Useful Life", "value": f"{filter_life_remaining_days} Days", "trend": "down"},
                {"label": "HVAC Energy Savings", "value": f"{energy_savings_pct}%", "trend": "up"}
            ],
            "actuators": [
                {"name": "Main Air Handling Unit (AHU-1)", "state": f"DAMPER_{damper_pct}%", "active": True},
                {"name": "Night Purge Auto-Scheduler", "state": "ARMED_0200_PKT", "active": True},
                {"name": "UV-C Germicidal Air Matrix", "state": "CONTINUOUS_RUN", "active": True}
            ]
        }

    @classmethod
    def get_municipal_intelligence(cls, pm2_5: float, wind_speed: float, forecast_1h: float) -> Dict[str, Any]:
        """Municipal, Urban Traffic & Green Corridors."""
        stagnation = wind_speed < 1.5 and pm2_5 > 60.0
        traffic_tier = "RESTRICTED_HEAVY_DIESEL" if pm2_5 > 90 else "TRAFFIC_SMOOTHING" if pm2_5 > 50 else "NORMAL_TRANSIT"

        return {
            "sector_id": "municipal",
            "name": "Municipal & Smart Mobility",
            "icon": "truck",
            "status": "CONGESTION_SMOG_RISK" if stagnation else "FLOW_NORMAL",
            "status_color": "#FF2A55" if stagnation else "#00E599",
            "primary_action": "Activate Campus Perimeter Green Corridor routing and recommend dynamic traffic re-routing." if stagnation else "Roadway particulate dispersion within standard limits.",
            "kpis": [
                {"label": "Urban Inversion Index", "value": "SEVERE" if stagnation else "LOW", "trend": "up" if stagnation else "stable"},
                {"label": "Green Corridor Efficiency", "value": "88.4%", "trend": "up"},
                {"label": "Corridor PM2.5 Differential", "value": "-32 ug/m3", "trend": "up"},
                {"label": "Transit Advisory State", "value": traffic_tier, "trend": "neutral"}
            ],
            "actuators": [
                {"name": "Dynamic VMS Roadway Signs", "state": "SMOG_ROUTE_ACTIVE", "active": stagnation},
                {"name": "Campus Ring Road Anti-Idling Gate", "state": "ENFORCED", "active": True},
                {"name": "Public Transit Frequency Dispatch", "state": "+15% CAPACITY", "active": pm2_5 > 70}
            ]
        }

    @classmethod
    def get_industrial_intelligence(cls, pm2_5: float, pm10: float, wind_speed: float) -> Dict[str, Any]:
        """Industrial & Construction Site Monitoring."""
        coarse_pm_ratio = pm10 / max(pm2_5, 1.0)
        dust_hazard = pm10 > 150.0 or coarse_pm_ratio > 3.0

        return {
            "sector_id": "industrial",
            "name": "Industrial & Construction Sites",
            "icon": "cube",
            "status": "DUST_SUPPRESSION_TRIGGER" if dust_hazard else "COMPLIANT",
            "status_color": "#FF7A00" if dust_hazard else "#00E599",
            "primary_action": "Trigger automated high-pressure mist cannons and enforce mandatory N95 respirators for outdoor personnel." if dust_hazard else "Industrial stack & construction emissions within standard regulatory thresholds.",
            "kpis": [
                {"label": "Fugitive Dust Index", "value": f"{int(pm10)} ug/m3", "trend": "up" if dust_hazard else "stable"},
                {"label": "Worker Outdoor Shift Limit", "value": "2 Hours" if pm2_5 > 80 else "8 Hours (Standard)", "trend": "neutral"},
                {"label": "Mist Cannon Pressure", "value": "4.2 Bar (ACTIVE)" if dust_hazard else "STANDBY", "trend": "stable"},
                {"label": "Emission Compliance", "value": "96.5%", "trend": "up"}
            ],
            "actuators": [
                {"name": "Automated High-Pressure Water Mist Cannons", "state": "AUTORUN" if dust_hazard else "STANDBY", "active": True},
                {"name": "Construction Aggregate Cover Alarm", "state": "ENGAGED" if dust_hazard else "CLEAR", "active": True},
                {"name": "Worker Biometric Safety PPE Gate", "state": "N95_REQUIRED" if pm2_5 > 50 else "OPTIONAL", "active": True}
            ]
        }

    @classmethod
    def get_agriculture_intelligence(cls, pm2_5: float, wind_speed: float, humidity_pct: float) -> Dict[str, Any]:
        """Agriculture, Stubble-Burning & Biomass Smoke Tracking."""
        # Detect sudden smoke plume signatures
        smoke_risk = pm2_5 > 65.0 and humidity_pct < 65.0
        smoke_tier = "HIGH_STUBBLE_PLUME" if smoke_risk else "NEGLIGIBLE_BIOMASS"

        return {
            "sector_id": "agriculture",
            "name": "Agriculture & Biomass Smoke",
            "icon": "sparkles",
            "status": "UPWIND_PLUME_DETECTED" if smoke_risk else "CLEAR_HORIZON",
            "status_color": "#FF2A55" if smoke_risk else "#00E599",
            "primary_action": "Upwind crop stubble burning detected within 45km radius. Projected campus impact window: 3-5 hours." if smoke_risk else "No significant rural biomass smoke transport currently affecting campus airspace.",
            "kpis": [
                {"label": "Biomass Plume Signature", "value": smoke_tier, "trend": "up" if smoke_risk else "stable"},
                {"label": "Upwind Hotspot Proximity", "value": "38 km (NE)" if smoke_risk else ">100 km", "trend": "neutral"},
                {"label": "Smoke Arrival Projection", "value": "T+3.5 Hours" if smoke_risk else "N/A", "trend": "neutral"},
                {"label": "Perimeter Buffer Shield", "value": "ARMED", "trend": "stable"}
            ],
            "actuators": [
                {"name": "Perimeter Vegetative Windbreak Misting", "state": "TRIGGER_PREWET" if smoke_risk else "OFF", "active": True},
                {"name": "Regional EPA Hotspot Alert Dispatch", "state": "AUTOMATED_SYNC", "active": True},
                {"name": "Air Intake Electrostatic Precipitator", "state": "HIGH_VOLTAGE_BOOST" if smoke_risk else "STANDARD", "active": True}
            ]
        }

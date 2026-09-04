"""AirSense Pakistan Versioned Quality-Control (QC) Engine."""

from datetime import datetime, timezone
import hashlib
from typing import Dict, Any, Tuple, List, Optional
from pydantic import BaseModel


class QCResult(BaseModel):
    quality_score: float
    quality_status: str  # accepted, accepted_with_warning, review_required, rejected, duplicate, stale
    impossible_value_flag: bool = False
    high_humidity_flag: bool = False
    gap_flag: bool = False
    duplicate_flag: bool = False
    stale_flag: bool = False
    spike_review_flag: bool = False
    ordering_consistency_flag: bool = False
    timestamp_flag: bool = False
    validation_messages: List[str] = []
    qc_version: str = "1.0.0"


# Canonical Physical Range Thresholds
PHYSICAL_LIMITS = {
    "pm1": (0.0, 1000.0),
    "pm2_5": (0.0, 1000.0),
    "pm10": (0.0, 1000.0),
    "temperature_c": (-20.0, 60.0),
    "humidity_pct": (0.0, 100.0),
    "pressure_hpa": (800.0, 1100.0),
    "wind_speed_m_s": (0.0, 100.0),
    "wind_direction_deg": (0.0, 360.0),
}


def compute_content_hash(station_code: str, observed_at: datetime, pm2_5: Optional[float], temp: Optional[float]) -> str:
    """Generates a stable content hash for deduplication."""
    obs_str = observed_at.isoformat() if isinstance(observed_at, datetime) else str(observed_at)
    raw_str = f"{station_code}:{obs_str}:{pm2_5}:{temp}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class QualityControlEngine:
    QC_VERSION = "1.0.0"

    @classmethod
    def evaluate_reading(
        cls,
        reading_dict: Dict[str, Any],
        previous_reading: Optional[Dict[str, Any]] = None
    ) -> QCResult:
        """Evaluates a raw reading dictionary and produces a bounded Quality Assessment."""
        messages: List[str] = []
        score = 1.0
        impossible = False
        high_humidity = False
        spike = False
        ordering_issue = False
        timestamp_issue = False

        # 1. Timestamp validation
        obs_time = reading_dict.get("observed_at")
        if not obs_time:
            timestamp_issue = True
            messages.append("Missing observed_at timestamp.")
            score -= 0.5
        elif isinstance(obs_time, datetime):
            now_utc = datetime.now(timezone.utc)
            if obs_time > now_utc:
                timestamp_issue = True
                messages.append("Future timestamp detected.")
                score -= 0.3

        # 2. Physical range checks
        for field, (min_val, max_val) in PHYSICAL_LIMITS.items():
            val = reading_dict.get(field)
            if val is not None:
                if not isinstance(val, (int, float)):
                    impossible = True
                    messages.append(f"Non-numeric value for {field}: {val}")
                    score -= 0.5
                elif val < min_val or val > max_val:
                    impossible = True
                    messages.append(f"Impossible value for {field}: {val} outside [{min_val}, {max_val}]")
                    score -= 0.4

        # 3. High Humidity check (> 90%)
        humidity = reading_dict.get("humidity_pct")
        if humidity is not None and isinstance(humidity, (int, float)) and humidity > 90.0:
            high_humidity = True
            messages.append(f"High humidity ({humidity}%) - potential particulate hygroscopic growth.")
            score -= 0.15

        # 4. Particulate ordering consistency (PM1 <= PM2.5 <= PM10)
        pm1 = reading_dict.get("pm1")
        pm2_5 = reading_dict.get("pm2_5")
        pm10 = reading_dict.get("pm10")

        if pm1 is not None and pm2_5 is not None and pm1 > pm2_5:
            ordering_issue = True
            messages.append(f"Particulate ordering violation: PM1 ({pm1}) > PM2.5 ({pm2_5}).")
            score -= 0.25

        if pm2_5 is not None and pm10 is not None and pm2_5 > pm10:
            ordering_issue = True
            messages.append(f"Particulate ordering violation: PM2.5 ({pm2_5}) > PM10 ({pm10}).")
            score -= 0.25

        # 5. Spike detection (relative to previous reading)
        if previous_reading and pm2_5 is not None:
            prev_pm2_5 = previous_reading.get("pm2_5")
            if prev_pm2_5 is not None:
                delta = abs(pm2_5 - prev_pm2_5)
                if delta > 150.0:
                    spike = True
                    messages.append(f"Spike detected: PM2.5 delta of {delta:.1f} ug/m3 exceeds threshold.")
                    score -= 0.20

        # Bounding score to [0.0, 1.0]
        final_score = max(0.0, min(1.0, round(score, 2)))

        # Status determination
        if impossible or final_score < 0.40:
            status_val = "rejected" if impossible else "review_required"
        elif final_score < 0.70:
            status_val = "review_required"
        elif final_score < 1.0:
            status_val = "accepted_with_warning"
        else:
            status_val = "accepted"

        return QCResult(
            quality_score=final_score,
            quality_status=status_val,
            impossible_value_flag=impossible,
            high_humidity_flag=high_humidity,
            spike_review_flag=spike,
            ordering_consistency_flag=ordering_issue,
            timestamp_flag=timestamp_issue,
            validation_messages=messages,
            qc_version=cls.QC_VERSION
        )

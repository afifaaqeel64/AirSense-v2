"""AirSense Pakistan - Telegram Autonomous Notification & Smog Alert Service.

Dispatches real-time hazardous air quality alerts, Punjab EPA Section 144 compliance
notices, and automated daily partitioned CSV telemetry backups via Telegram Bot API.
"""

import os
import re
import time
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger("airsense.telegram")

DEFAULT_COOLDOWN_SECONDS = 900  # 15 minutes between automated smog alerts per station


def normalize_telegram_bot_token(raw_token: Optional[str]) -> str:
    """Normalizes Telegram Bot Token by stripping quotes, whitespace, URL prefixes, and leading 'bot' prefixes."""
    if not raw_token:
        return ""
    t = str(raw_token).strip().strip('"').strip("'").strip()
    # Remove leading full URL if pasted: https://api.telegram.org/bot<token>
    t = re.sub(r"^https?://api\.telegram\.org/bot", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^api\.telegram\.org/bot", "", t, flags=re.IGNORECASE)
    # Remove trailing endpoint if pasted: /getMe, /sendMessage, /sendDocument
    t = re.sub(r"/[a-zA-Z]+$", "", t)
    # If starts with 'bot' followed immediately by digits and colon (e.g. 'bot712345678:ABC...')
    if t.lower().startswith("bot") and ":" in t:
        parts = t.split(":", 1)
        if parts[0][3:].isdigit():
            t = parts[0][3:] + ":" + parts[1]
    return t.strip().strip('"').strip("'").strip()


def normalize_telegram_chat_id(raw_chat_id: Optional[str]) -> str:
    """Normalizes Telegram Chat ID by stripping quotes, whitespace, and formatting."""
    if not raw_chat_id:
        return ""
    return str(raw_chat_id).strip().strip('"').strip("'").strip()


def mask_secret(val: str, prefix_len: int = 4, suffix_len: int = 4) -> str:
    """Masks sensitive strings for safe logging."""
    if not val:
        return "<empty>"
    if len(val) <= prefix_len + suffix_len:
        return "****"
    return f"{val[:prefix_len]}...{val[-suffix_len:]}"


def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
    timeout: float = 15.0
) -> bool:
    """Sends a text message via Telegram Bot API with token normalization and diagnostics."""
    norm_token = normalize_telegram_bot_token(bot_token)
    norm_chat = normalize_telegram_chat_id(chat_id)

    if not norm_token or not norm_chat:
        logger.warning("[TELEGRAM WARNING] Invalid or empty bot token / chat ID after normalization.")
        return False

    url = f"https://api.telegram.org/bot{norm_token}/sendMessage"
    payload = {
        "chat_id": norm_chat,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    try:
        resp = httpx.post(url, json=payload, timeout=timeout)
        if resp.status_code == 200:
            logger.info(f"[TELEGRAM SUCCESS] Message delivered to chat {norm_chat}")
            return True

        if resp.status_code == 404:
            logger.error(f"[TELEGRAM ERROR] HTTP 404 Not Found from Telegram Bot API with token {mask_secret(norm_token)}.")
        elif resp.status_code == 400:
            logger.error(f"[TELEGRAM ERROR] HTTP 400 Bad Request: {resp.text}")
        elif resp.status_code == 403:
            logger.error(f"[TELEGRAM ERROR] HTTP 403 Forbidden: {resp.text}")
        else:
            logger.warning(f"[TELEGRAM WARNING] Failed to send: HTTP {resp.status_code} - {resp.text}")
        return False
    except Exception as e:
        logger.warning(f"[TELEGRAM ERROR] Network error while sending message: {e}")
        return False


def send_telegram_document(
    bot_token: str,
    chat_id: str,
    file_path: Path,
    caption: str = "",
    timeout: float = 30.0
) -> bool:
    """Sends document/CSV attachment via Telegram Bot API with token normalization."""
    norm_token = normalize_telegram_bot_token(bot_token)
    norm_chat = normalize_telegram_chat_id(chat_id)

    if not norm_token or not norm_chat:
        logger.warning("[TELEGRAM WARNING] Invalid or empty bot token / chat ID after normalization.")
        return False

    safe_caption = caption[:1000] if len(caption) > 1000 else caption
    url = f"https://api.telegram.org/bot{norm_token}/sendDocument"

    try:
        with open(file_path, "rb") as f:
            files = {"document": (file_path.name, f, "text/csv")}
            data = {"chat_id": norm_chat, "caption": safe_caption}
            resp = httpx.post(url, data=data, files=files, timeout=timeout)
            if resp.status_code == 200:
                logger.info(f"[TELEGRAM SUCCESS] Document {file_path.name} delivered to chat {norm_chat}")
                return True
            logger.warning(f"[TELEGRAM WARNING] Failed to upload document: HTTP {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.warning(f"[TELEGRAM ERROR] Network error uploading document: {e}")
        return False


def format_smog_alert_text(
    station_code: str,
    campus_code: str,
    pm25: float,
    pm10: Optional[float] = None,
    temp_c: Optional[float] = None,
    hum_pct: Optional[float] = None,
    aqi: Optional[int] = None,
    severity: str = "HAZARDOUS",
    action_text: Optional[str] = None
) -> str:
    """Formats an urgent Telegram Smog Early Warning alert message."""
    pkt_tz = timezone(timedelta(hours=5))
    pkt_str = datetime.now(pkt_tz).strftime("%Y-%m-%d %H:%M:%S PKT")

    pm10_line = f"\n💨 <b>PM10:</b> {pm10:.1f} µg/m³" if pm10 is not None else ""
    weather_line = ""
    if temp_c is not None and hum_pct is not None:
        weather_line = f"\n🌡️ <b>Temperature:</b> {temp_c:.1f}°C | 💧 <b>Humidity:</b> {hum_pct:.0f}%"

    aqi_str = f" | AQI: {aqi}" if aqi is not None else ""
    rec_action = action_text or (
        "Activate industrial scrubbers, halt high-emission logistics routes, "
        "and transition sensitive school outdoor activities indoors."
    )

    alert_icon = "🚨" if severity.upper() in ["HAZARDOUS", "EMERGENCY", "SECTION 144"] else "⚠️"

    msg = (
        f"{alert_icon} <b>AIRSENSE PAKISTAN — SMOG EARLY WARNING ALERT</b>\n\n"
        f"<b>Station:</b> <code>{station_code}</code> ({campus_code})\n"
        f"<b>Timestamp:</b> {pkt_str}\n"
        f"<b>Severity Level:</b> <b>{severity}</b>{aqi_str}\n\n"
        f"🌫️ <b>PM2.5 Concentration:</b> <b>{pm25:.1f} µg/m³</b>"
        f"{pm10_line}"
        f"{weather_line}\n\n"
        f"📋 <b>Mandated Mitigation Action:</b>\n"
        f"<i>{rec_action}</i>\n\n"
        f"🌐 <i>AirSense Sovereign Decision Intelligence Engine</i>"
    )
    return msg


def send_smog_alert(
    bot_token: str,
    chat_id: str,
    station_code: str,
    campus_code: str,
    pm25: float,
    pm10: Optional[float] = None,
    temp_c: Optional[float] = None,
    hum_pct: Optional[float] = None,
    aqi: Optional[int] = None,
    severity: str = "HAZARDOUS",
    action_text: Optional[str] = None
) -> bool:
    """Sends a formatted smog alert message via Telegram."""
    text = format_smog_alert_text(
        station_code=station_code,
        campus_code=campus_code,
        pm25=pm25,
        pm10=pm10,
        temp_c=temp_c,
        hum_pct=hum_pct,
        aqi=aqi,
        severity=severity,
        action_text=action_text
    )
    return send_telegram_message(bot_token, chat_id, text, parse_mode="HTML")


class TelegramNotificationManager:
    """Manages Telegram notification state, rate limiting, and automated smog alerts."""

    def __init__(self, cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS):
        self.cooldown_seconds = cooldown_seconds
        self._last_alert_timestamps: Dict[str, float] = {}
        self._alert_history = []

    def get_status(self) -> Dict[str, Any]:
        """Returns Telegram integration health and configuration summary."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        norm_token = normalize_telegram_bot_token(token)
        norm_chat = normalize_telegram_chat_id(chat_id)

        return {
            "configured": bool(norm_token and norm_chat),
            "bot_token_configured": bool(norm_token),
            "chat_id_configured": bool(norm_chat),
            "masked_token": mask_secret(norm_token),
            "masked_chat_id": mask_secret(norm_chat),
            "cooldown_seconds": self.cooldown_seconds,
            "total_alerts_dispatched": len(self._alert_history),
            "last_alert": self._alert_history[-1] if self._alert_history else None
        }

    def evaluate_and_dispatch_smog_alert(
        self,
        payload: Dict[str, Any],
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        threshold_pm25: float = 150.0,
        force: bool = False
    ) -> Dict[str, Any]:
        """Evaluates live sensor payload and dispatches Telegram alert if threshold breached."""
        token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

        norm_token = normalize_telegram_bot_token(token)
        norm_chat = normalize_telegram_chat_id(chat)

        if not norm_token or not norm_chat:
            return {
                "triggered": False,
                "dispatched": False,
                "reason": "Telegram credentials not configured"
            }

        # Extract PM2.5
        pm25 = payload.get("pm2_5") or payload.get("pm25")
        if pm25 is None:
            return {
                "triggered": False,
                "dispatched": False,
                "reason": "No PM2.5 reading in payload"
            }

        try:
            pm25_val = float(pm25)
        except (ValueError, TypeError):
            return {
                "triggered": False,
                "dispatched": False,
                "reason": "Invalid PM2.5 value"
            }

        station_code = str(payload.get("station_code") or payload.get("device_id") or "STATION-DEFAULT")
        campus_code = str(payload.get("campus_code") or "DEFAULT")

        # Threshold check
        if pm25_val < threshold_pm25 and not force:
            return {
                "triggered": False,
                "dispatched": False,
                "pm25": pm25_val,
                "threshold": threshold_pm25,
                "reason": "PM2.5 below alert threshold"
            }

        # Cooldown check
        now = time.time()
        last_time = self._last_alert_timestamps.get(station_code, 0.0)
        elapsed = now - last_time

        if elapsed < self.cooldown_seconds and not force:
            return {
                "triggered": True,
                "dispatched": False,
                "pm25": pm25_val,
                "cooldown_remaining": int(self.cooldown_seconds - elapsed),
                "reason": f"Alert suppressed by cooldown ({int(self.cooldown_seconds - elapsed)}s remaining)"
            }

        # Determine severity
        severity = "VERY UNHEALTHY"
        if pm25_val >= 300.0:
            severity = "PUNJAB EPA SECTION 144 EMERGENCY"
        elif pm25_val >= 250.0:
            severity = "SEVERE HAZARDOUS SMOG"
        elif pm25_val >= 150.0:
            severity = "HAZARDOUS"

        pm10 = payload.get("pm10")
        pm10_val = float(pm10) if pm10 is not None else None
        temp = payload.get("temperature_c") or payload.get("temperature")
        temp_val = float(temp) if temp is not None else None
        hum = payload.get("humidity_pct") or payload.get("humidity")
        hum_val = float(hum) if hum is not None else None
        aqi = payload.get("aqi")
        aqi_val = int(aqi) if aqi is not None else None

        action_text = payload.get("action_text")

        sent = send_smog_alert(
            bot_token=norm_token,
            chat_id=norm_chat,
            station_code=station_code,
            campus_code=campus_code,
            pm25=pm25_val,
            pm10=pm10_val,
            temp_c=temp_val,
            hum_pct=hum_val,
            aqi=aqi_val,
            severity=severity,
            action_text=action_text
        )

        if sent:
            self._last_alert_timestamps[station_code] = now
            record = {
                "timestamp": now,
                "station_code": station_code,
                "campus_code": campus_code,
                "pm25": pm25_val,
                "severity": severity,
                "chat_id": mask_secret(norm_chat)
            }
            self._alert_history.append(record)
            if len(self._alert_history) > 100:
                self._alert_history.pop(0)

        return {
            "triggered": True,
            "dispatched": sent,
            "station_code": station_code,
            "pm25": pm25_val,
            "severity": severity
        }


# Global singleton instance
_telegram_manager_instance: Optional[TelegramNotificationManager] = None


def get_telegram_manager() -> TelegramNotificationManager:
    """Returns or initializes singleton TelegramNotificationManager."""
    global _telegram_manager_instance
    if _telegram_manager_instance is None:
        _telegram_manager_instance = TelegramNotificationManager()
    return _telegram_manager_instance

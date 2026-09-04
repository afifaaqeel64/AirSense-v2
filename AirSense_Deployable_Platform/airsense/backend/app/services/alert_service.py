"""Alert management - threshold monitoring and multi-channel notifications."""
import asyncpg, aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.validator import categorize_aqi, get_health_assessment
import structlog

log = structlog.get_logger()
DSN = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

async def check_and_send_alerts(measurement: dict):
    conn = await asyncpg.connect(DSN)
    try:
        subs = await conn.fetch("""
            SELECT s.*, u.email FROM alert_subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.city=$1 AND s.is_active=TRUE
              AND (s.last_alerted_at IS NULL OR
                   s.last_alerted_at < NOW() - (s.cooldown_hours || ' hours')::INTERVAL)
        """, measurement.get("city", "lahore"))

        aqi = measurement.get("aqi", 0)
        for sub in subs:
            if aqi >= sub["threshold_aqi"]:
                await _send_alert(dict(sub), measurement)
                await conn.execute(
                    "UPDATE alert_subscriptions SET last_alerted_at=NOW() WHERE id=$1",
                    sub["id"]
                )
    finally:
        await conn.close()

async def _send_alert(sub: dict, measurement: dict):
    aqi   = measurement.get("aqi", 0)
    city  = measurement.get("city", "Lahore").title()
    cat   = categorize_aqi(aqi)
    health= get_health_assessment(aqi)

    subject = f"🚨 AirSense Alert | AQI {aqi} ({cat['category']}) — {city}"
    body = f"""
AirSense Air Quality Alert

City: {city}
Current AQI: {aqi} — {cat['category']}
PM2.5: {measurement.get('pm25', 'N/A')} µg/m³
PM10:  {measurement.get('pm10', 'N/A')} µg/m³
Time:  {measurement.get('timestamp', datetime.utcnow())}

Health Advisory:
{health['message']}

Recommendations:
{chr(10).join('• ' + r for r in health['recommendations'])}

Outdoor Activities: {'✓ OK' if health['outdoor_ok'] else '✗ Avoid'}
Mask Required: {'Yes — N95/KN95' if health['mask_needed'] else 'No'}

Stay safe. Track live air quality at https://airsense.pk
Unsubscribe: https://airsense.pk/unsubscribe/{sub['id']}
    """.strip()

    channel = sub.get("channel", "email")
    try:
        if channel == "email":
            await _send_email(sub["contact_info"], subject, body)
        elif channel == "sms":
            await _send_sms(sub["contact_info"], f"AirSense: AQI {aqi} ({cat['category']}) in {city}. {health['message'][:100]}")
        elif channel == "webhook":
            await _send_webhook(sub["contact_info"], {
                "aqi": aqi, "city": city.lower(),
                "category": cat["category"], "color": cat["color"],
                "pm25": measurement.get("pm25"),
                "timestamp": str(measurement.get("timestamp", datetime.utcnow())),
                "health_message": health["message"],
            })
        log.info("alert_sent", channel=channel, aqi=aqi, city=city)
    except Exception as e:
        log.error("alert_failed", channel=channel, error=str(e))

async def _send_email(to_email: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg["From"]    = settings.EMAILS_FROM
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    async with aiosmtplib.SMTP(hostname=settings.SMTP_HOST, port=settings.SMTP_PORT) as smtp:
        await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        await smtp.send_message(msg)

async def _send_sms(to_number: str, message: str):
    if not settings.TWILIO_SID:
        log.warning("twilio_not_configured")
        return
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_SID}/Messages.json",
            auth=(settings.TWILIO_SID, settings.TWILIO_TOKEN),
            data={"From": settings.TWILIO_FROM, "To": to_number, "Body": message}
        )

async def _send_webhook(url: str, payload: dict):
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, timeout=10)

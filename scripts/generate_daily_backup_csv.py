"""AirSense Pakistan - Automated Daily 24/7 Telemetry Backup & Telegram Delivery.

Queries RawReading from the database for yesterday's 24 hours (PKT UTC+5),
generates a partitioned CSV file, and dispatches a summary + attachment
via Telegram Bot API at zero cost.

Usage:
    python scripts/generate_daily_backup_csv.py
    python scripts/generate_daily_backup_csv.py --date 2026-09-10
"""

import os
import sys
import csv
import io
import logging
import argparse
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

import httpx

# Add project root to Python module path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Clean empty DATABASE_URL from environment to prevent engine creation crashes
if os.environ.get("DATABASE_URL") == "":
    os.environ.pop("DATABASE_URL", None)

from apps.api.db.session import async_session_maker
from apps.api.db.models import RawReading
from sqlalchemy import select, and_

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("airsense.daily_backup")

DEFAULT_BACKUP_DIR = ROOT_DIR / "data" / "backups" / "daily_csv"


def sanitize_csv_cell(val: Any) -> Any:
    """Sanitizes text value to prevent CSV formula injection while preserving numeric values."""
    if val is None:
        return ""
    if isinstance(val, (int, float, bool)):
        return val
    s = str(val)
    try:
        float(s)
        return s
    except (ValueError, TypeError):
        pass
    if s.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{s}"
    return s


def send_telegram_document(bot_token: str, chat_id: str, file_path: Path, caption: str) -> bool:
    """Sends backup CSV and summary caption via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": (file_path.name, f, "text/csv")}
            data = {"chat_id": chat_id, "caption": caption}
            resp = httpx.post(url, data=data, files=files, timeout=30.0)
            if resp.status_code == 200:
                logger.info(f"[TELEGRAM] Backup file successfully sent to chat {chat_id}")
                return True
            else:
                logger.warning(f"[TELEGRAM WARNING] Failed to send: HTTP {resp.status_code} - {resp.text}")
                return False
    except Exception as e:
        logger.warning(f"[TELEGRAM ERROR] Network error while sending document: {e}")
        return False


async def query_daily_readings(start_utc: datetime, end_utc: datetime):
    """Fetches raw readings within the target UTC window."""
    async with async_session_maker() as session:
        stmt = (
            select(RawReading)
            .where(and_(RawReading.observed_at >= start_utc, RawReading.observed_at < end_utc))
            .order_by(RawReading.observed_at.asc())
        )
        res = await session.execute(stmt)
        return res.scalars().all()


async def async_generate_daily_backup(
    target_date: Optional[datetime.date] = None,
    output_dir: Optional[Path] = None,
    send_telegram: bool = True
) -> Dict[str, Any]:
    """Asynchronously generates daily partitioned CSV backup and dispatches notification."""
    pkt_tz = timezone(timedelta(hours=5))
    now_pkt = datetime.now(pkt_tz)

    if target_date is None:
        target_date = (now_pkt - timedelta(days=1)).date()

    date_str_dash = target_date.strftime("%Y-%m-%d")
    date_str_file = target_date.strftime("%Y_%m_%d")

    # Calendar day in PKT (UTC+5): 00:00:00 to 24:00:00 PKT
    start_pkt = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=pkt_tz)
    end_pkt = start_pkt + timedelta(days=1)

    start_utc = start_pkt.astimezone(timezone.utc)
    end_utc = end_pkt.astimezone(timezone.utc)

    # Determine output path
    out_dir = output_dir or DEFAULT_BACKUP_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_file = out_dir / f"airsense_daily_{date_str_file}.csv"

    logger.info(f"Querying database for date {date_str_dash} (PKT) [{start_utc.isoformat()} to {end_utc.isoformat()} UTC]...")
    readings = await query_daily_readings(start_utc, end_utc)
    total_records = len(readings)
    logger.info(f"Retrieved {total_records} raw readings.")

    # Write CSV
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "reading_id",
            "campus_id",
            "station_id",
            "device_id",
            "sequence_number",
            "observed_at_utc",
            "observed_at_pkt",
            "source",
            "pm1",
            "pm2_5",
            "pm10",
            "temperature_c",
            "humidity_pct",
            "pressure_hpa",
            "rain_flag",
            "aqi"
        ])

        for r in readings:
            obs_utc_str = r.observed_at.isoformat() if r.observed_at else ""
            if r.observed_at:
                obs_dt = r.observed_at if r.observed_at.tzinfo else r.observed_at.replace(tzinfo=timezone.utc)
                obs_pkt = obs_dt.astimezone(pkt_tz)
                obs_pkt_str = obs_pkt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                obs_pkt_str = ""

            writer.writerow([
                sanitize_csv_cell(r.id),
                sanitize_csv_cell(r.campus_id),
                sanitize_csv_cell(r.station_id),
                sanitize_csv_cell(r.device_id),
                sanitize_csv_cell(r.sequence_number),
                sanitize_csv_cell(obs_utc_str),
                sanitize_csv_cell(obs_pkt_str),
                sanitize_csv_cell(r.source),
                sanitize_csv_cell(r.pm1),
                sanitize_csv_cell(r.pm2_5),
                sanitize_csv_cell(r.pm10),
                sanitize_csv_cell(r.temperature_c),
                sanitize_csv_cell(r.humidity_pct),
                sanitize_csv_cell(r.pressure_hpa),
                sanitize_csv_cell(r.rain_flag),
                sanitize_csv_cell(r.aqi)
            ])

    logger.info(f"Daily backup CSV saved to: {csv_file}")

    # Compute summaries
    pm25_vals = [float(r.pm2_5) for r in readings if r.pm2_5 is not None]
    temp_vals = [float(r.temperature_c) for r in readings if r.temperature_c is not None]
    hum_vals = [float(r.humidity_pct) for r in readings if r.humidity_pct is not None]

    avg_pm25 = (sum(pm25_vals) / len(pm25_vals)) if pm25_vals else 0.0
    min_pm25 = min(pm25_vals) if pm25_vals else 0.0
    max_pm25 = max(pm25_vals) if pm25_vals else 0.0
    avg_temp = (sum(temp_vals) / len(temp_vals)) if temp_vals else 0.0
    avg_hum = (sum(hum_vals) / len(hum_vals)) if hum_vals else 0.0

    caption = (
        f"AirSense Pakistan - Daily Telemetry Backup\n"
        f"Date (PKT): {date_str_dash}\n"
        f"Total Records: {total_records}\n"
        f"PM2.5: Avg {avg_pm25:.1f} μg/m³ (Min: {min_pm25:.1f}, Max: {max_pm25:.1f})\n"
        f"Temperature: Avg {avg_temp:.1f}°C\n"
        f"Humidity: Avg {avg_hum:.0f}%\n"
        f"File: {csv_file.name}"
    )

    telegram_sent = False
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if send_telegram and bot_token and chat_id:
        telegram_sent = send_telegram_document(bot_token, chat_id, csv_file, caption)
    else:
        logger.info("[INFO] Telegram delivery skipped (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not configured).")

    return {
        "status": "success",
        "target_date": date_str_dash,
        "csv_path": str(csv_file),
        "total_records": total_records,
        "telegram_sent": telegram_sent,
        "summary": {
            "avg_pm25": avg_pm25,
            "min_pm25": min_pm25,
            "max_pm25": max_pm25,
            "avg_temp": avg_temp,
            "avg_hum": avg_hum
        }
    }


def generate_daily_backup(
    target_date: Optional[datetime.date] = None,
    output_dir: Optional[Path] = None,
    send_telegram: bool = True
) -> Dict[str, Any]:
    """Generates daily partitioned CSV backup and dispatches notification, safely handling running event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(async_generate_daily_backup(target_date, output_dir, send_telegram)))
            return future.result()
    else:
        return asyncio.run(async_generate_daily_backup(target_date, output_dir, send_telegram))


def main():
    parser = argparse.ArgumentParser(description="AirSense Daily Telemetry Backup & Telegram Exporter")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD (defaults to yesterday in PKT UTC+5)")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save backup CSV")
    parser.add_argument("--db-url", type=str, default=None, help="Optional database connection URL override")
    parser.add_argument("--no-telegram", action="store_true", help="Disable Telegram dispatch")
    args = parser.parse_args()

    if args.db_url:
        os.environ["DATABASE_URL"] = args.db_url

    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Expected YYYY-MM-DD.")
            sys.exit(1)

    out_dir = Path(args.output_dir) if args.output_dir else None
    res = generate_daily_backup(target_date=target_date, output_dir=out_dir, send_telegram=not args.no_telegram)
    logger.info(f"Backup process finished with status: {res['status']}")


if __name__ == "__main__":
    main()

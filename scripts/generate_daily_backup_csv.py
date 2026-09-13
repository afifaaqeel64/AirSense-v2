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

import re
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


def normalize_telegram_bot_token(raw_token: Optional[str]) -> str:
    """Normalizes Telegram Bot Token by stripping quotes, whitespace, URL prefixes, and leading 'bot' prefixes."""
    if not raw_token:
        return ""
    t = str(raw_token).strip().strip('"').strip("'").strip()
    # Remove leading full URL if pasted: https://api.telegram.org/bot<token>
    t = re.sub(r"^https?://api\.telegram\.org/bot", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^api\.telegram\.org/bot", "", t, flags=re.IGNORECASE)
    # Remove trailing endpoint if pasted: /getMe or /sendDocument
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


def send_telegram_document(bot_token: str, chat_id: str, file_path: Path, caption: str) -> bool:
    """Sends backup CSV and summary caption via Telegram Bot API with token normalization and diagnostics."""
    norm_token = normalize_telegram_bot_token(bot_token)
    norm_chat = normalize_telegram_chat_id(chat_id)

    if not norm_token or not norm_chat:
        logger.warning("[TELEGRAM WARNING] Invalid or empty bot token / chat ID after normalization.")
        return False

    # Telegram caption length limit is 1024 characters
    safe_caption = caption[:1000] if len(caption) > 1000 else caption

    # Candidates to try: normalized token first, then raw token if different
    candidates = [norm_token]
    raw_stripped = bot_token.strip().strip('"').strip("'").strip()
    if raw_stripped and raw_stripped not in candidates:
        candidates.append(raw_stripped)

    for idx, token in enumerate(candidates):
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        masked_tok = mask_secret(token)
        try:
            with open(file_path, "rb") as f:
                files = {"document": (file_path.name, f, "text/csv")}
                data = {"chat_id": norm_chat, "caption": safe_caption}
                logger.info(f"[TELEGRAM] Dispatching backup to chat {norm_chat} with token {masked_tok} (attempt {idx+1}/{len(candidates)})...")
                resp = httpx.post(url, data=data, files=files, timeout=30.0)

                if resp.status_code == 200:
                    logger.info(f"[TELEGRAM SUCCESS] Backup file successfully delivered to chat {norm_chat}")
                    return True

                # If 404 and we have another candidate, try candidate
                if resp.status_code == 404 and idx + 1 < len(candidates):
                    logger.warning(f"[TELEGRAM] HTTP 404 on attempt {idx+1}, trying fallback candidate...")
                    continue

                # Log detailed diagnostics for common Telegram errors
                if resp.status_code == 404:
                    logger.error(
                        f"[TELEGRAM ERROR] HTTP 404 Not Found from Telegram Bot API. "
                        f"The bot token {masked_tok} was rejected by api.telegram.org. "
                        f"Please verify TELEGRAM_BOT_TOKEN in GitHub repository secrets matches @BotFather."
                    )
                elif resp.status_code == 400:
                    logger.error(
                        f"[TELEGRAM ERROR] HTTP 400 Bad Request: {resp.text}. "
                        f"If the error is 'chat not found', the recipient user must open Telegram and send /start to the bot."
                    )
                elif resp.status_code == 403:
                    logger.error(
                        f"[TELEGRAM ERROR] HTTP 403 Forbidden: {resp.text}. "
                        f"The bot was blocked by the user or lacks permission to message chat {norm_chat}."
                    )
                else:
                    logger.warning(f"[TELEGRAM WARNING] Failed to send: HTTP {resp.status_code} - {resp.text}")

                return False

        except Exception as e:
            logger.warning(f"[TELEGRAM ERROR] Network error while sending document: {e}")
            if idx + 1 < len(candidates):
                continue
            return False

    return False


async def query_daily_readings(start_utc: datetime, end_utc: datetime, max_retries: int = 3):
    """Fetches raw readings within the target UTC window with retry backoff."""
    for attempt in range(max_retries):
        try:
            async with async_session_maker() as session:
                stmt = (
                    select(RawReading)
                    .where(and_(RawReading.observed_at >= start_utc, RawReading.observed_at < end_utc))
                    .order_by(RawReading.observed_at.asc())
                )
                res = await session.execute(stmt)
                return res.scalars().all()
        except Exception as e:
            if attempt + 1 < max_retries:
                wait_sec = 2 ** (attempt + 1)
                logger.warning(f"Database query attempt {attempt + 1} failed ({e}). Retrying in {wait_sec}s...")
                await asyncio.sleep(wait_sec)
            else:
                logger.error(f"Database query failed after {max_retries} attempts: {e}")
                raise


async def async_generate_daily_backup(
    target_date: Optional[datetime.date] = None,
    output_dir: Optional[Path] = None,
    send_telegram: bool = True,
    tier: str = "all"
) -> Dict[str, Any]:
    """Asynchronously generates 3-tier partitioned CSV backups, cross-validation, and dispatches notification."""
    import zipfile
    from services.quality_control.three_tier_framework import (
        fetch_verified_opensource_hourly,
        build_tier1_dataset,
        build_tier2_dataset,
        build_tier3_dataset,
        export_dataset_to_csv,
        FULL_SCHEMA_COLUMNS
    )

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

    # Determine output paths
    out_dir = output_dir or DEFAULT_BACKUP_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_file = out_dir / f"airsense_daily_{date_str_file}.csv"
    tier1_file = out_dir / f"tier1_hardware_chemical_{date_str_file}.csv"
    tier2_file = out_dir / f"tier2_opensource_pure_{date_str_file}.csv"
    tier3_file = out_dir / f"tier3_ml_cumulative_validated_{date_str_file}.csv"
    zip_file = out_dir / f"airsense_tiered_daily_{date_str_file}.zip"

    logger.info(f"Querying database for date {date_str_dash} (PKT) [{start_utc.isoformat()} to {end_utc.isoformat()} UTC]...")
    readings = await query_daily_readings(start_utc, end_utc)
    total_records = len(readings)
    logger.info(f"Retrieved {total_records} raw readings.")

    # 1. Fetch verified open-source physical & chemical atmospheric variables
    logger.info(f"Fetching verified open-source atmospheric grid data for {date_str_dash}...")
    os_hourly = await fetch_verified_opensource_hourly(target_date)

    # 2. Build datasets for Tier 1, Tier 2, Tier 3
    tier1_rows = build_tier1_dataset(readings, os_hourly) if total_records > 0 else []
    tier2_rows = build_tier2_dataset(os_hourly)
    tier3_rows = build_tier3_dataset(readings, os_hourly) if total_records > 0 else []

    # Export Tiered CSV files
    export_dataset_to_csv(tier1_rows, tier1_file)
    export_dataset_to_csv(tier2_rows, tier2_file)
    export_dataset_to_csv(tier3_rows, tier3_file)
    logger.info(f"Tiered CSV files saved: {tier1_file.name}, {tier2_file.name}, {tier3_file.name}")

    # 3. Export Legacy CSV (maintains 100% backward compatibility for existing consumers)
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

    logger.info(f"Legacy backup CSV saved to: {csv_file}")

    # 4. Package all tiered datasets into a single zip archive
    try:
        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tier1_file, arcname=tier1_file.name)
            zf.write(tier2_file, arcname=tier2_file.name)
            zf.write(tier3_file, arcname=tier3_file.name)
            zf.write(csv_file, arcname=csv_file.name)
        logger.info(f"Bundled tiered archive saved to: {zip_file}")
    except Exception as e:
        logger.warning(f"Could not package zip archive: {e}")

    # 5. Compute summaries
    pm25_vals = [float(r.pm2_5) for r in readings if r.pm2_5 is not None]
    temp_vals = [float(r.temperature_c) for r in readings if r.temperature_c is not None]
    hum_vals = [float(r.humidity_pct) for r in readings if r.humidity_pct is not None]

    avg_pm25 = (sum(pm25_vals) / len(pm25_vals)) if pm25_vals else 0.0
    min_pm25 = min(pm25_vals) if pm25_vals else 0.0
    max_pm25 = max(pm25_vals) if pm25_vals else 0.0
    avg_temp = (sum(temp_vals) / len(temp_vals)) if temp_vals else 0.0
    avg_hum = (sum(hum_vals) / len(hum_vals)) if hum_vals else 0.0
    valid_tier3_count = sum(1 for r in tier3_rows if r.get("is_valid"))

    caption = (
        f"AirSense Pakistan - 3-Tier Daily Snapshot\n"
        f"Date (PKT): {date_str_dash}\n"
        f"Tier 1 (HW+Chem): {len(tier1_rows)} rows\n"
        f"Tier 2 (OpenSource): {len(tier2_rows)} rows\n"
        f"Tier 3 (ML Validated): {len(tier3_rows)} rows (Valid: {valid_tier3_count})\n"
        f"PM2.5: Avg {avg_pm25:.1f} μg/m³ (Min: {min_pm25:.1f}, Max: {max_pm25:.1f})\n"
        f"Temperature: Avg {avg_temp:.1f}°C | Humidity: Avg {avg_hum:.0f}%\n"
        f"Primary Defining File: {tier3_file.name if total_records > 0 else csv_file.name}"
    )

    telegram_sent = False
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    # Delivery file: attach defining Tier 3 file if records exist, otherwise legacy CSV
    delivery_file = tier3_file if total_records > 0 else csv_file

    if send_telegram and bot_token and chat_id:
        logger.info(f"[TELEGRAM] Initiating notification (Token length: {len(bot_token)}, Chat ID: {mask_secret(chat_id)})...")
        telegram_sent = send_telegram_document(bot_token, chat_id, delivery_file, caption)
    else:
        logger.info(
            f"[INFO] Telegram delivery skipped: "
            f"send_telegram={send_telegram}, "
            f"bot_token_present={bool(bot_token)}, "
            f"chat_id_present={bool(chat_id)}."
        )

    return {
        "status": "success",
        "target_date": date_str_dash,
        "csv_path": str(csv_file),
        "tier1_csv_path": str(tier1_file),
        "tier2_csv_path": str(tier2_file),
        "tier3_csv_path": str(tier3_file),
        "zip_path": str(zip_file),
        "total_records": total_records,
        "telegram_sent": telegram_sent,
        "tier_counts": {
            "tier1": len(tier1_rows),
            "tier2": len(tier2_rows),
            "tier3": len(tier3_rows),
            "valid_tier3": valid_tier3_count
        },
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
    send_telegram: bool = True,
    tier: str = "all"
) -> Dict[str, Any]:
    """Generates daily partitioned CSV backup and dispatches notification, safely handling running event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(async_generate_daily_backup(target_date, output_dir, send_telegram, tier=tier)))
            return future.result()
    else:
        return asyncio.run(async_generate_daily_backup(target_date, output_dir, send_telegram, tier=tier))


def main():
    parser = argparse.ArgumentParser(description="AirSense 3-Tier Telemetry Backup & Telegram Exporter")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD (defaults to yesterday in PKT UTC+5)")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save backup CSV")
    parser.add_argument("--db-url", type=str, default=None, help="Optional database connection URL override")
    parser.add_argument("--tier", type=str, choices=["1", "2", "3", "all"], default="all", help="Specific tier to focus on (default: all)")
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
    res = generate_daily_backup(target_date=target_date, output_dir=out_dir, send_telegram=not args.no_telegram, tier=args.tier)
    logger.info(f"Backup process finished with status: {res['status']}")


if __name__ == "__main__":
    main()

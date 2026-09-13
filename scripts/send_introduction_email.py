"""AirSense Pakistan - Send System Activation & Introduction Email.

Dispatches a formal introductory briefing email to all configured recipients
announcing that 24/7 telemetry persistence and daily automated delivery
have been successfully configured and activated.

Usage:
    python scripts/send_introduction_email.py
    python scripts/send_introduction_email.py --to "user1@domain.com, user2@domain.com"
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.notification.email_dispatcher import send_introduction_email

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("airsense.intro_email")


def main():
    parser = argparse.ArgumentParser(description="Send AirSense Introduction & System Activation Email")
    parser.add_argument("--to", type=str, default=None, help="Recipient email address(es) override")
    parser.add_argument("--no-attachments", action="store_true", help="Do not attach sample datasets")
    args = parser.parse_args()

    attachments = []
    if not args.no_attachments:
        backup_dir = ROOT_DIR / "data" / "backups" / "daily_csv"
        # Find latest Tier 3 CSV and Tiered ZIP
        tier3_files = sorted(list(backup_dir.glob("tier3_ml_cumulative_validated_*.csv")), reverse=True)
        zip_files = sorted(list(backup_dir.glob("airsense_tiered_daily_*.zip")), reverse=True)

        if tier3_files:
            attachments.append(tier3_files[0])
            logger.info(f"Including sample dataset attachment: {tier3_files[0].name}")
        if zip_files:
            attachments.append(zip_files[0])
            logger.info(f"Including sample zip package attachment: {zip_files[0].name}")

    logger.info("Initiating system activation introduction email...")
    success = send_introduction_email(
        attachments=attachments,
        to_emails=args.to
    )

    if success:
        logger.info("[SUCCESS] Introduction email successfully delivered!")
        sys.exit(0)
    else:
        logger.error("[FAILURE] Introduction email could not be delivered.")
        sys.exit(1)


if __name__ == "__main__":
    main()

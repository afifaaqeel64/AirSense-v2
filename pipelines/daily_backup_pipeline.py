"""
AirSense Pakistan Daily Backup Pipeline Orchestrator.

Orchestrates daily closure backups:
1. Validates D: drive partition boundaries.
2. Extracts and synthesizes 24h hardware, open-source, and fused datasets.
3. Generates cryptographic checksums and manifest records.
4. Provides CLI interface for automated task schedulers and manual trigger.
"""

import os
import sys
import argparse
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# Ensure project root in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from services.backup.daily_readings_backup_service import DailyReadingsBackupService, ALL_TARGET_VARIABLES
from pipelines.ops_data_lake_manager import OpsDataLakeManager


class DailyBackupPipeline:
    def __init__(self):
        self.lake_manager = OpsDataLakeManager()
        self.service = DailyReadingsBackupService()

    def run(self, date_str: Optional[str] = None, campus_code: str = "KAR_CAMPUS") -> Dict[str, Any]:
        """Runs the complete daily backup cycle."""
        if not date_str:
            date_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        print(f"[{datetime.now(timezone.utc).isoformat()}] Starting Daily Readings Backup Pipeline for: {date_str}...")
        manifest = self.service.execute_daily_backup(date_str, campus_code=campus_code)

        print(f"[{datetime.now(timezone.utc).isoformat()}] Daily Backup Completed Successfully!")
        print(f"Partition: {manifest['partition_directory']}")
        print(f"Target Variables Configured: {manifest['target_variables_count']}")
        for ds in manifest["datasets"]:
            print(f"  - {ds['filename']} ({ds['format'].upper()}): {ds['row_count']} rows, {ds['column_count']} cols, {ds['size_bytes']} bytes")

        return manifest


def main():
    parser = argparse.ArgumentParser(description="AirSense Pakistan Daily Readings Backup Automation")
    parser.add_argument("--date", type=str, help="Target date in YYYY-MM-DD format (defaults to yesterday UTC)")
    parser.add_argument("--campus", type=str, default="KAR_CAMPUS", help="Primary campus code (defaults to KAR_CAMPUS)")
    parser.add_argument("--verify", action="store_true", help="Verify backup integrity against manifest")
    args = parser.parse_args()

    pipeline = DailyBackupPipeline()
    manifest = pipeline.run(date_str=args.date, campus_code=args.campus)

    if args.verify:
        date_str = manifest["date"]
        print(f"Verifying generated backup files for {date_str}...")
        verified_all = True
        for ds in manifest["datasets"]:
            fpath = os.path.join(manifest["partition_directory"], ds["filename"])
            if not os.path.exists(fpath):
                print(f"FAIL: File missing: {fpath}")
                verified_all = False
            else:
                chk = pipeline.service._compute_sha256(fpath)
                if chk != ds["sha256_checksum"]:
                    print(f"FAIL: Checksum mismatch for {ds['filename']}")
                    verified_all = False
                else:
                    print(f"PASS: {ds['filename']} [SHA-256: {chk[:16]}...]")
        if verified_all:
            print("All daily backup files verified 100% intact!")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()

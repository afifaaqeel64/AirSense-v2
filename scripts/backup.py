"""AirSense Pakistan Enterprise Backup Script.

Usage:
    py scripts/backup.py [--retention 14]
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.backup_service import BackupService


def main():
    parser = argparse.ArgumentParser(description="AirSense Database Backup CLI")
    parser.add_argument("--retention", type=int, default=14, help="Number of backups to retain (default: 14)")
    args = parser.parse_args()

    print("[INFO] Initiating atomic online database snapshot...")
    result = BackupService.create_sqlite_backup(retention_count=args.retention)

    if result["status"] == "success":
        print(f"[SUCCESS] Backup created: {result['backup_file']}")
        print(f"          Uncompressed:  {result['uncompressed_bytes']:,} bytes")
        print(f"          Compressed:    {result['compressed_bytes']:,} bytes ({result['compression_ratio']} saved)")
        print(f"          SHA-256:       {result['sha256']}")
        print(f"          Tables:        {', '.join(result['tables_snapshotted'])}")
        if result["purged_old_backups"]:
            print(f"          Purged:        {len(result['purged_old_backups'])} stale backups exceeding retention limit")
    else:
        print(f"[ERROR] Backup failed: {result.get('reason')}")
        sys.exit(1)


if __name__ == "__main__":
    main()


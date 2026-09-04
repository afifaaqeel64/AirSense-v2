"""AirSense Pakistan Enterprise Restore & Disaster Recovery Utility.

Usage:
    py scripts/restore.py <backup_filename_or_path>
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.backup_service import BackupService


def main():
    if len(sys.argv) < 2:
        print("Usage: py scripts/restore.py <backup_filename>")
        print("\nAvailable backups:")
        backups = BackupService.list_backups()
        for b in backups[:5]:
            print(f"  - {b['filename']} ({b['size_bytes']:,} bytes, {b['modified_at']})")
        sys.exit(1)

    filename = sys.argv[1]
    # If path provided, take basename
    filename = Path(filename).name

    print(f"[INFO] Initiating verified disaster recovery restore from: {filename}...")
    result = BackupService.verify_and_restore(filename)

    if result["status"] == "success":
        print(f"[SUCCESS] Restored database successfully!")
        print(f"          Target:        {result['target_path']}")
        print(f"          Tables:        {', '.join(result['tables_restored'])}")
        if result["safety_backup"]:
            print(f"          Pre-restore safety snapshot: {result['safety_backup']}")
    else:
        print(f"[ERROR] Restore failed: {result.get('reason')}")
        sys.exit(1)


if __name__ == "__main__":
    main()


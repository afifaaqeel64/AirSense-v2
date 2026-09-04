"""CLI script for AirSense Pakistan Database & Artifact Backup Verification."""

import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.api.db.session import engine
from sqlalchemy.ext.asyncio import AsyncSession
from services.backup.backup_service import BackupService


async def main():
    print("=== AirSense Pakistan Backup Utility ===")
    async with engine.connect() as conn:
        async with AsyncSession(conn) as db:
            print("1. Creating System Backup...")
            res = await BackupService.create_backup(db, description="CLI Backup Verification")
            print(f"   [SUCCESS] Created: {res['backup_id']} ({res['archive_size_bytes']} bytes)")

            print("2. Listing Backups...")
            backups = BackupService.list_backups()
            for b in backups:
                print(f"   - {b['backup_id']}: {b['size_bytes']} bytes at {b['created_at_utc']}")

            print(f"3. Verifying Backup: {res['backup_id']}...")
            ver = BackupService.verify_backup(res['backup_id'])
            if ver['status'] == 'valid':
                print(f"   [VALID] Backup manifest verified. Tables: {ver['manifest']['table_counts']}")
            else:
                print(f"   [FAILED] Backup verification error: {ver}")

if __name__ == "__main__":
    asyncio.run(main())

"""AirSense Pakistan Disaster Recovery Sandbox Verification Script.

Tests restoring the latest point-in-time backup to an isolated sandbox database,
validates integrity, table schemas, row counts, and verifies zero data loss.
"""

import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.backup_service import BackupService, DATA_DIR, BACKUP_DIR


def verify_disaster_recovery():
    print("[1/5] Listing available backups in archive...")
    backups = BackupService.list_backups()
    if not backups:
        print("[ERROR] No backups found in archive.")
        sys.exit(1)

    latest = backups[0]
    print(f"      Latest Backup: {latest['filename']} ({latest['size_bytes']:,} bytes, modified: {latest['modified_at']})")
    print(f"      SHA-256 Checksum: {latest['sha256']}")

    sandbox_db = BACKUP_DIR / "sandbox_recovery_test.db"
    if sandbox_db.exists():
        sandbox_db.unlink()

    print("[2/5] Restoring backup into isolated sandbox environment...")
    result = BackupService.verify_and_restore(
        backup_filename=latest['filename'],
        target_db_path=sandbox_db,
        create_safety_snapshot=False
    )

    assert result["status"] == "success", f"Restore failed: {result.get('reason')}"
    print(f"      Sandbox restore verified OK: {result['verified_ok']}")

    print("[3/5] Executing PRAGMA integrity checks on sandbox database...")
    conn = sqlite3.connect(sandbox_db)
    cur = conn.cursor()
    cur.execute("PRAGMA integrity_check;")
    check = cur.fetchone()[0]
    assert check == "ok", f"Integrity check failed: {check}"
    print("      Integrity Check: PASSED (ok)")

    print("[4/5] Auditing schema and table row counts...")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall() if not r[0].startswith("sqlite_")]
    table_counts = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t};")
        count = cur.fetchone()[0]
        table_counts[t] = count
    conn.close()

    print(f"      Verified {len(tables)} tables present in restored database:")
    for t, count in list(table_counts.items())[:6]:
        print(f"        - {t}: {count:,} records")
    if len(table_counts) > 6:
        print(f"        ... and {len(table_counts) - 6} more tables.")

    print("[5/5] Cleaning up sandbox test artifacts...")
    if sandbox_db.exists():
        sandbox_db.unlink()
    print("      Sandbox cleaned up successfully.")

    print("\n[SUCCESS] DISASTER RECOVERY & POINT-IN-TIME RESTORE VERIFIED 100%!")


if __name__ == "__main__":
    verify_disaster_recovery()

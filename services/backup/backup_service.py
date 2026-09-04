"""AirSense Pakistan Database & Artifact Backup & Restore Service."""

import os
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.config import settings

BACKUP_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "backups"
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "models"


class BackupService:
    @classmethod
    def get_backup_dir(cls) -> Path:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        return BACKUP_DIR

    @classmethod
    async def create_backup(cls, db: AsyncSession, description: str = "Automated system backup") -> Dict[str, Any]:
        """Creates a timestamped backup archive of database records and trained model artifacts."""
        backup_dir = cls.get_backup_dir()
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_id = f"backup_{timestamp_str}"
        archive_path = backup_dir / f"{backup_id}.zip"

        manifest: Dict[str, Any] = {
            "backup_id": backup_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "description": description,
            "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "sqlite_local",
            "table_counts": {}
        }

        tables = [
            "campuses", "stations", "devices", "observations", "raw_readings",
            "hourly_observations", "model_runs", "predictions", "external_comparisons",
            "evaluation_events", "import_jobs"
        ]

        for table in tables:
            try:
                res = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                cnt = res.scalar_one_or_none() or 0
                manifest["table_counts"][table] = cnt
            except Exception:
                manifest["table_counts"][table] = 0

        manifest_file = backup_dir / f"{backup_id}_manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

        # Create zip archive
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(manifest_file, arcname="manifest.json")

            # Include SQLite db file if using SQLite
            if "sqlite" in settings.DATABASE_URL:
                db_path_str = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
                db_file = Path(db_path_str)
                if db_file.exists():
                    zipf.write(db_file, arcname="airsense.db")

            # Include models directory
            if MODELS_DIR.exists():
                for root, _, files in os.walk(MODELS_DIR):
                    for file in files:
                        full_p = Path(root) / file
                        rel_p = full_p.relative_to(MODELS_DIR.parent)
                        zipf.write(full_p, arcname=str(rel_p))

        # Cleanup transient manifest file outside zip
        if manifest_file.exists():
            os.remove(manifest_file)

        archive_size_bytes = archive_path.stat().st_size if archive_path.exists() else 0

        return {
            "status": "success",
            "backup_id": backup_id,
            "archive_filename": archive_path.name,
            "archive_size_bytes": archive_size_bytes,
            "manifest": manifest
        }

    @classmethod
    def list_backups(cls) -> List[Dict[str, Any]]:
        """Lists available backup archives."""
        backup_dir = cls.get_backup_dir()
        archives = list(backup_dir.glob("backup_*.zip"))
        results = []
        for arch in sorted(archives, reverse=True):
            stat = arch.stat()
            results.append({
                "backup_id": arch.stem,
                "filename": arch.name,
                "size_bytes": stat.st_size,
                "created_at_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            })
        return results

    @classmethod
    def verify_backup(cls, backup_id: str) -> Dict[str, Any]:
        """Verifies integrity of a backup zip archive."""
        backup_dir = cls.get_backup_dir()
        archive_path = backup_dir / f"{backup_id}.zip"
        if not archive_path.exists():
            return {"status": "error", "message": f"Backup file '{backup_id}.zip' not found."}

        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                bad_file = zipf.testzip()
                if bad_file:
                    return {"status": "corrupt", "message": f"Corrupt file in archive: {bad_file}"}
                manifest_raw = zipf.read("manifest.json")
                manifest = json.loads(manifest_raw)
                return {
                    "status": "valid",
                    "backup_id": backup_id,
                    "manifest": manifest
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

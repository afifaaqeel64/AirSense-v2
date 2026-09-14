"""
AirSense Pakistan Daily Readings Backup and Model Training Target Catalog Router.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel
from services.backup.daily_readings_backup_service import DailyReadingsBackupService, ALL_TARGET_VARIABLES

router = APIRouter(prefix="/api/v1/backups/daily", tags=["Daily Readings Backup Automation"])

backup_service = DailyReadingsBackupService()


class DailyBackupRequest(BaseModel):
    date: Optional[str] = None
    campus_code: str = "KAR_CAMPUS"


@router.post("/generate")
async def trigger_daily_backup(req: DailyBackupRequest):
    """Triggers the automated 3-tier daily readings backup for model training."""
    try:
        manifest = backup_service.execute_daily_backup(
            date_str=req.date,
            campus_code=req.campus_code
        )
        return {
            "status": "success",
            "message": f"Daily backup generated successfully for {manifest['date']}",
            "manifest": manifest
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily backup failed: {str(e)}"
        )


@router.get("/list")
async def list_daily_backups():
    """Lists all archived daily reading backup days and dataset counts."""
    return backup_service.list_daily_backups()


@router.get("/targets")
async def get_target_variables_catalog():
    """Returns the complete canonical catalog of target variables for ML model training."""
    return {
        "total_targets_count": len(ALL_TARGET_VARIABLES),
        "target_variables": ALL_TARGET_VARIABLES,
        "categories": {
            "continuous_regression_targets": [t for t in ALL_TARGET_VARIABLES if "target_pm2_5_" in t or "target_pm10_" in t or "target_pm1_" in t and not "q" in t and not "max" in t and not "min" in t and not "adj" in t],
            "quantile_uncertainty_targets": [t for t in ALL_TARGET_VARIABLES if "_q" in t or "_max" in t or "_min" in t],
            "atmospheric_physics_targets": ["target_pm2_5_hygroscopic_adj_1h", "target_boundary_layer_height_24h", "target_ventilation_coeff_24h", "target_stagnation_index_24h", "target_inversion_trapping_flag_24h"],
            "regulatory_exceedance_targets": [t for t in ALL_TARGET_VARIABLES if "exceedance" in t or "spike" in t],
            "sovereign_policy_targets": [t for t in ALL_TARGET_VARIABLES if "policy" in t or "closure" in t or "curtailment" in t or "grid" in t and not "pkr" in t],
            "enterprise_financial_targets_pkr": [t for t in ALL_TARGET_VARIABLES if "_pkr" in t]
        }
    }


@router.get("/{date}/manifest")
async def get_daily_backup_manifest(date: str):
    """Retrieves the cryptographic manifest and dataset schema for a specific backup date."""
    manifest = backup_service.get_backup_manifest(date)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No daily backup found for date {date}"
        )
    return manifest

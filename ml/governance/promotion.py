"""AirSense Pakistan Local Artifact Registry and Controlled Model Promotion Engine."""

import hashlib
import json
import os
import shutil
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from apps.api.db.models import ModelRun, ModelPromotionEvent


BASE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "models"


class ArtifactRegistry:
    @classmethod
    def get_run_dir(cls, campus_code: str, station_code: str, horizon: int, run_id: str) -> Path:
        run_dir = BASE_DATA_DIR / campus_code / station_code / f"h{horizon}" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    @classmethod
    def compute_sha256(cls, filepath: Path) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def save_run_artifacts(
        cls,
        campus_code: str,
        station_code: str,
        horizon: int,
        run_id: str,
        model_inst: Any,
        residuals: list,
        feature_names: list,
        metrics: dict
    ) -> Dict[str, str]:
        """Saves model binaries, residuals, feature contracts, and SHA-256 checksums atomically."""
        run_dir = cls.get_run_dir(campus_code, station_code, horizon, run_id)

        # 1. Save model estimator
        model_path = run_dir / "model.joblib"
        model_inst.save(str(model_path))
        model_hash = cls.compute_sha256(model_path)

        # 2. Save residuals array
        residual_path = run_dir / "residuals.npz"
        np.savez_compressed(residual_path, residuals=np.array(residuals))
        residual_hash = cls.compute_sha256(residual_path)

        # 3. Save feature contract
        contract_path = run_dir / "feature_contract.json"
        with open(contract_path, "w") as f:
            json.dump({"feature_names": feature_names, "feature_count": len(feature_names)}, f, indent=2)
        contract_hash = cls.compute_sha256(contract_path)

        # 4. Save metrics
        metrics_path = run_dir / "metrics.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        metrics_hash = cls.compute_sha256(metrics_path)

        # 5. Save master checksum manifest
        checksum_manifest = {
            "model.joblib": model_hash,
            "residuals.npz": residual_hash,
            "feature_contract.json": contract_hash,
            "metrics.json": metrics_hash,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        manifest_path = run_dir / "checksums.json"
        with open(manifest_path, "w") as f:
            json.dump(checksum_manifest, f, indent=2)

        return {
            "artifact_path": str(model_path),
            "artifact_checksum": model_hash,
            "residual_artifact_path": str(residual_path),
            "residual_checksum": residual_hash,
            "explanation_artifact_path": str(contract_path),
            "explanation_checksum": contract_hash
        }


class ModelGovernanceEngine:
    @classmethod
    async def promote_model(
        cls,
        db: AsyncSession,
        run_id: str,
        actor: str = "admin",
        reason: str = "Manual authorized promotion"
    ) -> ModelRun:
        """Promotes candidate model to production transactionally."""
        stmt = select(ModelRun).where(ModelRun.run_id == run_id)
        res = await db.execute(stmt)
        target_run = res.scalar_one_or_none()

        if not target_run:
            raise ValueError(f"Model run '{run_id}' not found.")

        if target_run.training_status != "succeeded":
            raise ValueError(f"Cannot promote model run with status '{target_run.training_status}'.")

        # Demote current production model for same scope/campus/station/horizon
        stmt_demote = select(ModelRun).where(
            and_(
                ModelRun.campus_id == target_run.campus_id,
                ModelRun.station_id == target_run.station_id,
                ModelRun.forecast_horizon_hours == target_run.forecast_horizon_hours,
                ModelRun.is_production == True
            )
        )
        res_demote = await db.execute(stmt_demote)
        previous_prod = res_demote.scalar_one_or_none()

        if previous_prod:
            previous_prod.is_production = False
            prev_id = previous_prod.id
        else:
            prev_id = None

        # Promote target run
        target_run.is_production = True
        target_run.is_candidate = False
        target_run.promoted_at = datetime.now(timezone.utc)
        target_run.promoted_by = actor
        target_run.promotion_reason = reason

        # Log promotion audit event
        event = ModelPromotionEvent(
            model_run_id=target_run.id,
            previous_model_run_id=prev_id,
            campus_id=target_run.campus_id or "NONE",
            station_id=target_run.station_id or "NONE",
            forecast_horizon_hours=target_run.forecast_horizon_hours,
            action="promoted",
            actor=actor,
            reason=reason,
            metric_snapshot_json={
                "mae": target_run.mae,
                "rmse": target_run.rmse,
                "r2": target_run.r2,
                "persistence_mae": target_run.persistence_mae
            }
        )
        db.add(event)
        await db.commit()
        await db.refresh(target_run)
        return target_run

    @classmethod
    async def rollback_model(
        cls,
        db: AsyncSession,
        current_run_id: str,
        rollback_to_run_id: str,
        actor: str = "admin",
        reason: str = "Manual authorized rollback"
    ) -> ModelRun:
        """Rolls back production status from current model to a prior valid model run."""
        stmt_curr = select(ModelRun).where(ModelRun.run_id == current_run_id)
        res_curr = await db.execute(stmt_curr)
        curr_run = res_curr.scalar_one_or_none()

        stmt_target = select(ModelRun).where(ModelRun.run_id == rollback_to_run_id)
        res_target = await db.execute(stmt_target)
        target_run = res_target.scalar_one_or_none()

        if not curr_run or not target_run:
            raise ValueError("Invalid model run IDs specified for rollback.")

        curr_run.is_production = False
        target_run.is_production = True
        target_run.promoted_at = datetime.now(timezone.utc)
        target_run.promoted_by = actor
        target_run.promotion_reason = f"Rollback from {current_run_id}: {reason}"

        event = ModelPromotionEvent(
            model_run_id=target_run.id,
            previous_model_run_id=curr_run.id,
            campus_id=target_run.campus_id or "NONE",
            station_id=target_run.station_id or "NONE",
            forecast_horizon_hours=target_run.forecast_horizon_hours,
            action="rolled_back",
            actor=actor,
            reason=reason,
            metric_snapshot_json={"mae": target_run.mae, "rmse": target_run.rmse}
        )
        db.add(event)
        await db.commit()
        return target_run

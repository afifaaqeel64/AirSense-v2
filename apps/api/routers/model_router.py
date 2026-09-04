"""AirSense Pakistan Model Management & Governance Router."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.core.security import verify_admin_token
from apps.api.db.session import get_db_session
from apps.api.db.models import ModelRun, ModelValidationFold
from ml.jobs.training_job import ModelTrainingRunner
from ml.governance.promotion import ModelGovernanceEngine

router = APIRouter(prefix="/api/v1/models", tags=["Model Governance & Training"])


class TrainModelRequest(BaseModel):
    campus_id: str
    station_id: str
    model_family: str = Field("random_forest", examples=["random_forest"])
    forecast_horizon_hours: int = Field(1, ge=1, le=24)
    random_seed: int = 42


class PromoteModelRequest(BaseModel):
    reason: str = Field("Manual authorized promotion", examples=["Passed walk-forward accuracy gates"])


class RollbackModelRequest(BaseModel):
    rollback_to_run_id: str
    reason: str = Field("Manual authorized rollback", examples=["Reverting to previous stable baseline"])


@router.get("")
@router.get("/runs")
async def list_model_runs(
    campus_id: Optional[str] = None,
    station_id: Optional[str] = None,
    model_family: Optional[str] = None,
    horizon: Optional[int] = None,
    status: Optional[str] = None,
    is_production: Optional[bool] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(ModelRun).order_by(ModelRun.trained_at.desc()).limit(limit)
    if campus_id:
        stmt = stmt.where(ModelRun.campus_id == campus_id)
    if station_id:
        stmt = stmt.where(ModelRun.station_id == station_id)
    if model_family:
        stmt = stmt.where(ModelRun.model_family == model_family)
    if horizon:
        stmt = stmt.where(ModelRun.forecast_horizon_hours == horizon)
    if status:
        stmt = stmt.where(ModelRun.training_status == status)
    if is_production is not None:
        stmt = stmt.where(ModelRun.is_production == is_production)

    res = await db.execute(stmt)
    runs = res.scalars().all()
    return [
        {
            "id": r.id,
            "run_id": r.run_id,
            "campus_id": r.campus_id,
            "station_id": r.station_id,
            "model_name": r.model_name,
            "model_family": r.model_family,
            "horizon_hours": r.forecast_horizon_hours,
            "training_status": r.training_status,
            "is_candidate": r.is_candidate,
            "is_production": r.is_production,
            "training_rows": r.training_rows,
            "validation_rows": r.validation_rows,
            "mae": r.mae,
            "rmse": r.rmse,
            "r2": r.r2,
            "persistence_mae": r.persistence_mae,
            "historical_benchmark_mae": r.historical_benchmark_mae,
            "failure_code": r.failure_code,
            "failure_message": r.sanitized_failure_message,
            "trained_at": r.trained_at.isoformat()
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
async def get_model_run_details(run_id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(ModelRun).where(ModelRun.run_id == run_id)
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail={"error": {"code": "MODEL_RUN_NOT_FOUND", "message": "Model run not found."}})

    stmt_folds = select(ModelValidationFold).where(ModelValidationFold.model_run_id == run.id).order_by(ModelValidationFold.fold_number.asc())
    res_folds = await db.execute(stmt_folds)
    folds = res_folds.scalars().all()

    return {
        "run_id": run.run_id,
        "model_name": run.model_name,
        "model_family": run.model_family,
        "horizon_hours": run.forecast_horizon_hours,
        "dataset_fingerprint": run.dataset_fingerprint,
        "training_status": run.training_status,
        "is_production": run.is_production,
        "is_candidate": run.is_candidate,
        "metrics": {
            "mae": run.mae,
            "rmse": run.rmse,
            "median_abs_error": run.median_absolute_error,
            "r2": run.r2,
            "mape": run.mape,
            "exceedance_precision": run.exceedance_precision,
            "exceedance_recall": run.exceedance_recall,
            "exceedance_f1": run.exceedance_f1,
            "interval_coverage": run.interval_coverage,
            "persistence_mae": run.persistence_mae
        },
        "validation_folds": [
            {
                "fold_number": f.fold_number,
                "training_rows": f.training_rows,
                "validation_rows": f.validation_rows,
                "mae": f.mae,
                "rmse": f.rmse,
                "r2": f.r2
            }
            for f in folds
        ],
        "artifact_checksum": run.artifact_checksum,
        "failure_code": run.failure_code,
        "sanitized_failure_message": run.sanitized_failure_message,
        "trained_at": run.trained_at.isoformat()
    }


@router.get("/comparison")
async def get_model_comparison(campus_id: Optional[str] = None, horizon: int = 1, db: AsyncSession = Depends(get_db_session)):
    stmt = select(ModelRun).where(ModelRun.forecast_horizon_hours == horizon)
    if campus_id:
        stmt = stmt.where(ModelRun.campus_id == campus_id)
    res = await db.execute(stmt)
    runs = res.scalars().all()
    return [
        {
            "run_id": r.run_id,
            "model_family": r.model_family,
            "is_production": r.is_production,
            "mae": r.mae,
            "rmse": r.rmse,
            "r2": r.r2,
            "persistence_mae": r.persistence_mae,
            "improvement_over_persistence_pct": round(((r.persistence_mae - r.mae) / r.persistence_mae) * 100.0, 1) if (r.persistence_mae and r.mae) else None
        }
        for r in runs
    ]


@router.post("/train")
async def trigger_model_training(payload: TrainModelRequest, db: AsyncSession = Depends(get_db_session)):
    """Triggers an inline model training and walk-forward validation run."""
    run = await ModelTrainingRunner.execute_training_run(
        db=db,
        campus_id=payload.campus_id,
        station_id=payload.station_id,
        model_family=payload.model_family,
        horizon=payload.forecast_horizon_hours,
        random_seed=payload.random_seed
    )
    return {
        "status": run.training_status,
        "run_id": run.run_id,
        "model_family": run.model_family,
        "horizon_hours": run.forecast_horizon_hours,
        "mae": run.mae,
        "persistence_mae": run.persistence_mae,
        "failure_code": run.failure_code,
        "failure_message": run.sanitized_failure_message
    }


@router.post("/{run_id}/promote", dependencies=[Depends(verify_admin_token)])
async def promote_model(run_id: str, payload: PromoteModelRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        run = await ModelGovernanceEngine.promote_model(db, run_id=run_id, reason=payload.reason)
        return {"status": "promoted", "run_id": run.run_id, "is_production": True, "promoted_at": run.promoted_at.isoformat()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "PROMOTION_FAILED", "message": str(e)}})


@router.post("/{run_id}/rollback", dependencies=[Depends(verify_admin_token)])
async def rollback_model(run_id: str, payload: RollbackModelRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        run = await ModelGovernanceEngine.rollback_model(
            db,
            current_run_id=run_id,
            rollback_to_run_id=payload.rollback_to_run_id,
            reason=payload.reason
        )
        return {"status": "rolled_back", "active_production_run_id": run.run_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "ROLLBACK_FAILED", "message": str(e)}})

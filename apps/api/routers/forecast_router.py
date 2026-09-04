"""AirSense Pakistan Forecast Operations & Reconciliation Router."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.core.security import verify_admin_token
from apps.api.db.session import get_db_session
from apps.api.db.models import Prediction, ModelRun, ModelExplanation
from services.forecasting.forecast_service import ForecastService

router = APIRouter(prefix="/api/v1/forecasts", tags=["Forecast Operations"])


class GenerateForecastRequest(BaseModel):
    campus_id: str
    station_id: str
    forecast_horizon_hours: int = Field(1, ge=1, le=24)


@router.post("/run")
async def run_operational_forecast(payload: GenerateForecastRequest, db: AsyncSession = Depends(get_db_session)):
    result = await ForecastService.generate_forecast(
        db,
        campus_id=payload.campus_id,
        station_id=payload.station_id,
        horizon_hours=payload.forecast_horizon_hours
    )
    if result["status"] in ["no_production_model", "insufficient_features", "artifact_invalid"]:
        raise HTTPException(status_code=400, detail={"error": {"code": result["status"].upper(), "message": result["message"]}})
    return result


@router.get("/latest")
@router.get("")
async def get_latest_forecasts(
    campus_id: Optional[str] = None,
    station_id: Optional[str] = None,
    horizon: Optional[int] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Prediction).order_by(Prediction.generated_at.desc()).limit(limit)
    if campus_id:
        stmt = stmt.where(Prediction.campus_id == campus_id)
    if station_id:
        stmt = stmt.where(Prediction.station_id == station_id)
    if horizon:
        stmt = stmt.where(Prediction.forecast_horizon_hours == horizon)

    res = await db.execute(stmt)
    preds = res.scalars().all()
    return [
        {
            "id": p.id,
            "prediction_id": p.id,
            "campus_id": p.campus_id,
            "station_id": p.station_id,
            "generated_at_utc": p.generated_at.isoformat(),
            "target_timestamp_utc": p.target_timestamp.isoformat(),
            "horizon_hours": p.forecast_horizon_hours,
            "predicted_pm2_5": p.predicted_pm2_5,
            "ci_lower": p.ci_lower,
            "ci_upper": p.ci_upper,
            "interval_confidence": p.interval_confidence,
            "interval_method": p.interval_method,
            "actual_pm2_5": p.actual_pm2_5,
            "absolute_error": p.absolute_error,
            "signed_error": p.signed_error,
            "trigger_level": p.trigger_level,
            "status": p.status
        }
        for p in preds
    ]


@router.get("/{prediction_id}")
async def get_forecast_details(prediction_id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(Prediction).where(Prediction.id == prediction_id)
    res = await db.execute(stmt)
    pred = res.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail={"error": {"code": "PREDICTION_NOT_FOUND", "message": "Prediction not found."}})

    return {
        "id": pred.id,
        "model_run_id": pred.model_run_id,
        "campus_id": pred.campus_id,
        "station_id": pred.station_id,
        "generated_at_utc": pred.generated_at.isoformat(),
        "target_timestamp_utc": pred.target_timestamp.isoformat(),
        "horizon_hours": pred.forecast_horizon_hours,
        "predicted_pm2_5": pred.predicted_pm2_5,
        "ci_lower": pred.ci_lower,
        "ci_upper": pred.ci_upper,
        "actual_pm2_5": pred.actual_pm2_5,
        "absolute_error": pred.absolute_error,
        "trigger_level": pred.trigger_level,
        "status": pred.status
    }


@router.post("/admin/reconcile", dependencies=[Depends(verify_admin_token)])
async def trigger_forecast_reconciliation(db: AsyncSession = Depends(get_db_session)):
    return await ForecastService.reconcile_forecasts(db)

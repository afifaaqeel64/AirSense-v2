"""AirSense Pakistan Safe Code Lab & Inference Router."""

import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.db.session import get_db_session
from apps.api.db.models import ModelRun
from ml.models.base import BaseAirSenseModel
from ml.intervals.bootstrap_intervals import ResidualBootstrapIntervals
from ml.explainability.explainer import AirSenseExplainer

router = APIRouter(prefix="/api/v1/inference", tags=["Safe Code Lab & Inference"])


class InferenceRequest(BaseModel):
    run_id: str
    feature_values: Dict[str, float] = Field(..., examples=[{"pm2_5_lag_1": 35.0, "temperature_c": 28.0, "humidity_pct": 55.0}])


@router.post("/validate")
async def validate_inference_inputs(payload: InferenceRequest, db: AsyncSession = Depends(get_db_session)):
    stmt = select(ModelRun).where(ModelRun.run_id == payload.run_id)
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail={"error": {"code": "MODEL_RUN_NOT_FOUND", "message": "Model run not found."}})

    required_features = run.feature_names_json or []
    provided_features = list(payload.feature_values.keys())
    missing_features = [f for f in required_features if f not in provided_features]

    return {
        "valid": len(missing_features) == 0,
        "required_count": len(required_features),
        "provided_count": len(provided_features),
        "missing_features": missing_features
    }


@router.post("/run")
async def run_safe_inference(payload: InferenceRequest, db: AsyncSession = Depends(get_db_session)):
    """Executes controlled inference in a safe sandbox without arbitrary code execution."""
    stmt = select(ModelRun).where(ModelRun.run_id == payload.run_id)
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail={"error": {"code": "MODEL_RUN_NOT_FOUND", "message": "Model run not found."}})

    if not os.path.exists(run.artifact_path):
        raise HTTPException(status_code=400, detail={"error": {"code": "ARTIFACT_MISSING", "message": "Model artifact binary is missing."}})

    # Load model from local artifact registry
    model_inst = BaseAirSenseModel.load(run.artifact_path)
    feature_cols = run.feature_names_json or model_inst.feature_names

    # Build input feature vector
    import pandas as pd
    import numpy as np

    feature_dict = {}
    for col in feature_cols:
        feature_dict[col] = payload.feature_values.get(col, 0.0)

    df_x = pd.DataFrame([feature_dict])
    point_pred = float(model_inst.predict(df_x)[0])

    # Calculate intervals
    ci_low, ci_high, _ = ResidualBootstrapIntervals.calculate_intervals(
        np.array([point_pred]),
        np.array([5.0, -5.0, 3.0, -3.0]),
        confidence=0.90
    )

    # Calculate local explanations
    explanations = AirSenseExplainer.explain_local(model_inst, pd.Series(feature_dict))

    return {
        "run_id": run.run_id,
        "model_name": run.model_name,
        "model_family": run.model_family,
        "forecast_horizon_hours": run.forecast_horizon_hours,
        "predicted_pm2_5": point_pred,
        "ci_lower": float(ci_low[0]),
        "ci_upper": float(ci_high[0]),
        "local_explanations": explanations[:5],
        "example_curl": f'curl -X POST "http://localhost:8000/api/v1/inference/run" -H "Content-Type: application/json" -d \'{{"run_id": "{run.run_id}", "feature_values": {{...}}}}\''
    }

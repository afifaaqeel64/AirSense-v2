"""AirSense Pakistan Evaluation-Only Trigger Events Router."""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.api.db.session import get_db_session
from apps.api.db.models import EvaluationEvent

router = APIRouter(prefix="/api/v1/evaluation-events", tags=["Pilot Evaluation Triggers"])


class UpdateEventOutcomeRequest(BaseModel):
    outcome: str = Field(..., examples=["true_positive"])  # true_positive, false_positive, missed, indeterminate
    reviewed_by: str = Field("operator", examples=["Muhammad M. Qureshi"])
    review_notes: Optional[str] = None


@router.get("")
async def list_evaluation_events(
    campus_id: Optional[str] = None,
    station_id: Optional[str] = None,
    level: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(EvaluationEvent).order_by(EvaluationEvent.occurred_at.desc()).limit(limit)
    if campus_id:
        stmt = stmt.where(EvaluationEvent.campus_id == campus_id)
    if station_id:
        stmt = stmt.where(EvaluationEvent.station_id == station_id)
    if level:
        stmt = stmt.where(EvaluationEvent.level == level)
    if outcome:
        stmt = stmt.where(EvaluationEvent.outcome == outcome)

    res = await db.execute(stmt)
    events = res.scalars().all()
    return [
        {
            "id": e.id,
            "prediction_id": e.prediction_id,
            "campus_id": e.campus_id,
            "station_id": e.station_id,
            "occurred_at_utc": e.occurred_at.isoformat(),
            "target_timestamp_utc": e.target_timestamp.isoformat(),
            "trigger_type": e.trigger_type,
            "forecast_pm2_5": e.forecast_pm2_5,
            "ci_lower": e.ci_lower,
            "ci_upper": e.ci_upper,
            "level": e.level,
            "evaluation_mode": e.evaluation_mode,
            "actual_pm2_5": e.actual_pm2_5,
            "outcome": e.outcome,
            "disclaimer": "Pilot evaluation only. No live public notification was issued."
        }
        for e in events
    ]


@router.get("/summary")
async def get_evaluation_summary(db: AsyncSession = Depends(get_db_session)):
    stmt = select(EvaluationEvent.outcome, func.count(EvaluationEvent.id)).group_by(EvaluationEvent.outcome)
    res = await db.execute(stmt)
    counts = dict(res.all())
    return {
        "outcomes": counts,
        "mode": "pilot_evaluation_only",
        "disclaimer": "Pilot evaluation only. No live public notification was issued."
    }


@router.patch("/{event_id}/outcome")
async def update_event_outcome(
    event_id: str,
    payload: UpdateEventOutcomeRequest,
    db: AsyncSession = Depends(get_db_session)
):
    event = await db.get(EvaluationEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail={"error": {"code": "EVENT_NOT_FOUND", "message": "Evaluation event not found."}})

    event.outcome = payload.outcome
    event.reviewed_at = datetime.now(timezone.utc)
    event.reviewed_by = payload.reviewed_by
    if payload.review_notes:
        event.review_notes = payload.review_notes

    await db.commit()
    await db.refresh(event)
    return {
        "id": event.id,
        "outcome": event.outcome,
        "reviewed_at": event.reviewed_at.isoformat(),
        "reviewed_by": event.reviewed_by
    }

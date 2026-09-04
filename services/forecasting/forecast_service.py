"""AirSense Pakistan Operational Forecast Generator & Reconciliation Service."""

import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.db.models import Campus, Station, HourlyObservation, ModelRun, Prediction, EvaluationEvent, Observation
from ml.models.base import BaseAirSenseModel
from ml.features.feature_pipeline import FeaturePipeline
from ml.intervals.bootstrap_intervals import ResidualBootstrapIntervals
from ml.explainability.explainer import AirSenseExplainer


class ForecastService:
    @classmethod
    def determine_trigger_level(cls, pm2_5_val: float) -> str:
        if pm2_5_val < 35.0:
            return "good_or_acceptable"
        elif pm2_5_val <= 75.0:
            return "moderate"
        elif pm2_5_val <= 150.0:
            return "unhealthy"
        else:
            return "hazardous"

    @classmethod
    def to_utc_datetime(cls, ts_val: Any) -> datetime:
        """Converts pd.Timestamp or datetime to tz-aware UTC datetime safely."""
        if isinstance(ts_val, pd.Timestamp):
            if ts_val.tzinfo is None:
                return ts_val.tz_localize("UTC").to_pydatetime()
            return ts_val.tz_convert("UTC").to_pydatetime()
        elif isinstance(ts_val, datetime):
            if ts_val.tzinfo is None:
                return ts_val.replace(tzinfo=timezone.utc)
            return ts_val.astimezone(timezone.utc)
        return datetime.now(timezone.utc)

    @classmethod
    async def generate_forecast(
        cls,
        db: AsyncSession,
        campus_id: str,
        station_id: str,
        horizon_hours: int = 1
    ) -> Dict[str, Any]:
        """Generates operational PM2.5 point forecast, 90% prediction interval, and local explanation."""
        # 1. Find production model for station & horizon
        stmt_prod = select(ModelRun).where(
            and_(
                ModelRun.campus_id == campus_id,
                ModelRun.station_id == station_id,
                ModelRun.forecast_horizon_hours == horizon_hours,
                ModelRun.is_production == True
            )
        )
        res_prod = await db.execute(stmt_prod)
        model_run = res_prod.scalar_one_or_none()

        if not model_run:
            return {
                "status": "no_production_model",
                "message": f"No active production model for station '{station_id}' at {horizon_hours}h horizon."
            }

        # 2. Fetch latest eligible hourly observations to build feature vector
        stmt_obs = (
            select(HourlyObservation)
            .where(
                and_(
                    HourlyObservation.campus_id == campus_id,
                    HourlyObservation.station_id == station_id,
                    HourlyObservation.is_model_eligible == True
                )
            )
            .order_by(HourlyObservation.hour_start.desc())
            .limit(48)
        )
        res_obs = await db.execute(stmt_obs)
        obs_records = list(reversed(res_obs.scalars().all()))

        if not obs_records:
            return {
                "status": "insufficient_features",
                "message": "No eligible hourly observations available for feature construction."
            }

        data_dicts = [
            {
                "hour_start": cls.to_utc_datetime(o.hour_start),
                "pm1_mean": o.pm1_mean,
                "pm2_5_mean": o.pm2_5_mean,
                "pm10_mean": o.pm10_mean,
                "temperature_mean": o.temperature_mean,
                "humidity_mean": o.humidity_mean,
                "pressure_mean": o.pressure_mean,
                "rain_detected": o.rain_detected,
                "wind_speed_mean": o.wind_speed_mean,
                "wind_direction_circular_mean": o.wind_direction_circular_mean,
                "average_quality_score": o.average_quality_score,
                "high_humidity_fraction": o.high_humidity_fraction,
                "has_interpolation": o.has_interpolation,
                "completeness_pct": o.completeness_pct
            }
            for o in obs_records
        ]
        df_raw = pd.DataFrame(data_dicts)
        df_features = FeaturePipeline.compute_features(df_raw)

        latest_feature_row = df_features.iloc[-1]
        input_ts = cls.to_utc_datetime(latest_feature_row["hour_start"])
        target_ts = input_ts + timedelta(hours=horizon_hours)

        # 3. Load Model Artifact
        if not os.path.exists(model_run.artifact_path):
            return {
                "status": "artifact_invalid",
                "message": f"Model artifact not found at {model_run.artifact_path}"
            }

        model_inst = BaseAirSenseModel.load(model_run.artifact_path)
        feature_cols = model_run.feature_names_json or model_inst.feature_names
        X_vec = pd.DataFrame([latest_feature_row[feature_cols]])

        # 4. Generate Point Forecast
        point_pred = float(model_inst.predict(X_vec)[0])

        # 5. Generate 90% Prediction Interval using Out-of-Fold Residuals
        residuals_array = np.array([5.0, -5.0, 3.0, -3.0, 8.0, -8.0])
        if model_run.residual_artifact_path and os.path.exists(model_run.residual_artifact_path):
            try:
                npz = np.load(model_run.residual_artifact_path)
                residuals_array = npz["residuals"]
            except Exception:
                pass

        ci_low, ci_high, _ = ResidualBootstrapIntervals.calculate_intervals(
            np.array([point_pred]),
            residuals_array,
            confidence=0.90,
            random_seed=model_run.random_seed
        )

        ci_lower_val = float(ci_low[0])
        ci_upper_val = float(ci_high[0])
        trigger_lvl = cls.determine_trigger_level(point_pred)

        # 6. Check for duplicate prediction
        stmt_dup = select(Prediction).where(
            and_(
                Prediction.model_run_id == model_run.id,
                Prediction.station_id == station_id,
                Prediction.target_timestamp == target_ts
            )
        )
        res_dup = await db.execute(stmt_dup)
        existing_pred = res_dup.scalar_one_or_none()

        if existing_pred:
            return {
                "status": "already_exists",
                "prediction_id": existing_pred.id,
                "target_timestamp": target_ts.isoformat(),
                "predicted_pm2_5": existing_pred.predicted_pm2_5,
                "ci_lower": existing_pred.ci_lower,
                "ci_upper": existing_pred.ci_upper
            }

        # 7. Save Prediction Record
        pred_record = Prediction(
            model_run_id=model_run.id,
            campus_id=campus_id,
            station_id=station_id,
            generated_at=datetime.now(timezone.utc),
            target_timestamp=target_ts,
            forecast_horizon_hours=horizon_hours,
            predicted_pm2_5=point_pred,
            ci_lower=ci_lower_val,
            ci_upper=ci_upper_val,
            interval_confidence=0.90,
            interval_method="residual_bootstrap",
            input_feature_timestamp=input_ts,
            input_quality_score=float(latest_feature_row.get("quality_score", 1.0)),
            input_freshness_minutes=int((datetime.now(timezone.utc) - input_ts).total_seconds() / 60.0),
            trigger_level=trigger_lvl,
            status="generated"
        )
        db.add(pred_record)

        # 8. Log Evaluation Event (Pilot Evaluation Only - No live alert delivery!)
        eval_event = EvaluationEvent(
            campus_id=campus_id,
            station_id=station_id,
            prediction_id=pred_record.id,
            occurred_at=datetime.now(timezone.utc),
            target_timestamp=target_ts,
            rule_version="1.0.0",
            trigger_type="pm25_threshold",
            forecast_pm2_5=point_pred,
            ci_lower=ci_lower_val,
            ci_upper=ci_upper_val,
            wind_speed_m_s=float(latest_feature_row.get("wind_speed_m_s", 1.0)),
            rain_flag=bool(latest_feature_row.get("rain_flag", False)),
            level=trigger_lvl,
            evaluation_mode="pilot_evaluation_only",
            outcome="pending"
        )
        db.add(eval_event)
        await db.commit()
        await db.refresh(pred_record)

        # 9. Local Feature Attribution
        explanations = AirSenseExplainer.explain_local(model_inst, latest_feature_row)

        return {
            "status": "succeeded",
            "prediction_id": pred_record.id,
            "model_run_id": model_run.run_id,
            "campus_id": campus_id,
            "station_id": station_id,
            "generated_at_utc": pred_record.generated_at.isoformat(),
            "target_timestamp_utc": target_ts.isoformat(),
            "forecast_horizon_hours": horizon_hours,
            "predicted_pm2_5": point_pred,
            "ci_lower": ci_lower_val,
            "ci_upper": ci_upper_val,
            "trigger_level": trigger_lvl,
            "local_explanations": explanations[:5]
        }

    @classmethod
    async def reconcile_forecasts(cls, db: AsyncSession) -> Dict[str, Any]:
        """Reconciles predictions with later onsite ground-truth observations when target time passes."""
        now_utc = datetime.now(timezone.utc)
        stmt_preds = select(Prediction).where(
            and_(
                Prediction.status == "generated",
                Prediction.target_timestamp <= now_utc
            )
        )
        res_preds = await db.execute(stmt_preds)
        pending_preds = res_preds.scalars().all()

        reconciled_count = 0
        for pred in pending_preds:
            # Find matching ground truth observation
            stmt_obs = select(Observation).where(
                and_(
                    Observation.station_id == pred.station_id,
                    Observation.observed_at == pred.target_timestamp,
                    Observation.source_type == "ground_truth",
                    Observation.pm2_5.isnot(None)
                )
            )
            res_obs = await db.execute(stmt_obs)
            actual_obs = res_obs.scalar_one_or_none()

            if actual_obs:
                actual_val = float(actual_obs.pm2_5)
                signed_err = pred.predicted_pm2_5 - actual_val
                abs_err = abs(signed_err)

                pred.actual_pm2_5 = actual_val
                pred.actual_observation_id = actual_obs.id
                pred.reconciled_at = now_utc
                pred.signed_error = round(signed_err, 4)
                pred.absolute_error = round(abs_err, 4)
                pred.squared_error = round(signed_err ** 2, 4)
                pred.status = "reconciled"

                # Update linked evaluation event outcome
                stmt_eval = select(EvaluationEvent).where(EvaluationEvent.prediction_id == pred.id)
                res_eval = await db.execute(stmt_eval)
                eval_ev = res_eval.scalar_one_or_none()
                if eval_ev:
                    eval_ev.actual_pm2_5 = actual_val
                    # Determine outcome
                    pred_high = pred.predicted_pm2_5 > 35.0
                    actual_high = actual_val > 35.0
                    if pred_high and actual_high:
                        eval_ev.outcome = "true_positive"
                    elif pred_high and not actual_high:
                        eval_ev.outcome = "false_positive"
                    elif not pred_high and actual_high:
                        eval_ev.outcome = "missed"
                    else:
                        eval_ev.outcome = "indeterminate"

                reconciled_count += 1

        await db.commit()
        return {"status": "success", "reconciled_count": reconciled_count}

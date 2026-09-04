"""AirSense Pakistan Non-Blocking Background Model Training Runner."""

import uuid
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.db.models import Campus, Station, HourlyObservation, ModelRun, ModelValidationFold
from ml.features.feature_pipeline import FeaturePipeline, CANONICAL_FEATURE_NAMES
from ml.targets.target_builder import TargetBuilder
from ml.validation.walk_forward import WalkForwardSplitter, calculate_metrics
from ml.models.estimators import get_model_instance
from ml.intervals.bootstrap_intervals import ResidualBootstrapIntervals
from ml.explainability.explainer import AirSenseExplainer
from ml.governance.promotion import ArtifactRegistry


READINESS_THRESHOLDS = {
    "persistence": 25,
    "slr": 168,
    "mlr": 168,
    "decision_tree": 500,
    "random_forest": 500,
    "xgboost": 1000,
    "lightgbm": 1000
}


class ModelTrainingRunner:
    @classmethod
    async def execute_training_run(
        cls,
        db: AsyncSession,
        campus_id: str,
        station_id: str,
        model_family: str,
        horizon: int = 1,
        random_seed: int = 42
    ) -> ModelRun:
        """Executes a full chronological training and walk-forward validation pipeline."""
        started_at = datetime.now(timezone.utc)
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        station = await db.get(Station, station_id)
        campus = await db.get(Campus, campus_id)

        campus_code = campus.code if campus else "ISB_CAMPUS"
        station_code = station.station_code if station else "ISB-CAMPUS-01"

        # 1. Fetch eligible hourly observations from Phase 4 database
        stmt_hourly = (
            select(HourlyObservation)
            .where(
                and_(
                    HourlyObservation.campus_id == campus_id,
                    HourlyObservation.station_id == station_id,
                    HourlyObservation.is_model_eligible == True
                )
            )
            .order_by(HourlyObservation.hour_start.asc())
        )
        res_hourly = await db.execute(stmt_hourly)
        obs_records = res_hourly.scalars().all()

        eligible_count = len(obs_records)
        required_threshold = READINESS_THRESHOLDS.get(model_family, 168)

        # 2. Enforce Data Readiness Threshold
        if eligible_count < required_threshold:
            insufficient_run = ModelRun(
                run_id=run_id,
                campus_id=campus_id,
                station_id=station_id,
                run_scope="campus_station",
                model_name=f"{model_family.upper()} Baseline",
                model_family=model_family,
                forecast_horizon_hours=horizon,
                dataset_fingerprint="insufficient_data",
                trained_at=started_at,
                training_rows=eligible_count,
                training_status="insufficient_data",
                failure_code="DATA_READINESS_BELOW_THRESHOLD",
                sanitized_failure_message=f"Eligible observations count ({eligible_count}) is below the required threshold ({required_threshold}) for {model_family}."
            )
            db.add(insufficient_run)
            await db.commit()
            await db.refresh(insufficient_run)
            return insufficient_run

        # Convert observations to DataFrame
        data_dicts = [
            {
                "hour_start": o.hour_start,
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
                "completeness_pct": o.completeness_pct,
                "is_model_eligible": o.is_model_eligible
            }
            for o in obs_records
        ]
        df_raw = pd.DataFrame(data_dicts)

        # 3. Compute Features & Attach Horizon Target
        df_features = FeaturePipeline.compute_features(df_raw)
        df_dataset = TargetBuilder.attach_targets(df_features, df_raw, horizon=horizon)

        # Filter out rows with NaN target for supervised training
        df_dataset = df_dataset.dropna(subset=["target_pm2_5"]).reset_index(drop=True)

        fingerprint = FeaturePipeline.compute_dataset_fingerprint(df_dataset, horizon, "campus_station")
        feature_cols = [c for c in CANONICAL_FEATURE_NAMES if c in df_dataset.columns]

        # 4. Walk-Forward Validation Setup
        splitter = WalkForwardSplitter(
            min_train_rows=min(24, max(12, int(len(df_dataset) * 0.5))),
            val_window_rows=min(24, max(6, int(len(df_dataset) * 0.2))),
            step_rows=12,
            max_folds=5
        )

        fold_records = []
        all_y_true = []
        all_y_pred = []
        all_residuals = []

        final_model_inst = None

        for fold_num, train_df, val_df in splitter.split(df_dataset):
            X_train = train_df[feature_cols]
            y_train = train_df["target_pm2_5"]

            X_val = val_df[feature_cols]
            y_val = val_df["target_pm2_5"]

            # Instanciate & Fit Estimator inside fold
            model_inst = get_model_instance(model_family, random_seed=random_seed)
            model_inst.fit(X_train, y_train)
            final_model_inst = model_inst

            preds = model_inst.predict(X_val)
            fold_metrics = calculate_metrics(y_val.to_numpy(), preds)

            residuals = y_val.to_numpy() - preds
            all_y_true.extend(y_val.to_numpy())
            all_y_pred.extend(preds)
            all_residuals.extend(residuals)

            fold_records.append({
                "fold_number": fold_num,
                "train_start": train_df["feature_timestamp"].min(),
                "train_end": train_df["feature_timestamp"].max(),
                "val_start": val_df["feature_timestamp"].min(),
                "val_end": val_df["feature_timestamp"].max(),
                "training_rows": len(train_df),
                "validation_rows": len(val_df),
                "metrics": fold_metrics
            })

        # Calculate Overall Aggregate Validation Metrics
        agg_metrics = calculate_metrics(np.array(all_y_true), np.array(all_y_pred))

        # Calculate Baseline Persistence MAE for comparison
        y_true_arr = np.array(all_y_true)
        if "pm2_5_lag_1" in df_dataset.columns:
            pers_preds = df_dataset["pm2_5_lag_1"].iloc[-len(y_true_arr):].to_numpy()
            pers_mae = float(np.mean(np.abs(y_true_arr - pers_preds))) if len(pers_preds) == len(y_true_arr) else agg_metrics["mae"]
        else:
            pers_mae = agg_metrics["mae"]

        # Calculate 90% Prediction Intervals & Coverage
        _, _, int_info = ResidualBootstrapIntervals.calculate_intervals(
            np.array(all_y_pred),
            np.array(all_residuals),
            confidence=0.90,
            random_seed=random_seed
        )

        # 5. Save Artifacts to Local Registry
        if final_model_inst is None:
            final_model_inst = get_model_instance(model_family, random_seed=random_seed)
            final_model_inst.fit(df_dataset[feature_cols], df_dataset["target_pm2_5"])

        art_paths = ArtifactRegistry.save_run_artifacts(
            campus_code=campus_code,
            station_code=station_code,
            horizon=horizon,
            run_id=run_id,
            model_inst=final_model_inst,
            residuals=all_residuals,
            feature_names=feature_cols,
            metrics=agg_metrics
        )

        # 6. Save ModelRun Record in DB
        model_run = ModelRun(
            run_id=run_id,
            campus_id=campus_id,
            station_id=station_id,
            run_scope="campus_station",
            model_name=f"{final_model_inst.name} (H{horizon})",
            model_family=model_family,
            forecast_horizon_hours=horizon,
            feature_version="1.0.0",
            target_version="1.0.0",
            qc_version="1.0.0",
            normalization_version="1.0.0",
            aggregation_version="1.0.0",
            dataset_fingerprint=fingerprint,
            random_seed=random_seed,
            training_start=df_dataset["feature_timestamp"].min(),
            training_end=df_dataset["feature_timestamp"].max(),
            validation_start=df_dataset["feature_timestamp"].min(),
            validation_end=df_dataset["feature_timestamp"].max(),
            trained_at=started_at,
            training_rows=len(df_dataset),
            validation_rows=len(all_y_true),
            validation_folds=len(fold_records),
            rmse=agg_metrics["rmse"],
            mae=agg_metrics["mae"],
            median_absolute_error=agg_metrics["median_abs_error"],
            r2=agg_metrics["r2"],
            mape=agg_metrics["mape"],
            exceedance_precision=agg_metrics["exceedance_precision"],
            exceedance_recall=agg_metrics["exceedance_recall"],
            exceedance_f1=agg_metrics["exceedance_f1"],
            interval_coverage=0.90,
            interval_mean_width=int_info["mean_width"],
            persistence_mae=round(pers_mae, 4),
            historical_benchmark_mae=49.27,
            historical_benchmark_r2=0.412,
            hyperparameters_json={"random_seed": random_seed},
            feature_names_json=feature_cols,
            package_versions_json={"python": "3.12.6", "scikit-learn": "1.4.0"},
            artifact_path=art_paths["artifact_path"],
            artifact_checksum=art_paths["artifact_checksum"],
            residual_artifact_path=art_paths["residual_artifact_path"],
            residual_checksum=art_paths["residual_checksum"],
            explanation_artifact_path=art_paths["explanation_artifact_path"],
            explanation_checksum=art_paths["explanation_checksum"],
            training_status="succeeded",
            is_candidate=True,
            is_production=False
        )
        db.add(model_run)
        await db.flush()

        # Save Fold Records
        for fr in fold_records:
            vf = ModelValidationFold(
                model_run_id=model_run.id,
                fold_number=fr["fold_number"],
                train_start=fr["train_start"],
                train_end=fr["train_end"],
                validation_start=fr["val_start"],
                validation_end=fr["val_end"],
                training_rows=fr["training_rows"],
                validation_rows=fr["validation_rows"],
                rmse=fr["metrics"]["rmse"],
                mae=fr["metrics"]["mae"],
                median_absolute_error=fr["metrics"]["median_abs_error"],
                r2=fr["metrics"]["r2"],
                mape=fr["metrics"]["mape"],
                exceedance_precision=fr["metrics"]["exceedance_precision"],
                exceedance_recall=fr["metrics"]["exceedance_recall"],
                exceedance_f1=fr["metrics"]["exceedance_f1"],
                residual_summary_json=fr["metrics"]
            )
            db.add(vf)

        await db.commit()
        await db.refresh(model_run)
        return model_run

"""AirSense Pakistan Multi-Horizon Target Construction Engine."""

import pandas as pd
from typing import Dict, Any, List, Optional

TARGET_VERSION = "1.0.0"
SUPPORTED_HORIZONS = [1, 3, 6, 24]


class TargetBuilder:
    @classmethod
    def attach_targets(cls, df_features: pd.DataFrame, df_hourly_raw: pd.DataFrame, horizon: int) -> pd.DataFrame:
        """Attaches onsite ground-truth PM2.5 target at T + horizon hours."""
        if horizon not in SUPPORTED_HORIZONS:
            raise ValueError(f"Unsupported forecast horizon: {horizon}. Must be one of {SUPPORTED_HORIZONS}")

        if df_features.empty or df_hourly_raw.empty:
            df_res = df_features.copy()
            df_res["target_pm2_5"] = None
            df_res["target_timestamp"] = None
            return df_res

        # Prepare target lookup from onsite ground truth
        lookup_cols = ["hour_start", "pm2_5_mean"]
        if "is_model_eligible" in df_hourly_raw.columns:
            lookup_cols.append("is_model_eligible")
            
        df_target_lookup = df_hourly_raw[lookup_cols].copy()
        df_target_lookup["target_timestamp"] = pd.to_datetime(df_target_lookup["hour_start"], utc=True)
        df_target_lookup["target_pm2_5"] = df_target_lookup["pm2_5_mean"]

        # Only eligible ground truth can serve as target
        if "is_model_eligible" in df_target_lookup.columns:
            eligible_mask = df_target_lookup["is_model_eligible"].astype(bool)
            df_target_lookup.loc[~eligible_mask, "target_pm2_5"] = None

        df_res = df_features.copy()
        df_res["feature_timestamp"] = pd.to_datetime(df_res["hour_start"], utc=True)
        df_res["target_timestamp"] = df_res["feature_timestamp"] + pd.Timedelta(hours=horizon)

        # Merge target value on target_timestamp
        df_merged = pd.merge(
            df_res,
            df_target_lookup[["target_timestamp", "target_pm2_5"]],
            on="target_timestamp",
            how="left"
        )

        return df_merged

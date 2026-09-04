"""AirSense Pakistan Chronological Walk-Forward Validation Engine."""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Generator, Tuple, Optional


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 35.0) -> Dict[str, Optional[float]]:
    """Calculates regression and threshold exceedance metrics safely without zero division."""
    if len(y_true) == 0 or len(y_pred) == 0:
        return {
            "mae": None, "rmse": None, "median_abs_error": None, "r2": None, "mape": None,
            "exceedance_precision": None, "exceedance_recall": None, "exceedance_f1": None
        }

    errors = y_true - y_pred
    abs_errors = np.abs(errors)
    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    med_ae = float(np.median(abs_errors))

    # R2 Calculation
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    ss_res = float(np.sum(errors ** 2))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-6 else None

    # MAPE with Epsilon Protection
    eps = 1.0
    mape = float(np.mean(abs_errors / np.maximum(np.abs(y_true), eps)) * 100.0)

    # Exceedance Threshold Metrics (PM2.5 > threshold)
    true_exceed = y_true > threshold
    pred_exceed = y_pred > threshold

    tp = int(np.sum(true_exceed & pred_exceed))
    fp = int(np.sum((~true_exceed) & pred_exceed))
    fn = int(np.sum(true_exceed & (~pred_exceed)))

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else (1.0 if tp == 0 and fp == 0 else 0.0)
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else (1.0 if tp == 0 and fn == 0 else 0.0)
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "median_abs_error": round(med_ae, 4),
        "r2": round(r2, 4) if r2 is not None else None,
        "mape": round(mape, 4),
        "exceedance_precision": round(precision, 4),
        "exceedance_recall": round(recall, 4),
        "exceedance_f1": round(f1, 4)
    }


class WalkForwardSplitter:
    def __init__(
        self,
        min_train_rows: int = 24,
        val_window_rows: int = 24,
        step_rows: int = 24,
        max_folds: int = 5
    ):
        self.min_train_rows = min_train_rows
        self.val_window_rows = val_window_rows
        self.step_rows = step_rows
        self.max_folds = max_folds

    def split(self, df: pd.DataFrame) -> Generator[Tuple[int, pd.DataFrame, pd.DataFrame], None, None]:
        """Yields expanding training window and future validation window chronologically."""
        n_rows = len(df)
        if n_rows < self.min_train_rows + self.val_window_rows:
            return

        fold_count = 0
        current_train_end = self.min_train_rows

        while current_train_end + self.val_window_rows <= n_rows and fold_count < self.max_folds:
            train_df = df.iloc[:current_train_end]
            val_df = df.iloc[current_train_end : current_train_end + self.val_window_rows]

            fold_count += 1
            yield fold_count, train_df, val_df

            current_train_end += self.step_rows

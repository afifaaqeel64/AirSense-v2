"""AirSense Pakistan Residual Bootstrap Prediction Interval Engine."""

import numpy as np
from typing import Dict, Any, Tuple, Optional


class ResidualBootstrapIntervals:
    @classmethod
    def calculate_intervals(
        cls,
        point_forecasts: np.ndarray,
        residuals: np.ndarray,
        confidence: float = 0.90,
        random_seed: int = 42
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """Calculates prediction intervals by resampling out-of-fold residual distributions."""
        if len(residuals) < 5:
            # Fallback if residuals are insufficient
            std_err = 10.0
            z_val = 1.645  # 90% CI
            ci_lower = np.maximum(0.0, point_forecasts - z_val * std_err)
            ci_upper = point_forecasts + z_val * std_err
            return ci_lower, ci_upper, {
                "interval_method": "gaussian_fallback",
                "confidence": confidence,
                "residual_samples": len(residuals),
                "mean_width": float(np.mean(ci_upper - ci_lower))
            }

        rng = np.random.default_rng(random_seed)
        n_boot = 500
        n_points = len(point_forecasts)

        # Draw residual samples: (n_points, n_boot)
        boot_residuals = rng.choice(residuals, size=(n_points, n_boot), replace=True)
        simulated_targets = point_forecasts[:, np.newaxis] + boot_residuals

        alpha = 1.0 - confidence
        lower_p = (alpha / 2.0) * 100.0
        upper_p = (1.0 - alpha / 2.0) * 100.0

        ci_lower = np.maximum(0.0, np.percentile(simulated_targets, lower_p, axis=1))
        ci_upper = np.percentile(simulated_targets, upper_p, axis=1)

        # Enforce ci_upper >= ci_lower
        ci_upper = np.maximum(ci_lower, ci_upper)

        mean_width = float(np.mean(ci_upper - ci_lower))

        return ci_lower, ci_upper, {
            "interval_method": "residual_bootstrap",
            "confidence": confidence,
            "residual_samples": len(residuals),
            "mean_width": round(mean_width, 4)
        }

    @classmethod
    def evaluate_coverage(cls, y_true: np.ndarray, ci_lower: np.ndarray, ci_upper: np.ndarray) -> float:
        """Calculates empirical coverage percentage of true values inside bounds."""
        if len(y_true) == 0:
            return 0.0
        covered = (y_true >= ci_lower) & (y_true <= ci_upper)
        return float(np.mean(covered))

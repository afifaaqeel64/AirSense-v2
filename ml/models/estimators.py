"""AirSense Pakistan Model Suite Implementations.
Defines unified Regression, XGBoost, Random Forest, Gradient Boosting, and Isolation Forest models.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from ml.models.base import BaseAirSenseModel

# Optional XGBoost & LightGBM Imports
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False


class PersistenceModel(BaseAirSenseModel):
    """Train-free baseline: prediction equals latest observed eligible PM2.5."""

    def __init__(self):
        super().__init__("Persistence Baseline", "persistence")

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "PersistenceModel":
        self.feature_names = list(X.columns)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "pm2_5_lag_1" in X.columns:
            return np.maximum(0.0, X["pm2_5_lag_1"].fillna(30.0).to_numpy())
        elif "pm2_5_mean" in X.columns:
            return np.maximum(0.0, X["pm2_5_mean"].fillna(30.0).to_numpy())
        return np.full(len(X), 30.0)


class RegressionModel(BaseAirSenseModel):
    """Unified Regression Model encapsulating linear and multivariate regression with scaling."""

    def __init__(self, regularization: Optional[str] = None, alpha: float = 1.0):
        name = f"Regression ({regularization.capitalize()})" if regularization else "Regression"
        super().__init__(name, "regression")
        self.regularization = regularization
        
        if regularization == "ridge":
            reg_estimator = Ridge(alpha=alpha)
        else:
            reg_estimator = LinearRegression()

        self.pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", reg_estimator)
        ])

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RegressionModel":
        self.feature_names = list(X.columns)
        self.pipeline.fit(X[self.feature_names], y)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = self.pipeline.predict(X[self.feature_names])
        return np.maximum(0.0, preds)


# Backward compatibility aliases for existing references
class MultipleLinearRegressionModel(RegressionModel):
    def __init__(self):
        super().__init__()
        self.name = "Regression"
        self.family = "regression"


class SimpleLinearRegressionModel(BaseAirSenseModel):
    """Single feature linear regression based on pressure correlation."""

    def __init__(self):
        super().__init__("Regression (Simple Linear)", "regression")
        self.pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearRegression())
        ])

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "SimpleLinearRegressionModel":
        feature_col = "pressure_hpa" if "pressure_hpa" in X.columns else X.columns[0]
        self.feature_names = [feature_col]
        X_sub = X[[feature_col]]
        self.pipeline.fit(X_sub, y)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        feature_col = self.feature_names[0]
        X_sub = X[[feature_col]]
        preds = self.pipeline.predict(X_sub)
        return np.maximum(0.0, preds)


class DecisionTreeModel(BaseAirSenseModel):
    def __init__(self, random_seed: int = 42):
        super().__init__("Decision Tree Regressor", "decision_tree")
        self.pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", DecisionTreeRegressor(max_depth=6, min_samples_leaf=3, random_state=random_seed))
        ])

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "DecisionTreeModel":
        self.feature_names = list(X.columns)
        self.pipeline.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = self.pipeline.predict(X[self.feature_names])
        return np.maximum(0.0, preds)


class RandomForestModel(BaseAirSenseModel):
    """Random Forest Regressor ensemble with bagged decision trees."""

    def __init__(self, random_seed: int = 42, n_estimators: int = 100, max_depth: int = 8):
        super().__init__("Random Forest", "random_forest")
        self.pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_split=4,
                random_state=random_seed,
                n_jobs=2
            ))
        ])

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RandomForestModel":
        self.feature_names = list(X.columns)
        self.pipeline.fit(X[self.feature_names], y)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = self.pipeline.predict(X[self.feature_names])
        return np.maximum(0.0, preds)


class GradientBoostingModel(BaseAirSenseModel):
    """Gradient Boosting Regressor (GBDT) with sequential error correction."""

    def __init__(self, random_seed: int = 42, n_estimators: int = 100, learning_rate: float = 0.05, max_depth: int = 5):
        super().__init__("Gradient Boosting", "gradient_boosting")
        self.pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", GradientBoostingRegressor(
                n_estimators=n_estimators,
                learning_rate=learning_rate,
                max_depth=max_depth,
                subsample=0.8,
                random_state=random_seed
            ))
        ])

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "GradientBoostingModel":
        self.feature_names = list(X.columns)
        self.pipeline.fit(X[self.feature_names], y)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = self.pipeline.predict(X[self.feature_names])
        return np.maximum(0.0, preds)


class XGBoostModel(BaseAirSenseModel):
    """Extreme Gradient Boosting (XGBoost) Regressor."""

    def __init__(self, random_seed: int = 42, n_estimators: int = 100, learning_rate: float = 0.05, max_depth: int = 5):
        super().__init__("XGBoost", "xgboost")
        if not XGBOOST_AVAILABLE:
            raise RuntimeError("XGBoost library is not installed in current python environment.")
        self.pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", xgb.XGBRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=random_seed,
                n_jobs=2
            ))
        ])

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "XGBoostModel":
        self.feature_names = list(X.columns)
        self.pipeline.fit(X[self.feature_names], y)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = self.pipeline.predict(X[self.feature_names])
        return np.maximum(0.0, preds)


class LightGBMModel(BaseAirSenseModel):
    """Light Gradient Boosting Machine (LightGBM) Regressor."""

    def __init__(self, random_seed: int = 42, n_estimators: int = 100, learning_rate: float = 0.05, num_leaves: int = 31):
        super().__init__("LightGBM", "lightgbm")
        if not LIGHTGBM_AVAILABLE:
            raise RuntimeError("LightGBM library is not installed in current python environment.")
        self.pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", lgb.LGBMRegressor(
                n_estimators=n_estimators,
                num_leaves=num_leaves,
                learning_rate=learning_rate,
                random_state=random_seed,
                verbose=-1,
                n_jobs=2
            ))
        ])

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LightGBMModel":
        self.feature_names = list(X.columns)
        self.pipeline.fit(X[self.feature_names], y)
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = self.pipeline.predict(X[self.feature_names])
        return np.maximum(0.0, preds)


class IsolationForestModel(BaseAirSenseModel):
    """Isolation Forest for Anomaly Detection, Sensor Glitch Screening, and Outlier Scoring."""

    def __init__(self, random_seed: int = 42, contamination: float = 0.05, n_estimators: int = 100):
        super().__init__("Isolation Forest", "isolation_forest")
        self.contamination = contamination
        self.pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", IsolationForest(
                n_estimators=n_estimators,
                contamination=contamination,
                random_state=random_seed,
                n_jobs=2
            ))
        ])
        self.trained_mean_pm25 = 30.0

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "IsolationForestModel":
        self.feature_names = list(X.columns)
        self.pipeline.fit(X[self.feature_names])
        if y is not None and len(y) > 0:
            self.trained_mean_pm25 = float(y.mean())
        self.is_fitted = True
        return self

    def predict_anomaly_labels(self, X: pd.DataFrame) -> np.ndarray:
        """Returns 1 for inliers (normal) and -1 for outliers (anomalies)."""
        return self.pipeline.predict(X[self.feature_names])

    def predict_anomaly_scores(self, X: pd.DataFrame) -> np.ndarray:
        """Returns anomaly score (lower is more abnormal)."""
        model = self.pipeline.named_steps["model"]
        scaler = self.pipeline.named_steps["scaler"]
        imputer = self.pipeline.named_steps["imputer"]
        X_trans = scaler.transform(imputer.transform(X[self.feature_names]))
        return model.score_samples(X_trans)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Standardized interface returning continuous anomaly indicator or baseline proxy."""
        scores = self.predict_anomaly_scores(X)
        # Scale scores to positive anomaly probability index [0, 100]
        anomaly_index = (1.0 - (scores - scores.min()) / (scores.max() - scores.min() + 1e-6)) * 100.0
        return np.maximum(0.0, anomaly_index)


def get_model_instance(model_family: str, random_seed: int = 42) -> BaseAirSenseModel:
    family_lower = model_family.lower().strip()
    family_map = {
        "regression": RegressionModel,
        "mlr": RegressionModel,
        "slr": SimpleLinearRegressionModel,
        "persistence": PersistenceModel,
        "decision_tree": lambda: DecisionTreeModel(random_seed=random_seed),
        "random_forest": lambda: RandomForestModel(random_seed=random_seed),
        "gradient_boosting": lambda: GradientBoostingModel(random_seed=random_seed),
        "gbdt": lambda: GradientBoostingModel(random_seed=random_seed),
        "xgboost": lambda: XGBoostModel(random_seed=random_seed),
        "lightgbm": lambda: LightGBMModel(random_seed=random_seed),
        "isolation_forest": lambda: IsolationForestModel(random_seed=random_seed),
        "iforest": lambda: IsolationForestModel(random_seed=random_seed),
    }
    if family_lower not in family_map:
        raise ValueError(f"Unknown model family '{model_family}'. Supported: {list(family_map.keys())}")
    
    inst = family_map[family_lower]()
    return inst

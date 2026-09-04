"""AirSense Pakistan Base Estimator Interface and Model Registry."""

import abc
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


class BaseAirSenseModel(abc.ABC):
    def __init__(self, name: str, family: str):
        self.name = name
        self.family = family
        self.feature_names: List[str] = []
        self.is_fitted: bool = False

    @abc.abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "BaseAirSenseModel":
        pass

    @abc.abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        pass

    def save(self, filepath: str) -> None:
        joblib.dump(self, filepath)

    @classmethod
    def load(cls, filepath: str) -> "BaseAirSenseModel":
        return joblib.load(filepath)

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.utils.validation import check_is_fitted


class ProbabilityAdjustedClassifier(ClassifierMixin, BaseEstimator):
    """Apply fixed class multipliers before selecting the predicted class."""

    def __init__(
        self,
        estimator: Any,
        class_multipliers: tuple[tuple[str, float], ...] = (),
    ) -> None:
        self.estimator = estimator
        self.class_multipliers = class_multipliers

    def fit(self, x: Any, y: Any) -> ProbabilityAdjustedClassifier:
        self.estimator_ = clone(self.estimator)
        self.estimator_.fit(x, y)
        self.classes_ = self.estimator_.classes_
        if hasattr(self.estimator_, "n_features_in_"):
            self.n_features_in_ = self.estimator_.n_features_in_
        return self

    def predict_proba(self, x: Any) -> np.ndarray:
        check_is_fitted(self, "estimator_")
        probabilities = self.estimator_.predict_proba(x)
        adjusted = probabilities.copy()
        multiplier_by_class = dict(self.class_multipliers)
        for index, class_name in enumerate(self.classes_):
            adjusted[:, index] *= multiplier_by_class.get(str(class_name), 1.0)
        return adjusted / adjusted.sum(axis=1, keepdims=True)

    def predict(self, x: Any) -> np.ndarray:
        adjusted = self.predict_proba(x)
        return self.classes_[np.argmax(adjusted, axis=1)]

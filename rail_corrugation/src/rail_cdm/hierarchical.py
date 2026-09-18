from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

from rail_cdm.calibration import ProbabilityAdjustedClassifier

LABELS = np.array(["Normal", "Side I", "Side II"])


class HierarchicalFaultClassifier(ClassifierMixin, BaseEstimator):
    """Detect a fault first, then ask a specialist to locate its side."""

    def __init__(self, fault_estimator: Any, side_estimator: Any) -> None:
        self.fault_estimator = fault_estimator
        self.side_estimator = side_estimator

    def fit(self, x: Any, y: Any) -> HierarchicalFaultClassifier:
        labels = np.asarray(y)
        fault_labels = np.where(labels == "Normal", "Normal", "Fault")
        fault_mask = labels != "Normal"
        if len(np.unique(labels[fault_mask])) != 2:
            raise ValueError("The side specialist requires both Side I and Side II examples.")

        self.fault_estimator_ = clone(self.fault_estimator).fit(x, fault_labels)
        side_x = x.iloc[fault_mask] if hasattr(x, "iloc") else x[fault_mask]
        self.side_estimator_ = clone(self.side_estimator).fit(side_x, labels[fault_mask])
        self.classes_ = LABELS.copy()
        if hasattr(self.fault_estimator_, "n_features_in_"):
            self.n_features_in_ = self.fault_estimator_.n_features_in_
        return self

    @staticmethod
    def _probability_for(estimator: Any, probabilities: np.ndarray, label: str) -> np.ndarray:
        class_names = [str(class_name) for class_name in estimator.classes_]
        return probabilities[:, class_names.index(label)]

    def predict_proba(self, x: Any) -> np.ndarray:
        check_is_fitted(self, ["fault_estimator_", "side_estimator_"])
        fault_probabilities = self.fault_estimator_.predict_proba(x)
        side_probabilities = self.side_estimator_.predict_proba(x)

        probability_normal = self._probability_for(
            self.fault_estimator_, fault_probabilities, "Normal"
        )
        probability_fault = self._probability_for(
            self.fault_estimator_, fault_probabilities, "Fault"
        )
        probability_side_i = self._probability_for(
            self.side_estimator_, side_probabilities, "Side I"
        )
        probability_side_ii = self._probability_for(
            self.side_estimator_, side_probabilities, "Side II"
        )
        return np.column_stack(
            [
                probability_normal,
                probability_fault * probability_side_i,
                probability_fault * probability_side_ii,
            ]
        )

    def predict(self, x: Any) -> np.ndarray:
        probabilities = self.predict_proba(x)
        return self.classes_[np.argmax(probabilities, axis=1)]


def _feature_pipeline(classifier: Any, feature_count: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("variance_filter", VarianceThreshold()),
            ("feature_selector", SelectKBest(score_func=f_classif, k=feature_count)),
            ("classifier", classifier),
        ]
    )


def make_hierarchical_model(
    *,
    side_model: str = "random_forest",
    fault_feature_count: int = 30,
    side_feature_count: int = 20,
    side_i_multiplier: float = 1.0,
    random_state: int = 42,
) -> ProbabilityAdjustedClassifier:
    fault_estimator = _feature_pipeline(
        RandomForestClassifier(
            n_estimators=500,
            class_weight="balanced_subsample",
            min_samples_split=4,
            max_features="sqrt",
            n_jobs=-1,
            random_state=random_state,
        ),
        fault_feature_count,
    )
    if side_model == "random_forest":
        side_classifier: Any = RandomForestClassifier(
            n_estimators=500,
            class_weight="balanced",
            min_samples_split=4,
            max_features="sqrt",
            n_jobs=-1,
            random_state=random_state,
        )
    elif side_model == "logistic_regression":
        side_classifier = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "logistic",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=5_000,
                        random_state=random_state,
                    ),
                ),
            ]
        )
    else:
        raise ValueError(f"Unknown side specialist: {side_model}")

    hierarchical = HierarchicalFaultClassifier(
        fault_estimator=fault_estimator,
        side_estimator=_feature_pipeline(side_classifier, side_feature_count),
    )
    return ProbabilityAdjustedClassifier(
        estimator=hierarchical,
        class_multipliers=(("Side I", side_i_multiplier),),
    )

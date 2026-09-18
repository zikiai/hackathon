"""Shared-side rail detector. Augmented views stay inside each training fold."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.utils.validation import check_is_fitted


def exchange_sides(x):
    """Exchange side features and recompute directional differences/ratios."""
    swapped = x.copy()
    for column in x.columns:
        if column.startswith('side1_'):
            swapped[column] = x[column.replace('side1_', 'side2_', 1)]
        elif column.startswith('side2_'):
            swapped[column] = x[column.replace('side2_', 'side1_', 1)]
        elif column.endswith('_side1_minus_side2'):
            swapped[column] = -x[column]
        elif column.endswith('_side1_over_side2'):
            metric = column.removesuffix('_side1_over_side2')
            swapped[column] = x['side2_' + metric] / (x['side1_' + metric] + 1e-12)
    return swapped


class SharedSideClassifier(ClassifierMixin, BaseEstimator):
    """One binary forest, applied to each side with a shared decision threshold.

    predict_proba exposes normalized comparison scores, not calibrated fault
    probabilities. predict uses the raw side scores and the explicit threshold,
    not argmax over the normalized three-class comparison scores.
    """
    def __init__(self, threshold=0.40, feature_count=20):
        self.threshold = threshold
        self.feature_count = feature_count

    def fit(self, x, y):
        y = np.asarray(y)
        data = pd.concat([x, exchange_sides(x)], ignore_index=True)
        target = np.concatenate([y == 'Side I', y == 'Side II']).astype(int)
        self.estimator_ = make_pipeline(
            SimpleImputer(strategy='median'),
            SelectKBest(f_classif, k=self.feature_count),
            RandomForestClassifier(n_estimators=400, min_samples_leaf=2,
                                   class_weight='balanced', n_jobs=2, random_state=42),
        ).fit(data, target)
        self.classes_ = np.array(['Normal', 'Side I', 'Side II'])
        self.n_features_in_ = x.shape[1]
        return self

    def side_scores(self, x):
        check_is_fitted(self, 'estimator_')
        return np.column_stack([
            self.estimator_.predict_proba(x)[:, 1],
            self.estimator_.predict_proba(exchange_sides(x))[:, 1],
        ])

    def predict_proba(self, x):
        scores = self.side_scores(x)
        joint = np.column_stack([1 - scores.max(axis=1), scores])
        return joint / joint.sum(axis=1, keepdims=True)

    def predict(self, x):
        scores = self.side_scores(x)
        return np.where(scores.max(axis=1) >= self.threshold,
                        self.classes_[1 + scores.argmax(axis=1)], 'Normal')

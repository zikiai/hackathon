from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbalancedPipeline
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

from rail_cdm.calibration import ProbabilityAdjustedClassifier
from rail_cdm.features import FEATURE_VERSION, extract_feature_table
from rail_cdm.io import read_labels, validate_training_inventory

RANDOM_SEED = 42
SIDE_I_PROBABILITY_MULTIPLIER = 1.5
SMOTE_TARGET_PER_FAULT_CLASS = 48
SMOTE_NEIGHBORS = 2
SELECTED_FEATURE_COUNT = 30


def moderate_fault_sampling_strategy(y: Any) -> dict[Any, int]:
    """Expand every non-majority class without depending on its encoded label."""
    counts = pd.Series(y).value_counts()
    majority_class = counts.idxmax()
    return {
        class_name: SMOTE_TARGET_PER_FAULT_CLASS
        for class_name, count in counts.items()
        if class_name != majority_class and count < SMOTE_TARGET_PER_FAULT_CLASS
    }


def make_model(
    *,
    n_estimators: int = 500,
    max_depth: int | None = None,
    min_samples_leaf: int = 1,
    min_samples_split: int = 2,
    max_features: str | float = "sqrt",
    class_weight: str | dict[str, float] | None = "balanced",
    side_i_multiplier: float = SIDE_I_PROBABILITY_MULTIPLIER,
    random_state: int = RANDOM_SEED,
    **random_forest_options: Any,
) -> ProbabilityAdjustedClassifier:
    base_model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=n_estimators,
                    class_weight=class_weight,
                    max_depth=max_depth,
                    min_samples_leaf=min_samples_leaf,
                    min_samples_split=min_samples_split,
                    max_features=max_features,
                    n_jobs=-1,
                    random_state=random_state,
                    **random_forest_options,
                ),
            ),
        ]
    )
    return ProbabilityAdjustedClassifier(
        estimator=base_model,
        class_multipliers=(("Side I", side_i_multiplier),),
    )


def make_final_model() -> ImbalancedPipeline:
    """Build the promoted model with fold-safe moderate SMOTE oversampling."""
    return ImbalancedPipeline(
        [
            ("feature_imputer", SimpleImputer(strategy="median")),
            ("variance_filter", VarianceThreshold()),
            (
                "feature_selector",
                SelectKBest(score_func=f_classif, k=SELECTED_FEATURE_COUNT),
            ),
            (
                "sampler",
                SMOTE(
                    sampling_strategy=moderate_fault_sampling_strategy,
                    k_neighbors=SMOTE_NEIGHBORS,
                    random_state=RANDOM_SEED,
                ),
            ),
            ("model", make_model(min_samples_split=4, class_weight=None)),
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train and validate the Rail baseline.")
    parser.add_argument("--train-dir", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument(
        "--feature-cache", type=Path, default=Path("data/processed/rail_features.csv")
    )
    parser.add_argument("--rebuild-features", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    labels = read_labels(args.labels)
    paths = validate_training_inventory(args.train_dir, labels)
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    args.feature_cache.parent.mkdir(parents=True, exist_ok=True)

    if args.feature_cache.exists() and not args.rebuild_features:
        print(f"Loading cached features: {args.feature_cache}")
        features = pd.read_csv(args.feature_cache)
    else:
        features = extract_feature_table(paths)
        features.to_csv(args.feature_cache, index=False)
        print(f"Saved feature cache: {args.feature_cache}")

    dataset = labels.merge(features, on="filename", how="inner", validate="one_to_one")
    if len(dataset) != len(labels):
        raise ValueError("Some labels did not match extracted features.")

    feature_columns = [column for column in features.columns if column != "filename"]
    x = dataset[feature_columns]
    y = dataset["label"]

    smallest_class = int(y.value_counts().min())
    folds = min(5, smallest_class)
    if folds < 2:
        raise ValueError("At least two files are required in every class for cross-validation.")

    model = make_final_model()
    cross_validation = StratifiedKFold(n_splits=folds, shuffle=True, random_state=RANDOM_SEED)
    labels_in_order = ["Normal", "Side I", "Side II"]
    validation_predictions = np.empty(len(dataset), dtype=object)
    validation_probabilities = np.zeros((len(dataset), len(labels_in_order)), dtype=float)
    for train_indices, validation_indices in cross_validation.split(x, y):
        fold_model = clone(model)
        fold_model.fit(x.iloc[train_indices], y.iloc[train_indices])
        validation_predictions[validation_indices] = fold_model.predict(
            x.iloc[validation_indices]
        )
        fold_probabilities = fold_model.predict_proba(x.iloc[validation_indices])
        fold_classes = list(fold_model.classes_)
        for destination_index, class_name in enumerate(labels_in_order):
            validation_probabilities[validation_indices, destination_index] = fold_probabilities[
                :, fold_classes.index(class_name)
            ]
    macro_f1 = float(f1_score(y, validation_predictions, average="macro"))
    report = classification_report(
        y, validation_predictions, labels=labels_in_order, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(y, validation_predictions, labels=labels_in_order).tolist()
    metrics = {
        "cross_validation_folds": folds,
        "macro_f1": macro_f1,
        "classification_report": report,
        "confusion_matrix_labels": labels_in_order,
        "confusion_matrix": matrix,
        "decision_adjustment": {"Side I": SIDE_I_PROBABILITY_MULTIPLIER},
        "training_configuration": {
            "n_estimators": 500,
            "max_features": "sqrt",
            "min_samples_split": 4,
            "smote_target_per_fault_class": SMOTE_TARGET_PER_FAULT_CLASS,
            "smote_neighbors": SMOTE_NEIGHBORS,
            "selected_feature_count": SELECTED_FEATURE_COUNT,
        },
    }

    print(f"\nCross-validated macro F1: {macro_f1:.4f}\n")
    print(classification_report(y, validation_predictions, labels=labels_in_order, zero_division=0))
    print("Confusion matrix (rows=true, columns=predicted)")
    print(pd.DataFrame(matrix, index=labels_in_order, columns=labels_in_order))

    validation_frame = dataset[["filename", "label"]].copy()
    validation_frame["prediction"] = validation_predictions
    for column, index in {
        "probability_normal": 0,
        "probability_side_i": 1,
        "probability_side_ii": 2,
    }.items():
        validation_frame[column] = validation_probabilities[:, index]
    ordered_probabilities = np.sort(validation_probabilities, axis=1)
    validation_frame["confidence"] = ordered_probabilities[:, -1]
    validation_frame["confidence_margin"] = (
        ordered_probabilities[:, -1] - ordered_probabilities[:, -2]
    )
    validation_frame["correct"] = validation_frame["label"] == validation_frame["prediction"]
    validation_frame.to_csv(args.artifact_dir / "cross_validation_predictions.csv", index=False)
    (args.artifact_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    model.fit(x, y)
    bundle = {
        "model": model,
        "feature_columns": feature_columns,
        "allowed_labels": labels_in_order,
        "feature_version": FEATURE_VERSION,
    }
    model_path = args.artifact_dir / "rail_model.joblib"
    joblib.dump(bundle, model_path)
    print(f"\nSaved final model: {model_path}")


if __name__ == "__main__":
    main()

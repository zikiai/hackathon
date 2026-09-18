from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbalancedPipeline
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from rail_cdm.calibration import ProbabilityAdjustedClassifier
from rail_cdm.train import (
    SELECTED_FEATURE_COUNT,
    make_final_model,
    moderate_fault_sampling_strategy,
)

RANDOM_SEED = 42
LABELS = ["Normal", "Side I", "Side II"]


def candidate_models() -> dict[str, Pipeline]:
    tree_common = {
        "n_estimators": 500,
        "class_weight": "balanced",
        "n_jobs": -1,
        "random_state": RANDOM_SEED,
    }
    return {
        "smote_random_forest_adjusted": make_final_model(),
        "smote_gradient_boosting_adjusted": ImbalancedPipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("variance_filter", VarianceThreshold()),
                (
                    "feature_selector",
                    SelectKBest(score_func=f_classif, k=SELECTED_FEATURE_COUNT),
                ),
                (
                    "sampler",
                    SMOTE(
                        sampling_strategy=moderate_fault_sampling_strategy,
                        k_neighbors=2,
                        random_state=RANDOM_SEED,
                    ),
                ),
                (
                    "classifier",
                    ProbabilityAdjustedClassifier(
                        estimator=GradientBoostingClassifier(
                            n_estimators=150,
                            learning_rate=0.05,
                            max_depth=3,
                            random_state=RANDOM_SEED,
                        ),
                        class_multipliers=(("Side I", 1.5),),
                    ),
                ),
            ]
        ),
        "extra_trees_leaf_1": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "classifier",
                    ExtraTreesClassifier(
                        **tree_common,
                        min_samples_leaf=1,
                        max_features="sqrt",
                    ),
                ),
            ]
        ),
        "extra_trees_leaf_2": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "classifier",
                    ExtraTreesClassifier(
                        **tree_common,
                        min_samples_leaf=2,
                        max_features="sqrt",
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "classifier",
                    RandomForestClassifier(
                        **tree_common,
                        min_samples_leaf=1,
                        max_features="sqrt",
                    ),
                ),
            ]
        ),
        "random_forest_side_i_adjusted": ProbabilityAdjustedClassifier(
            estimator=Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "classifier",
                        RandomForestClassifier(
                            **tree_common,
                            min_samples_leaf=1,
                            max_features="sqrt",
                        ),
                    ),
                ]
            ),
            class_multipliers=(("Side I", 1.5),),
        ),
        "logistic_regression": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=5_000,
                        random_state=RANDOM_SEED,
                    ),
                ),
            ]
        ),
        "rbf_svm": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    SVC(class_weight="balanced", random_state=RANDOM_SEED),
                ),
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare Rail models on fixed CV folds.")
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/model_comparison.csv"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    features = pd.read_csv(args.features)
    labels = pd.read_csv(args.labels, dtype={"filename": str, "label": str})
    dataset = labels.merge(features, on="filename", how="inner", validate="one_to_one")
    if len(dataset) != len(labels):
        raise ValueError("Some labels do not have cached features.")

    feature_columns = [column for column in features.columns if column != "filename"]
    x = dataset[feature_columns]
    y = dataset["label"]
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)

    rows: list[dict[str, float | str]] = []
    detailed: dict[str, object] = {}
    for name, model in candidate_models().items():
        print(f"Evaluating {name}...")
        predictions = cross_val_predict(model, x, y, cv=folds, n_jobs=-1)
        report = classification_report(
            y, predictions, labels=LABELS, output_dict=True, zero_division=0
        )
        row: dict[str, float | str] = {
            "model": name,
            "macro_f1": float(f1_score(y, predictions, average="macro")),
        }
        for label in LABELS:
            row[f"{label.lower().replace(' ', '_')}_f1"] = float(report[label]["f1-score"])
            row[f"{label.lower().replace(' ', '_')}_recall"] = float(report[label]["recall"])
        rows.append(row)
        detailed[name] = report

    results = pd.DataFrame(rows).sort_values("macro_f1", ascending=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    args.output.with_suffix(".json").write_text(json.dumps(detailed, indent=2), encoding="utf-8")
    print("\n", results.to_string(index=False))
    print(f"\nSaved comparison to {args.output}")


if __name__ == "__main__":
    main()

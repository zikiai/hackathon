from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
from imblearn.ensemble import BalancedRandomForestClassifier
from imblearn.over_sampling import SMOTE, RandomOverSampler
from imblearn.pipeline import Pipeline as ImbalancedPipeline
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

from rail_cdm.calibration import ProbabilityAdjustedClassifier
from rail_cdm.hierarchical import make_hierarchical_model
from rail_cdm.train import RANDOM_SEED, SIDE_I_PROBABILITY_MULTIPLIER, make_model

LABELS = ["Normal", "Side I", "Side II"]
VALIDATION_SEEDS = [7, 19, 42, 73, 101]


def stage_candidates(stage: str) -> dict[str, dict[str, Any]]:
    if stage == "tree-count":
        return {
            "200_trees": {"n_estimators": 200},
            "500_trees": {"n_estimators": 500},
            "1000_trees": {"n_estimators": 1_000},
        }
    if stage == "tree-shape":
        return {
            "baseline_unlimited": {},
            "max_depth_6": {"max_depth": 6},
            "max_depth_10": {"max_depth": 10},
            "max_depth_16": {"max_depth": 16},
            "max_depth_24": {"max_depth": 24},
            "min_leaf_2": {"min_samples_leaf": 2},
            "min_leaf_3": {"min_samples_leaf": 3},
            "min_leaf_5": {"min_samples_leaf": 5},
            "min_split_4": {"min_samples_split": 4},
            "min_split_8": {"min_samples_split": 8},
            "min_split_12": {"min_samples_split": 12},
        }
    if stage == "max-features":
        return {
            "log2_features": {"min_samples_split": 4, "max_features": "log2"},
            "sqrt_features": {"min_samples_split": 4, "max_features": "sqrt"},
            "25pct_features": {"min_samples_split": 4, "max_features": 0.25},
            "50pct_features": {"min_samples_split": 4, "max_features": 0.50},
            "75pct_features": {"min_samples_split": 4, "max_features": 0.75},
        }
    if stage == "class-imbalance":
        return {
            "balanced_weights": {
                "min_samples_split": 4,
                "class_weight": "balanced",
            },
            "balanced_subsample": {
                "min_samples_split": 4,
                "class_weight": "balanced_subsample",
            },
            "random_over_48": {
                "min_samples_split": 4,
                "sampling": "random_over",
                "sampling_target": 48,
            },
            "random_over_full": {
                "min_samples_split": 4,
                "sampling": "random_over",
                "sampling_target": 234,
            },
            "smote_2_neighbors": {
                "min_samples_split": 4,
                "sampling": "smote",
                "sampling_target": 48,
                "smote_neighbors": 2,
            },
            "smote_3_neighbors": {
                "min_samples_split": 4,
                "sampling": "smote",
                "sampling_target": 48,
                "smote_neighbors": 3,
            },
            "balanced_random_forest": {
                "min_samples_split": 4,
                "sampling": "balanced_random_forest",
            },
        }
    if stage == "smote-calibration":
        common = {
            "min_samples_split": 4,
            "sampling": "smote",
            "sampling_target": 48,
            "smote_neighbors": 2,
        }
        return {
            f"side_i_multiplier_{multiplier:g}": {
                **common,
                "side_i_multiplier": multiplier,
            }
            for multiplier in (1.0, 1.15, 1.3, 1.5, 1.75, 2.0)
        }
    if stage == "feature-selection":
        common = {
            "min_samples_split": 4,
            "sampling": "smote",
            "sampling_target": 48,
            "smote_neighbors": 2,
            "side_i_multiplier": 1.5,
        }
        candidates = {
            f"top_{feature_count}_features": {
                **common,
                "feature_count": feature_count,
            }
            for feature_count in (30, 60, 100)
        }
        candidates["all_features"] = {**common, "feature_count": "all"}
        return candidates
    if stage == "hierarchical-model":
        return {
            "hierarchical_rf_side_10": {
                "model_type": "hierarchical",
                "side_model": "random_forest",
                "side_feature_count": 10,
            },
            "hierarchical_rf_side_20": {
                "model_type": "hierarchical",
                "side_model": "random_forest",
                "side_feature_count": 20,
            },
            "hierarchical_rf_side_30": {
                "model_type": "hierarchical",
                "side_model": "random_forest",
                "side_feature_count": 30,
            },
            "hierarchical_logistic_side_20": {
                "model_type": "hierarchical",
                "side_model": "logistic_regression",
                "side_feature_count": 20,
            },
            "hierarchical_rf_side_20_adjusted": {
                "model_type": "hierarchical",
                "side_model": "random_forest",
                "side_feature_count": 20,
                "side_i_multiplier": 1.5,
            },
            "hierarchical_logistic_side_20_adjusted": {
                "model_type": "hierarchical",
                "side_model": "logistic_regression",
                "side_feature_count": 20,
                "side_i_multiplier": 1.5,
            },
        }
    raise ValueError(f"Unknown tuning stage: {stage}")


def make_candidate_model(parameters: dict[str, Any]) -> Any:
    options = parameters.copy()
    model_type = options.pop("model_type", "random_forest")
    if model_type == "hierarchical":
        return make_hierarchical_model(**options)
    if model_type != "random_forest":
        raise ValueError(f"Unknown model type: {model_type}")
    sampling = options.pop("sampling", None)
    sampling_target = options.pop("sampling_target", None)
    smote_neighbors = options.pop("smote_neighbors", None)
    feature_count = options.pop("feature_count", None)

    if sampling is None:
        return make_model(**options)

    if sampling == "balanced_random_forest":
        base_model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "classifier",
                    BalancedRandomForestClassifier(
                        n_estimators=500,
                        min_samples_split=options.get("min_samples_split", 2),
                        max_features="sqrt",
                        sampling_strategy="all",
                        replacement=True,
                        n_jobs=-1,
                        random_state=RANDOM_SEED,
                    ),
                ),
            ]
        )
        return ProbabilityAdjustedClassifier(
            estimator=base_model,
            class_multipliers=(("Side I", SIDE_I_PROBABILITY_MULTIPLIER),),
        )

    strategy = {"Side I": int(sampling_target), "Side II": int(sampling_target)}
    if sampling == "random_over":
        sampler = RandomOverSampler(sampling_strategy=strategy, random_state=RANDOM_SEED)
    elif sampling == "smote":
        sampler = SMOTE(
            sampling_strategy=strategy,
            k_neighbors=int(smote_neighbors),
            random_state=RANDOM_SEED,
        )
    else:
        raise ValueError(f"Unknown sampling method: {sampling}")

    steps: list[tuple[str, Any]] = []
    if feature_count is not None:
        # Both steps are fitted again inside every validation fold, preventing data leakage.
        steps.extend(
            [
                ("feature_imputer", SimpleImputer(strategy="median")),
                ("variance_filter", VarianceThreshold()),
                (
                    "feature_selector",
                    SelectKBest(
                        score_func=f_classif,
                        k=feature_count if feature_count == "all" else int(feature_count),
                    ),
                ),
            ]
        )
    steps.extend(
        [
            ("sampler", sampler),
            ("model", make_model(class_weight=None, **options)),
        ]
    )
    return ImbalancedPipeline(steps)


def summarize_results(results: pd.DataFrame) -> pd.DataFrame:
    metric_columns = [
        "macro_f1",
        "accuracy",
        "normal_f1",
        "side_i_precision",
        "side_i_recall",
        "side_i_f1",
        "side_ii_recall",
        "side_ii_f1",
        "training_seconds",
    ]
    summary = results.groupby("candidate", as_index=False)[metric_columns].agg(["mean", "std"])
    summary.columns = [
        column if not statistic else f"{column}_{statistic}"
        for column, statistic in summary.columns.to_flat_index()
    ]
    return summary.sort_values("macro_f1_mean", ascending=False)


def evaluate_stage(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    candidates: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    dataset = labels.merge(features, on="filename", how="inner", validate="one_to_one")
    if len(dataset) != len(labels):
        raise ValueError("Some labels do not have cached features.")

    feature_columns = [column for column in features.columns if column != "filename"]
    x = dataset[feature_columns]
    y = dataset["label"]
    rows: list[dict[str, Any]] = []

    for candidate, parameters in candidates.items():
        for seed in VALIDATION_SEEDS:
            print(f"Evaluating {candidate}, validation seed {seed}...")
            cross_validation = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
            started = time.perf_counter()
            predictions = cross_val_predict(
                make_candidate_model(parameters),
                x,
                y,
                cv=cross_validation,
                n_jobs=-1,
            )
            elapsed = time.perf_counter() - started
            report = classification_report(
                y, predictions, labels=LABELS, output_dict=True, zero_division=0
            )
            rows.append(
                {
                    "candidate": candidate,
                    "parameters": json.dumps(parameters, sort_keys=True),
                    "validation_seed": seed,
                    "macro_f1": float(f1_score(y, predictions, average="macro")),
                    "accuracy": float(report["accuracy"]),
                    "normal_f1": float(report["Normal"]["f1-score"]),
                    "side_i_precision": float(report["Side I"]["precision"]),
                    "side_i_recall": float(report["Side I"]["recall"]),
                    "side_i_f1": float(report["Side I"]["f1-score"]),
                    "side_ii_recall": float(report["Side II"]["recall"]),
                    "side_ii_f1": float(report["Side II"]["f1-score"]),
                    "training_seconds": elapsed,
                }
            )
    return pd.DataFrame(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run reproducible Rail tuning stages.")
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument(
        "--stage",
        choices=[
            "tree-count",
            "tree-shape",
            "max-features",
            "class-imbalance",
            "smote-calibration",
            "feature-selection",
            "hierarchical-model",
        ],
        required=True,
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("outputs/tuning"), help="Experiment results"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    features = pd.read_csv(args.features)
    labels = pd.read_csv(args.labels, dtype={"filename": str, "label": str})
    results = evaluate_stage(features, labels, stage_candidates(args.stage))
    summary = summarize_results(results)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    detailed_path = args.output_dir / f"{args.stage}_detailed.csv"
    summary_path = args.output_dir / f"{args.stage}_summary.csv"
    results.to_csv(detailed_path, index=False)
    summary.to_csv(summary_path, index=False)

    print("\n", summary.to_string(index=False))
    print(f"\nSaved detailed results to {detailed_path}")
    print(f"Saved summary to {summary_path}")


if __name__ == "__main__":
    main()

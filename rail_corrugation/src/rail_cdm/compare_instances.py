from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from rail_cdm.features import extract_car_feature_rows
from rail_cdm.io import read_sensor_csv
from rail_cdm.train import make_final_model
from rail_cdm.tune import LABELS, VALIDATION_SEEDS, summarize_results

SIDE_I_MULTIPLIER = 1.5


def extract_car_feature_table(paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for number, path in enumerate(paths, start=1):
        print(f"[{number:>3}/{len(paths)}] Extracting car instances from {path.name}")
        for car_features in extract_car_feature_rows(read_sensor_csv(path)):
            rows.append({"filename": path.name, **car_features})
    return pd.DataFrame(rows)


def _car_model(model_type: str) -> Pipeline:
    if model_type == "random_forest":
        classifier: Any = RandomForestClassifier(
            n_estimators=500,
            class_weight="balanced_subsample",
            min_samples_split=4,
            max_features="sqrt",
            n_jobs=-1,
            random_state=42,
        )
    elif model_type == "logistic_regression":
        classifier = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "logistic",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=5_000,
                        random_state=42,
                    ),
                ),
            ]
        )
    else:
        raise ValueError(f"Unknown car model: {model_type}")
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("variance_filter", VarianceThreshold()),
            ("feature_selector", SelectKBest(score_func=f_classif, k=30)),
            ("classifier", classifier),
        ]
    )


def _aligned_probabilities(model: Any, x: pd.DataFrame) -> np.ndarray:
    probabilities = model.predict_proba(x)
    class_names = [str(class_name) for class_name in model.classes_]
    return np.column_stack(
        [probabilities[:, class_names.index(class_name)] for class_name in LABELS]
    )


def _adjust_side_i(probabilities: np.ndarray) -> np.ndarray:
    adjusted = probabilities.copy()
    adjusted[:, LABELS.index("Side I")] *= SIDE_I_MULTIPLIER
    return adjusted / adjusted.sum(axis=1, keepdims=True)


def _pool_car_probabilities(
    filenames: pd.Series,
    probabilities: np.ndarray,
    validation_filenames: list[str],
    method: str,
) -> np.ndarray:
    probability_frame = pd.DataFrame(probabilities, columns=LABELS)
    probability_frame.insert(0, "filename", filenames.to_numpy())
    grouped = probability_frame.groupby("filename")[LABELS]
    if method == "mean":
        pooled = grouped.mean()
    elif method == "median":
        pooled = grouped.median()
    elif method == "top_two_mean":
        pooled = grouped.agg(lambda values: np.mean(np.sort(values.to_numpy())[-2:]))
    elif method == "maximum":
        pooled = grouped.max()
    else:
        raise ValueError(f"Unknown pooling method: {method}")
    pooled_values = pooled.loc[validation_filenames].to_numpy()
    return pooled_values / pooled_values.sum(axis=1, keepdims=True)


def _metrics_row(
    candidate: str,
    seed: int,
    labels: pd.Series,
    probabilities: np.ndarray,
    elapsed: float,
) -> dict[str, float | int | str]:
    predictions = np.asarray(LABELS)[np.argmax(probabilities, axis=1)]
    report = classification_report(
        labels, predictions, labels=LABELS, output_dict=True, zero_division=0
    )
    return {
        "candidate": candidate,
        "validation_seed": seed,
        "macro_f1": float(f1_score(labels, predictions, average="macro")),
        "accuracy": float(report["accuracy"]),
        "normal_f1": float(report["Normal"]["f1-score"]),
        "side_i_precision": float(report["Side I"]["precision"]),
        "side_i_recall": float(report["Side I"]["recall"]),
        "side_i_f1": float(report["Side I"]["f1-score"]),
        "side_ii_recall": float(report["Side II"]["recall"]),
        "side_ii_f1": float(report["Side II"]["f1-score"]),
        "training_seconds": elapsed,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare train-level and per-car models.")
    parser.add_argument("--train-dir", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/tuning"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    train_features = pd.read_csv(args.features)
    labels = pd.read_csv(args.labels, dtype={"filename": str, "label": str})
    paths = [args.train_dir / filename for filename in labels["filename"]]
    car_feature_cache = args.output_dir / "car_instance_features.csv"
    if car_feature_cache.exists():
        print(f"Loading cached car instances: {car_feature_cache}")
        car_features = pd.read_csv(car_feature_cache)
    else:
        car_features = extract_car_feature_table(paths)
    car_dataset = car_features.merge(labels, on="filename", validate="many_to_one")
    train_dataset = labels.merge(train_features, on="filename", validate="one_to_one")
    train_columns = [column for column in train_features if column != "filename"]
    car_columns = [
        column for column in car_features if column not in {"filename", "car_index"}
    ]
    rows: list[dict[str, float | int | str]] = []

    for seed in VALIDATION_SEEDS:
        print(f"Evaluating per-car models, validation seed {seed}...")
        started = time.perf_counter()
        validation = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        candidate_probabilities = {
            "whole_train_view": np.zeros((len(labels), len(LABELS))),
            "car_rf_mean": np.zeros((len(labels), len(LABELS))),
            "car_rf_median": np.zeros((len(labels), len(LABELS))),
            "car_rf_top_two_mean": np.zeros((len(labels), len(LABELS))),
            "car_rf_maximum": np.zeros((len(labels), len(LABELS))),
            "car_logistic_mean": np.zeros((len(labels), len(LABELS))),
            "car_logistic_median": np.zeros((len(labels), len(LABELS))),
            "car_logistic_top_two_mean": np.zeros((len(labels), len(LABELS))),
        }
        for training_indices, validation_indices in validation.split(
            train_dataset[train_columns], train_dataset["label"]
        ):
            training_filenames = set(labels.iloc[training_indices]["filename"])
            validation_filenames = labels.iloc[validation_indices]["filename"].tolist()

            global_model = clone(make_final_model()).fit(
                train_dataset.iloc[training_indices][train_columns],
                train_dataset.iloc[training_indices]["label"],
            )
            candidate_probabilities["whole_train_view"][validation_indices] = (
                _aligned_probabilities(
                    global_model, train_dataset.iloc[validation_indices][train_columns]
                )
            )

            car_training = car_dataset["filename"].isin(training_filenames)
            car_validation = car_dataset["filename"].isin(validation_filenames)
            validation_car_rows = car_dataset.loc[car_validation]
            for model_type, candidate_prefix in (
                ("random_forest", "car_rf"),
                ("logistic_regression", "car_logistic"),
            ):
                car_model = _car_model(model_type).fit(
                    car_dataset.loc[car_training, car_columns],
                    car_dataset.loc[car_training, "label"],
                )
                car_probabilities = _aligned_probabilities(
                    car_model, validation_car_rows[car_columns]
                )
                for pooling_method in ("mean", "median", "top_two_mean", "maximum"):
                    if model_type == "logistic_regression" and pooling_method == "maximum":
                        continue
                    pooled = _pool_car_probabilities(
                        validation_car_rows["filename"],
                        car_probabilities,
                        validation_filenames,
                        pooling_method,
                    )
                    candidate_probabilities[f"{candidate_prefix}_{pooling_method}"][
                        validation_indices
                    ] = _adjust_side_i(pooled)

        candidate_probabilities["blend_global_car_rf_mean"] = (
            0.5 * candidate_probabilities["whole_train_view"]
            + 0.5 * candidate_probabilities["car_rf_mean"]
        )
        candidate_probabilities["blend_90_global_10_car_rf_top_two"] = (
            0.9 * candidate_probabilities["whole_train_view"]
            + 0.1 * candidate_probabilities["car_rf_top_two_mean"]
        )
        candidate_probabilities["blend_80_global_20_car_rf_top_two"] = (
            0.8 * candidate_probabilities["whole_train_view"]
            + 0.2 * candidate_probabilities["car_rf_top_two_mean"]
        )
        elapsed = time.perf_counter() - started
        for candidate, probabilities in candidate_probabilities.items():
            rows.append(
                _metrics_row(candidate, seed, labels["label"], probabilities, elapsed)
            )

    results = pd.DataFrame(rows)
    summary = summarize_results(results)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    car_features.to_csv(args.output_dir / "car_instance_features.csv", index=False)
    results.to_csv(args.output_dir / "car-instance_detailed.csv", index=False)
    summary.to_csv(args.output_dir / "car-instance_summary.csv", index=False)
    print("\n", summary.to_string(index=False))


if __name__ == "__main__":
    main()

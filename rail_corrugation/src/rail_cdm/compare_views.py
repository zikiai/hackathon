from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold

from rail_cdm.features import extract_cross_car_consensus_features
from rail_cdm.io import read_sensor_csv
from rail_cdm.train import make_final_model
from rail_cdm.tune import LABELS, VALIDATION_SEEDS, make_candidate_model, summarize_results


def extract_consensus_table(paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for number, path in enumerate(paths, start=1):
        print(f"[{number:>3}/{len(paths)}] Extracting consensus from {path.name}")
        rows.append(
            {
                "filename": path.name,
                **extract_cross_car_consensus_features(read_sensor_csv(path)),
            }
        )
    return pd.DataFrame(rows)


def _aligned_probabilities(model: Any, x: pd.DataFrame) -> np.ndarray:
    probabilities = model.predict_proba(x)
    class_names = [str(class_name) for class_name in model.classes_]
    return np.column_stack(
        [probabilities[:, class_names.index(class_name)] for class_name in LABELS]
    )


def _model_probabilities(
    model: Any,
    x: pd.DataFrame,
    y: pd.Series,
    validation: StratifiedKFold,
) -> np.ndarray:
    probabilities = np.zeros((len(x), len(LABELS)), dtype=float)
    for training_indices, validation_indices in validation.split(x, y):
        fold_model = clone(model).fit(x.iloc[training_indices], y.iloc[training_indices])
        probabilities[validation_indices] = _aligned_probabilities(
            fold_model, x.iloc[validation_indices]
        )
    return probabilities


def _metrics_row(
    candidate: str,
    seed: int,
    y: pd.Series,
    probabilities: np.ndarray,
    elapsed: float,
) -> dict[str, float | int | str]:
    predictions = np.asarray(LABELS)[np.argmax(probabilities, axis=1)]
    report = classification_report(
        y, predictions, labels=LABELS, output_dict=True, zero_division=0
    )
    return {
        "candidate": candidate,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare whole-train and cross-car views.")
    parser.add_argument("--train-dir", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/tuning"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    base_features = pd.read_csv(args.features)
    labels = pd.read_csv(args.labels, dtype={"filename": str, "label": str})
    paths = [args.train_dir / filename for filename in labels["filename"]]
    consensus_features = extract_consensus_table(paths)
    augmented_features = base_features.merge(
        consensus_features, on="filename", validate="one_to_one"
    )

    base_columns = [column for column in base_features if column != "filename"]
    consensus_columns = [column for column in consensus_features if column != "filename"]
    augmented_columns = [column for column in augmented_features if column != "filename"]
    dataset = labels.merge(augmented_features, on="filename", validate="one_to_one")
    y = dataset["label"]

    common = {
        "min_samples_split": 4,
        "sampling": "smote",
        "sampling_target": 48,
        "smote_neighbors": 2,
        "side_i_multiplier": 1.5,
    }
    base_model = make_final_model()
    augmented_model = make_candidate_model({**common, "feature_count": 30})
    consensus_model = make_candidate_model({**common, "feature_count": 20})
    rows: list[dict[str, float | int | str]] = []

    for seed in VALIDATION_SEEDS:
        print(f"Evaluating multi-view models, validation seed {seed}...")
        validation = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        started = time.perf_counter()
        base_probabilities = _model_probabilities(
            base_model, dataset[base_columns], y, validation
        )
        augmented_probabilities = _model_probabilities(
            augmented_model, dataset[augmented_columns], y, validation
        )
        consensus_probabilities = _model_probabilities(
            consensus_model, dataset[consensus_columns], y, validation
        )
        elapsed = time.perf_counter() - started
        candidates = {
            "whole_train_view": base_probabilities,
            "whole_train_plus_consensus": augmented_probabilities,
            "consensus_only": consensus_probabilities,
            "blend_75_global_25_augmented": (
                0.75 * base_probabilities + 0.25 * augmented_probabilities
            ),
            "blend_50_global_50_augmented": (
                0.50 * base_probabilities + 0.50 * augmented_probabilities
            ),
            "blend_25_global_75_augmented": (
                0.25 * base_probabilities + 0.75 * augmented_probabilities
            ),
        }
        for candidate, probabilities in candidates.items():
            rows.append(_metrics_row(candidate, seed, y, probabilities, elapsed))

    results = pd.DataFrame(rows)
    summary = summarize_results(results)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output_dir / "multi-view_detailed.csv", index=False)
    summary.to_csv(args.output_dir / "multi-view_summary.csv", index=False)
    print("\n", summary.to_string(index=False))


if __name__ == "__main__":
    main()

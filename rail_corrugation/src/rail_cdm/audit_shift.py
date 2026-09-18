from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from rail_cdm.features import extract_feature_table

RANDOM_SEED = 42


def selected_feature_names(bundle: dict[str, Any]) -> list[str]:
    """Recover the measurements retained by the fitted feature-selection pipeline."""
    model = bundle["model"]
    original_names = bundle["feature_columns"]
    variance_filter = model.named_steps["variance_filter"]
    selector = model.named_steps["feature_selector"]
    after_variance = [
        name
        for name, keep in zip(original_names, variance_filter.get_support(), strict=True)
        if keep
    ]
    return [
        name
        for name, keep in zip(after_variance, selector.get_support(), strict=True)
        if keep
    ]


def feature_shift_table(
    training_features: pd.DataFrame,
    test_features: pd.DataFrame,
    feature_names: list[str],
) -> pd.DataFrame:
    """Compare selected feature distributions without using hidden test answers."""
    rows: list[dict[str, float | str]] = []
    for feature_name in feature_names:
        training = training_features[feature_name].to_numpy(dtype=float)
        test = test_features[feature_name].to_numpy(dtype=float)
        pooled_scale = np.sqrt((np.var(training) + np.var(test)) / 2) + 1e-12
        rows.append(
            {
                "feature": feature_name,
                "ks_statistic": float(ks_2samp(training, test).statistic),
                "standardized_mean_shift": float(
                    abs(np.mean(training) - np.mean(test)) / pooled_scale
                ),
                "training_median": float(np.median(training)),
                "test_median": float(np.median(test)),
            }
        )
    return pd.DataFrame(rows).sort_values("ks_statistic", ascending=False)


def domain_classifier_auc(
    training_features: pd.DataFrame,
    test_features: pd.DataFrame,
    feature_names: list[str],
) -> float:
    """Measure whether a classifier can tell training and test rows apart."""
    combined = pd.concat(
        [training_features[feature_names], test_features[feature_names]], ignore_index=True
    )
    domain_labels = np.concatenate(
        [np.zeros(len(training_features), dtype=int), np.ones(len(test_features), dtype=int)]
    )
    validation = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    classifier = RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        min_samples_leaf=3,
        max_features="sqrt",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    probabilities = cross_val_predict(
        classifier,
        combined,
        domain_labels,
        cv=validation,
        method="predict_proba",
        n_jobs=1,
    )[:, 1]
    return float(roc_auc_score(domain_labels, probabilities))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Rail train/test feature similarity.")
    parser.add_argument("--train-features", type=Path, required=True)
    parser.add_argument("--test-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/generalization"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    training_features = pd.read_csv(args.train_features)
    test_paths = sorted(
        args.test_dir.glob("*.csv"),
        key=lambda path: int("".join(character for character in path.stem if character.isdigit())),
    )
    if not test_paths:
        raise ValueError(f"No test CSV files found in {args.test_dir}")

    test_features = extract_feature_table(test_paths)
    bundle = joblib.load(args.model)
    feature_names = selected_feature_names(bundle)
    shift = feature_shift_table(training_features, test_features, feature_names)
    domain_auc = domain_classifier_auc(training_features, test_features, feature_names)

    report = {
        "training_files": len(training_features),
        "test_files": len(test_features),
        "selected_features": len(feature_names),
        "domain_classifier_auc": domain_auc,
        "median_ks_statistic": float(shift["ks_statistic"].median()),
        "maximum_ks_statistic": float(shift["ks_statistic"].max()),
        "median_standardized_mean_shift": float(
            shift["standardized_mean_shift"].median()
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    shift.to_csv(args.output_dir / "feature_shift.csv", index=False)
    (args.output_dir / "distribution_shift.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

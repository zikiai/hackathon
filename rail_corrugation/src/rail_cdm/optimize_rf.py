"""Bounded, paired experiments around the promoted Rail Random Forest.

This command only writes research reports; it never replaces active artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import clone
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import RobustScaler, StandardScaler

from rail_cdm.train import make_final_model
from rail_cdm.tune import LABELS, VALIDATION_SEEDS


def candidate_settings() -> dict[str, dict]:
    # Declare a small search before scoring; each changes one hypothesis.
    return {
        "baseline": {},
        "features_20": {"feature_selector__k": 20},
        "features_25": {"feature_selector__k": 25},
        "features_35": {"feature_selector__k": 35},
        "features_40": {"feature_selector__k": 40},
        "standard_scaled_smote": {"smote_scaler": "standard"},
        "robust_scaled_smote": {"smote_scaler": "robust"},
        "entropy_splits": {"model__estimator__classifier__criterion": "entropy"},
        "features_per_split_25pct": {"model__estimator__classifier__max_features": 0.25},
        "bootstrap_75pct": {"model__estimator__classifier__max_samples": 0.75},
        "smote_target_32": {"sampler__sampling_strategy": {"Side I": 32, "Side II": 32}},
        "smote_target_64": {"sampler__sampling_strategy": {"Side I": 64, "Side II": 64}},
        "smote_neighbors_1": {"sampler__k_neighbors": 1},
        "smote_neighbors_3": {"sampler__k_neighbors": 3},
        "side_i_multiplier_1_3": {"model__class_multipliers": (("Side I", 1.3),)},
        "side_i_multiplier_1_75": {"model__class_multipliers": (("Side I", 1.75),)},
        "min_split_2": {"model__estimator__classifier__min_samples_split": 2},
        "min_split_8": {"model__estimator__classifier__min_samples_split": 8},
        "min_leaf_2": {"model__estimator__classifier__min_samples_leaf": 2},
        "max_depth_6": {"model__estimator__classifier__max_depth": 6},
    }


def build_candidate(name: str, forest_seed: int = 42):
    settings = candidate_settings()[name].copy()
    scaler = settings.pop("smote_scaler", None)
    model = make_final_model()
    if scaler is not None:
        transform = StandardScaler() if scaler == "standard" else RobustScaler()
        position = [step for step, _ in model.steps].index("sampler")
        model.steps.insert(position, ("smote_scaler", transform))
    model.set_params(
        **settings,
        model__estimator__classifier__random_state=forest_seed,
        model__estimator__classifier__n_jobs=1,
    )
    return model


def paired_summary(results: pd.DataFrame) -> pd.DataFrame:
    keys = ["validation_seed", "forest_seed"]
    baseline = results.loc[results.candidate == "baseline", keys + ["macro_f1"]]
    paired = results.merge(baseline, on=keys, validate="many_to_one", suffixes=("", "_base"))
    paired["delta"] = paired.macro_f1 - paired.macro_f1_base
    paired["win"] = paired.delta > 1e-12
    summary = paired.groupby("candidate", as_index=False).agg(
        macro_f1_mean=("macro_f1", "mean"),
        macro_f1_std=("macro_f1", "std"),
        mean_delta=("delta", "mean"),
        minimum_delta=("delta", "min"),
        paired_wins=("win", "sum"),
        comparisons=("win", "size"),
        side_i_precision_mean=("side_i_precision", "mean"),
        side_i_recall_mean=("side_i_recall", "mean"),
        side_i_f1_mean=("side_i_f1", "mean"),
        side_ii_f1_mean=("side_ii_f1", "mean"),
    )
    summary["passes_screen"] = (summary.mean_delta > 0.01) & (
        summary.paired_wins >= np.ceil(0.8 * summary.comparisons)
    )
    return summary.sort_values("macro_f1_mean", ascending=False)


def load_training(features_path: Path, labels_path: Path) -> pd.DataFrame:
    features = pd.read_csv(features_path)
    labels = pd.read_csv(labels_path)
    if set(features.filename) != set(labels.filename):
        raise ValueError("Features and labels must cover exactly the same recordings.")
    dataset = labels.merge(features, on="filename", validate="one_to_one")
    if set(dataset.label) != set(LABELS) or dataset.isna().any().any():
        raise ValueError("Expected complete features and all three known classes.")
    return dataset


def fold_probabilities(model, x, y, train, valid):
    fitted = clone(model).fit(x.iloc[train], y.iloc[train])
    probabilities = fitted.predict_proba(x.iloc[valid])
    order = [list(fitted.classes_).index(label) for label in LABELS]
    return valid, probabilities[:, order]


def out_of_fold_probabilities(model, x, y, validation, jobs):
    # cross_val_predict(method="predict_proba") encodes labels as integers before
    # fit, which would bypass ProbabilityAdjustedClassifier's named multipliers.
    folds = Parallel(n_jobs=jobs)(
        delayed(fold_probabilities)(model, x, y, train, valid)
        for train, valid in validation.split(x, y)
    )
    probabilities = np.zeros((len(x), len(LABELS)))
    for valid, fold_values in folds:
        probabilities[valid] = fold_values
    return probabilities


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--candidates", nargs="+", choices=list(candidate_settings()))
    parser.add_argument("--validation-seeds", nargs="+", type=int, default=VALIDATION_SEEDS)
    parser.add_argument("--forest-seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--jobs", type=int, default=5)
    args = parser.parse_args()
    names = list(dict.fromkeys(["baseline", *(args.candidates or candidate_settings())]))
    dataset = load_training(args.features, args.labels)
    x = dataset.drop(columns=["filename", "label"])
    y = dataset.label
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "library_versions": {
            name: version(name) for name in ("scikit-learn", "imbalanced-learn", "numpy", "pandas")
        },
        "feature_sha256": hashlib.sha256(args.features.read_bytes()).hexdigest(),
        "label_sha256": hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        "candidates": {name: candidate_settings()[name] for name in names},
        "validation_seeds": args.validation_seeds,
        "forest_seeds": args.forest_seeds,
        "screen": "mean macro F1 gain > 0.01 and wins in >= 80% of paired arrangements",
        "caution": "Repeated CV reuses recordings; this is not an independent test score.",
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    rows = []
    predictions = []
    for name in names:
        for forest_seed in args.forest_seeds:
            for seed in args.validation_seeds:
                model = build_candidate(name, forest_seed)
                validation = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
                probabilities = out_of_fold_probabilities(model, x, y, validation, args.jobs)
                predicted = np.asarray(LABELS)[probabilities.argmax(axis=1)]
                report = classification_report(
                    y, predicted, labels=LABELS, output_dict=True, zero_division=0
                )
                row = {
                    "candidate": name,
                    "validation_seed": seed,
                    "forest_seed": forest_seed,
                    "macro_f1": f1_score(y, predicted, average="macro"),
                    "accuracy": report["accuracy"],
                    "side_i_precision": report["Side I"]["precision"],
                    "side_i_recall": report["Side I"]["recall"],
                    "side_i_f1": report["Side I"]["f1-score"],
                    "side_ii_f1": report["Side II"]["f1-score"],
                    "confusion_matrix": json.dumps(
                        confusion_matrix(y, predicted, labels=LABELS).tolist()
                    ),
                }
                rows.append(row)
                prediction = dataset[["filename", "label"]].copy()
                prediction["candidate"] = name
                prediction["validation_seed"] = seed
                prediction["forest_seed"] = forest_seed
                prediction["prediction"] = predicted
                prediction[["probability_normal", "probability_side_i", "probability_side_ii"]] = (
                    probabilities
                )
                predictions.append(prediction)
                print(
                    f"{name}: split={seed}, forest={forest_seed}, F1={row['macro_f1']:.6f}",
                    flush=True,
                )
        results = pd.DataFrame(rows)
        results.to_csv(args.output_dir / "rf-refinement_detailed.csv", index=False)
        paired_summary(results).to_csv(args.output_dir / "rf-refinement_summary.csv", index=False)
        pd.concat(predictions, ignore_index=True).to_csv(
            args.output_dir / "out_of_fold.csv", index=False
        )
    print(paired_summary(pd.DataFrame(rows)).to_string(index=False))


if __name__ == "__main__":
    main()

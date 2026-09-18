from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from rail_cdm.features import extract_periodicity_features
from rail_cdm.io import read_sensor_csv
from rail_cdm.tune import evaluate_stage, summarize_results


def extract_periodicity_table(paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for number, path in enumerate(paths, start=1):
        print(f"[{number:>3}/{len(paths)}] Extracting periodicity from {path.name}")
        rows.append(
            {"filename": path.name, **extract_periodicity_features(read_sensor_csv(path))}
        )
    return pd.DataFrame(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test rail-vibration periodicity features.")
    parser.add_argument("--train-dir", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/tuning"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    base_features = pd.read_csv(args.features)
    labels = pd.read_csv(args.labels, dtype={"filename": str, "label": str})
    cache_path = args.output_dir / "periodicity_features.csv"
    if cache_path.exists():
        print(f"Loading cached periodicity features: {cache_path}")
        periodicity = pd.read_csv(cache_path)
    else:
        paths = [args.train_dir / filename for filename in labels["filename"]]
        periodicity = extract_periodicity_table(paths)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        periodicity.to_csv(cache_path, index=False)

    augmented = base_features.merge(periodicity, on="filename", validate="one_to_one")
    common = {
        "min_samples_split": 4,
        "sampling": "smote",
        "sampling_target": 48,
        "smote_neighbors": 2,
        "side_i_multiplier": 1.5,
    }
    candidates = {
        f"periodicity_top_{feature_count}": {
            **common,
            "feature_count": feature_count,
        }
        for feature_count in (20, 30, 40, 60)
    }
    results = evaluate_stage(augmented, labels, candidates)
    summary = summarize_results(results)
    results.to_csv(args.output_dir / "periodicity-view_detailed.csv", index=False)
    summary.to_csv(args.output_dir / "periodicity-view_summary.csv", index=False)
    print("\n", summary.to_string(index=False))
    print("\nCurrent whole-train reference macro F1: 0.822854")


if __name__ == "__main__":
    main()

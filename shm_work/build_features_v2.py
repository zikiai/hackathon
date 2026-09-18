"""Add two rainflow features while preserving all original features.

Place beside build_features.py inside shm_work and run this script.
Creates features_v2.csv; does not modify features.csv or train a model.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import rainflow
from build_features import extract_features, load_stress


def extract_features_v2(stress):
    # Reuse the original feature code so the first 17 stay consistent.
    features = extract_features(stress)
    cycles = rainflow.count_cycles(stress)
    if cycles:
        ranges = np.array([item[0] for item in cycles], dtype=float)
        counts = np.array([item[1] for item in cycles], dtype=float)
        # Full cycles count as 1, half-cycles as 0.5.
        # Use unrounded cycle ranges; these are features, not damage labels.
        power4 = float(np.sum(counts * ranges ** 4))
        power6 = float(np.sum(counts * ranges ** 6))
    else:
        power4 = 0.0
        power6 = 0.0
    features["rf_range_power4_sum"] = power4
    features["rf_range_power6_sum"] = power6
    if not np.isfinite(list(features.values())).all():
        raise ValueError("Feature calculation produced missing or infinite values.")
    return features


def main():
    folder = Path(__file__).resolve().parent
    default_data = (folder.parent / "NebulaX-Hackathon-ProblemStatement-main"
                    / "PS3" / "02_Datasets" / "SHM")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=default_data)
    parser.add_argument("--output", type=Path, default=folder / "features_v2.csv")
    args = parser.parse_args()
    if args.output.resolve() == (folder / "features.csv").resolve():
        raise ValueError("Choose a new output filename, not the original features.csv.")
    labels_path = args.data_dir / "Train_Labels.csv"
    if not labels_path.is_file():
        raise FileNotFoundError(f"Labels not found:\n{labels_path}")
    labels = pd.read_csv(labels_path)
    if not {"filename", "damage"}.issubset(labels.columns) or labels.empty:
        raise ValueError("Labels must contain filename and damage, with at least one row.")
    if labels.filename.isna().any():
        raise ValueError("Missing filename in labels.")
    labels["filename"] = labels.filename.astype(str).str.strip()
    if labels.filename.eq("").any() or labels.filename.duplicated().any():
        raise ValueError("Empty or duplicate filenames in labels.")
    labels["damage"] = pd.to_numeric(labels.damage, errors="raise")
    if not np.isfinite(labels.damage.to_numpy()).all() or (labels.damage < 0).any():
        raise ValueError("Missing, infinite, or negative damage labels.")
    for name in labels.filename:
        if Path(name).name != name or not (args.data_dir / "Train" / name).is_file():
            raise FileNotFoundError(f"Invalid or missing training filename: {name}")

    print(f"Found {len(labels)} labelled recordings.")
    print("Keeping original features and adding fourth- and sixth-power cycle sums.")
    print("This extracts features only; it does not train a model.\n")
    rows = []
    for number, row in enumerate(labels.itertuples(index=False), 1):
        print(f"[{number}/{len(labels)}] Processing {row.filename}...", flush=True)
        try:
            stress = load_stress(args.data_dir / "Train" / row.filename)
            features = extract_features_v2(stress)
        except Exception as error:
            raise RuntimeError(f"Failed on {row.filename}: {error}") from error
        rows.append({"filename": row.filename, **features, "damage": float(row.damage)})
    table = pd.DataFrame(rows)

    # If present, check that the original features and labels are reproduced.
    original_path = folder / "features.csv"
    if original_path.is_file():
        original = pd.read_csv(original_path)
        if original.filename.duplicated().any() or set(original.filename) != set(table.filename):
            raise ValueError("Original features.csv lists different or duplicate recordings. Check the dataset.")
        new_indexed = table.set_index("filename")
        old_indexed = original.set_index("filename").loc[new_indexed.index]
        columns = old_indexed.columns.tolist()
        if not set(columns).issubset(new_indexed.columns):
            raise ValueError("Original feature columns differ from the feature extraction code.")
        if not np.allclose(old_indexed[columns].to_numpy(dtype=float),
                           new_indexed[columns].to_numpy(dtype=float), rtol=1e-8, atol=1e-10):
            raise ValueError("Original values changed. Check your extraction code/data before comparing models.")
        print("\nVerified: the original features and labels are unchanged.")

    # Write only after every recording and validation check succeeds.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    print(f"\nFinished: {len(table)} recordings, {len(table.columns)-2} input features.")
    print(f"Saved: {args.output.resolve()}")
    print("\nNew-feature preview:")
    print(table[["filename", "rf_range_power4_sum", "rf_range_power6_sum"]].head().to_string(index=False))
    print("\nOriginal datasets, features.csv, and saved models were not changed.")
    print("Re-running this script replaces features_v2.csv. No model has been trained.")


if __name__ == "__main__":
    main()

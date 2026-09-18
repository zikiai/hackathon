from pathlib import Path

import numpy as np
import pandas as pd
import rainflow


def extract_features(stress):
    """Calculate useful measurements from one stress recording."""

    # Basic stress measurements.
    features = {
        "stress_min": float(stress.min()),
        "stress_max": float(stress.max()),
        "stress_mean": float(stress.mean()),
        "stress_std": float(stress.std()),
        "stress_range": float(np.ptp(stress)),
        "stress_rms": float(np.sqrt(np.mean(stress ** 2))),
    }

    # Typical low, middle, and high stress values.
    p05, p50, p95 = np.percentile(stress, [5, 50, 95])

    features.update({
        "stress_p05": float(p05),
        "stress_median": float(p50),
        "stress_p95": float(p95),
        "stress_p95_minus_p05": float(p95 - p05),
    })

    # Average size of changes between neighbouring readings.
    # This is change per sample, not change per second.
    features["mean_absolute_change"] = float(
        np.mean(np.abs(np.diff(stress)))
    )

    # Identify loading cycles.
    cycles = rainflow.count_cycles(stress)

    if cycles:
        ranges = np.array(
            [cycle_range for cycle_range, count in cycles],
            dtype=float,
        )
        counts = np.array(
            [count for cycle_range, count in cycles],
            dtype=float,
        )

        mean_range = float(np.average(ranges, weights=counts))

        features.update({
            "rf_cycle_count": float(counts.sum()),
            "rf_mean_range": mean_range,
            "rf_std_range": float(
                np.sqrt(
                    np.average(
                        (ranges - mean_range) ** 2,
                        weights=counts,
                    )
                )
            ),
            "rf_max_range": float(ranges.max()),

            # Trial features that emphasise larger loading cycles.
            # These are NOT damage predictions or known material constants.
            "rf_range_power3_sum": float(
                np.sum(counts * ranges ** 3)
            ),
            "rf_range_power5_sum": float(
                np.sum(counts * ranges ** 5)
            ),
        })
    else:
        # A constant recording may contain no loading cycles.
        features.update({
            "rf_cycle_count": 0.0,
            "rf_mean_range": 0.0,
            "rf_std_range": 0.0,
            "rf_max_range": 0.0,
            "rf_range_power3_sum": 0.0,
            "rf_range_power5_sum": 0.0,
        })

    if not np.isfinite(list(features.values())).all():
        raise ValueError("Feature calculation produced an invalid number.")

    return features


def load_stress(file_path):
    """Read and validate a single-column stress recording."""

    if not file_path.is_file():
        raise FileNotFoundError(f"Recording not found:\n{file_path}")

    recording = pd.read_csv(
        file_path,
        header=None,
        skip_blank_lines=False,
    )

    if recording.shape[1] != 1:
        raise ValueError(
            f"{file_path.name}: expected one column, "
            f"but found {recording.shape[1]}."
        )

    stress = pd.to_numeric(
        recording.iloc[:, 0],
        errors="raise",
    ).to_numpy(dtype=float)

    if len(stress) < 2:
        raise ValueError(
            f"{file_path.name}: fewer than two stress readings."
        )

    if not np.isfinite(stress).all():
        raise ValueError(
            f"{file_path.name}: contains missing or infinite readings."
        )

    return stress


def main():
    # build_features.py is inside hackathon/shm_work/.
    script_folder = Path(__file__).resolve().parent
    project_folder = script_folder.parent

    data_folder = (
        project_folder
        / "NebulaX-Hackathon-ProblemStatement-main"
        / "PS3"
        / "02_Datasets"
        / "SHM"
    )

    train_folder = data_folder / "Train"
    labels_path = data_folder / "Train_Labels.csv"
    output_path = script_folder / "features.csv"

    if not labels_path.is_file():
        raise FileNotFoundError(
            f"Could not find the labels file:\n{labels_path}"
        )

    # Read filenames and their known damage values.
    labels = pd.read_csv(labels_path)

    if not {"filename", "damage"}.issubset(labels.columns):
        raise ValueError(
            "Train_Labels.csv must contain 'filename' and 'damage'."
        )

    if labels.empty:
        raise ValueError("The labels file contains no examples.")

    if labels["filename"].isna().any():
        raise ValueError("The labels file contains missing filenames.")

    labels["filename"] = labels["filename"].astype(str).str.strip()

    if labels["filename"].eq("").any():
        raise ValueError("The labels file contains empty filenames.")

    if labels["filename"].duplicated().any():
        raise ValueError("The labels file contains duplicate filenames.")

    labels["damage"] = pd.to_numeric(
        labels["damage"],
        errors="raise",
    )

    if not np.isfinite(labels["damage"].to_numpy(dtype=float)).all():
        raise ValueError("The labels contain missing or infinite damage.")

    if (labels["damage"] < 0).any():
        raise ValueError("The labels contain negative damage values.")

    # Check that all required recordings exist before processing.
    missing_files = [
        filename
        for filename in labels["filename"]
        if not (train_folder / filename).is_file()
    ]

    if missing_files:
        raise FileNotFoundError(
            "Missing training recordings:\n" + "\n".join(missing_files)
        )

    print(f"Found {len(labels)} labelled training recordings.")
    print("Calculating features. This may take a few minutes.")
    print("The original recordings will not be changed.\n")

    rows = []

    # Process every recording listed in Train_Labels.csv.
    for number, label in enumerate(
        labels.itertuples(index=False),
        start=1,
    ):
        filename = label.filename

        print(
            f"[{number}/{len(labels)}] Processing {filename}...",
            flush=True,
        )

        try:
            stress = load_stress(train_folder / filename)
            features = extract_features(stress)
        except Exception as error:
            raise RuntimeError(
                f"Could not process {filename}: {error}"
            ) from error

        # One recording becomes one row in the final table.
        rows.append({
            "filename": filename,
            **features,
            "damage": float(label.damage),
        })

    features_table = pd.DataFrame(rows)

    # Save only after every recording has been processed successfully.
    # Running this script again replaces this generated features.csv.
    features_table.to_csv(output_path, index=False)

    feature_count = len(features_table.columns) - 2

    print("\nFinished!")
    print(f"Recordings processed: {len(features_table)}")
    print(f"Input features per recording: {feature_count}")
    print(f"Saved to: {output_path}")
    print("\nPreview:")
    print(features_table[[
        "filename",
        "stress_std",
        "rf_cycle_count",
        "damage",
    ]].head().to_string(index=False))

    print("\nNo model has been trained yet.")
    print("This saved table is ready for the training step.")


if __name__ == "__main__":
    main()
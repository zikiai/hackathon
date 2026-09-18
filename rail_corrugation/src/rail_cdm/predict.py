from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd

from rail_cdm.features import extract_feature_table
from rail_cdm.io import ALLOWED_LABELS, list_csv_files


def validate_prediction_output(output: pd.DataFrame, expected_filenames: list[str]) -> None:
    """Require one valid official prediction for every requested recording."""
    if list(output.columns) != ["file_id", "prediction"]:
        raise ValueError("Prediction columns must be exactly file_id,prediction.")
    if not expected_filenames:
        raise ValueError("Select at least one recording.")
    if len(set(expected_filenames)) != len(expected_filenames):
        raise ValueError("Duplicate filenames detected. Each recording needs a unique filename.")
    if output.isna().any().any() or output["file_id"].duplicated().any():
        raise ValueError("Predictions contain duplicate filenames or missing values.")
    if len(output) != len(expected_filenames) or set(output.file_id) != set(expected_filenames):
        raise ValueError(
            "Some recordings failed validation. Fix them before downloading the batch."
        )
    if not set(output.prediction).issubset(ALLOWED_LABELS):
        raise ValueError("Predictions contain an unsupported rail condition.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate rail_predictions.csv.")
    parser.add_argument("--test-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/rail_predictions.csv"))
    return parser


def create_predictions(test_dir: Path, model_path: Path) -> pd.DataFrame:
    bundle = joblib.load(model_path)
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]

    paths = list_csv_files(test_dir)
    features = extract_feature_table(paths)
    x = features.reindex(columns=feature_columns)
    predictions = model.predict(x)

    output = pd.DataFrame(
        {"file_id": features["filename"].astype(str), "prediction": predictions.astype(str)}
    )
    validate_prediction_output(output, [path.name for path in paths])
    return output


def main() -> None:
    args = build_parser().parse_args()
    output = create_predictions(args.test_dir, args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(f"Saved {len(output)} predictions to {args.output}")


if __name__ == "__main__":
    main()

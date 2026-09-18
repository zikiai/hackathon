from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import numpy as np
import pandas as pd

EXPECTED_COLUMNS = 129
EXPECTED_ROWS = 10_000
ALLOWED_LABELS = {"Normal", "Side I", "Side II"}


def natural_file_key(path: Path) -> tuple[str, int]:
    """Sort Train2.csv before Train10.csv."""
    stem = path.stem
    prefix = stem.rstrip("0123456789")
    suffix = stem[len(prefix) :]
    return prefix.lower(), int(suffix) if suffix else -1


def list_csv_files(directory: str | Path) -> list[Path]:
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Data directory not found: {directory}")
    files = sorted(directory.glob("*.csv"), key=natural_file_key)
    if not files:
        raise FileNotFoundError(f"No CSV files found in: {directory}")
    return files


def read_sensor_csv(source: str | Path | BinaryIO) -> pd.DataFrame:
    """Load and validate one organizer Rail CSV."""
    frame = pd.read_csv(source)
    if frame.shape[1] != EXPECTED_COLUMNS:
        raise ValueError(
            f"Expected {EXPECTED_COLUMNS} columns (speed + 128 sensor columns), "
            f"but found {frame.shape[1]}."
        )
    if frame.empty:
        raise ValueError("The sensor file contains no readings.")
    if len(frame) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS:,} readings for a one-second recording, "
            f"but found {len(frame):,}."
        )

    numeric = frame.apply(pd.to_numeric, errors="coerce")
    bad_cells = int(numeric.isna().sum().sum())
    if bad_cells:
        raise ValueError(f"The sensor file contains {bad_cells} missing or non-numeric values.")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("The sensor file contains infinite values.")
    return numeric


def read_labels(labels_path: str | Path) -> pd.DataFrame:
    labels = pd.read_csv(labels_path, dtype={"filename": str, "label": str})
    required = {"filename", "label"}
    if not required.issubset(labels.columns):
        raise ValueError(f"Labels file must contain columns: {sorted(required)}")
    if labels["filename"].duplicated().any():
        duplicates = labels.loc[labels["filename"].duplicated(), "filename"].tolist()
        raise ValueError(f"Duplicate filenames in labels: {duplicates[:5]}")
    unknown = set(labels["label"].dropna()) - ALLOWED_LABELS
    if unknown:
        raise ValueError(f"Unexpected labels: {sorted(unknown)}")
    return labels


def validate_training_inventory(train_dir: str | Path, labels: pd.DataFrame) -> list[Path]:
    files = list_csv_files(train_dir)
    files_by_name = {path.name: path for path in files}
    labelled_names = set(labels["filename"])
    missing_files = sorted(labelled_names - set(files_by_name))
    unlabelled_files = sorted(set(files_by_name) - labelled_names)
    if missing_files:
        raise FileNotFoundError(f"Labelled files missing from Train/: {missing_files[:5]}")
    if unlabelled_files:
        raise ValueError(f"Training files missing labels: {unlabelled_files[:5]}")
    return [files_by_name[name] for name in labels["filename"]]

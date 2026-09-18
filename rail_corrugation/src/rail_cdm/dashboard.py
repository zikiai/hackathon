from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_metrics(path: Path) -> dict[str, Any]:
    """Load the validation metrics written by rail-train."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def per_class_metrics(metrics: dict[str, Any]) -> pd.DataFrame:
    """Return beginner-friendly per-class scores for tables and charts."""
    report = metrics["classification_report"]
    labels = metrics["confusion_matrix_labels"]
    return pd.DataFrame(
        [
            {
                "Class": label,
                "Precision": report[label]["precision"],
                "Recall": report[label]["recall"],
                "F1": report[label]["f1-score"],
                "Files": int(report[label]["support"]),
            }
            for label in labels
        ]
    )


def confusion_matrix_frame(metrics: dict[str, Any]) -> pd.DataFrame:
    """Return the confusion matrix with explicit actual/predicted labels."""
    labels = metrics["confusion_matrix_labels"]
    return pd.DataFrame(
        metrics["confusion_matrix"],
        index=pd.Index(labels, name="Actual"),
        columns=pd.Index(labels, name="Predicted"),
    )


def validation_errors(predictions: pd.DataFrame) -> pd.DataFrame:
    """Select validation files whose predicted class was incorrect."""
    required = {"filename", "label", "prediction"}
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"Validation predictions are missing columns: {sorted(missing)}")

    optional_columns = [
        "probability_normal",
        "probability_side_i",
        "probability_side_ii",
        "confidence",
        "confidence_margin",
    ]
    selected_columns = ["filename", "label", "prediction"] + [
        column for column in optional_columns if column in predictions.columns
    ]
    errors = predictions.loc[
        predictions["label"] != predictions["prediction"], selected_columns
    ].copy()
    return errors.rename(
        columns={
            "filename": "File",
            "label": "Actual",
            "prediction": "Predicted",
            "probability_normal": "P(Normal)",
            "probability_side_i": "P(Side I)",
            "probability_side_ii": "P(Side II)",
            "confidence": "Confidence",
            "confidence_margin": "Margin",
        }
    )

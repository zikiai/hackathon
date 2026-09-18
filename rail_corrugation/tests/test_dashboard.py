import pandas as pd
import pytest

from rail_cdm.dashboard import confusion_matrix_frame, per_class_metrics, validation_errors


@pytest.fixture
def metrics() -> dict:
    return {
        "classification_report": {
            "Normal": {"precision": 0.9, "recall": 0.8, "f1-score": 0.85, "support": 10.0},
            "Side I": {"precision": 0.5, "recall": 0.4, "f1-score": 0.44, "support": 2.0},
        },
        "confusion_matrix_labels": ["Normal", "Side I"],
        "confusion_matrix": [[8, 2], [1, 1]],
    }


def test_per_class_metrics_is_chart_ready(metrics: dict) -> None:
    result = per_class_metrics(metrics)

    assert result.to_dict("records") == [
        {"Class": "Normal", "Precision": 0.9, "Recall": 0.8, "F1": 0.85, "Files": 10},
        {"Class": "Side I", "Precision": 0.5, "Recall": 0.4, "F1": 0.44, "Files": 2},
    ]


def test_confusion_matrix_has_clear_axes(metrics: dict) -> None:
    result = confusion_matrix_frame(metrics)

    assert result.index.name == "Actual"
    assert result.columns.name == "Predicted"
    assert result.loc["Side I", "Normal"] == 1


def test_validation_errors_only_returns_mistakes() -> None:
    predictions = pd.DataFrame(
        {
            "filename": ["one.csv", "two.csv"],
            "label": ["Normal", "Side I"],
            "prediction": ["Normal", "Side II"],
        }
    )

    result = validation_errors(predictions)

    assert result.to_dict("records") == [
        {"File": "two.csv", "Actual": "Side I", "Predicted": "Side II"}
    ]


def test_validation_errors_keeps_probability_evidence() -> None:
    predictions = pd.DataFrame(
        {
            "filename": ["one.csv"],
            "label": ["Side I"],
            "prediction": ["Normal"],
            "probability_normal": [0.52],
            "probability_side_i": [0.45],
            "probability_side_ii": [0.03],
            "confidence": [0.52],
            "confidence_margin": [0.07],
        }
    )

    result = validation_errors(predictions)

    assert result.loc[0, "P(Side I)"] == 0.45
    assert result.loc[0, "Margin"] == 0.07

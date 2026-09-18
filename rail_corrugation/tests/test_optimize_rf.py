import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedKFold

from rail_cdm.calibration import ProbabilityAdjustedClassifier
from rail_cdm.optimize_rf import load_training, out_of_fold_probabilities, paired_summary


def test_out_of_fold_probabilities_preserve_named_class_adjustment():
    # Regress the label encoding trap in cross_val_predict(predict_proba):
    # Side I must retain its multiplier when evaluating held-out recordings.
    x = pd.DataFrame({"value": range(18)})
    y = pd.Series(["Normal", "Side I", "Side II"] * 6)
    model = ProbabilityAdjustedClassifier(
        DummyClassifier(strategy="prior"), class_multipliers=(("Side I", 1.5),)
    )
    result = out_of_fold_probabilities(
        model, x, y, StratifiedKFold(3, shuffle=True, random_state=7), jobs=1
    )
    np.testing.assert_allclose(result, np.tile([2 / 7, 3 / 7, 2 / 7], (18, 1)))


def test_screen_requires_both_mean_gain_and_consistency():
    rows = []
    candidates = {
        "baseline": [0.80] * 5,
        "consistent": [0.82, 0.82, 0.82, 0.82, 0.80],
        "three_wins": [0.84, 0.84, 0.84, 0.79, 0.79],
        "tiny_gain": [0.801] * 5,
    }
    for name, scores in candidates.items():
        for seed, score in enumerate(scores):
            rows.append(
                {
                    "candidate": name,
                    "validation_seed": seed,
                    "forest_seed": 42,
                    "macro_f1": score,
                    "side_i_precision": 0.5,
                    "side_i_recall": 0.7,
                    "side_i_f1": 0.6,
                    "side_ii_f1": 0.8,
                }
            )
    summary = paired_summary(pd.DataFrame(rows)).set_index("candidate")
    assert summary.loc["consistent", "passes_screen"]
    assert not summary.loc["three_wins", "passes_screen"]
    assert not summary.loc["tiny_gain", "passes_screen"]


def test_training_inventory_cannot_silently_drop_recordings(tmp_path):
    features = tmp_path / "features.csv"
    labels = tmp_path / "labels.csv"
    pd.DataFrame({"filename": ["one.csv"], "signal": [1.0]}).to_csv(features, index=False)
    pd.DataFrame({"filename": ["one.csv", "two.csv"], "label": ["Normal", "Side I"]}).to_csv(
        labels, index=False
    )
    with pytest.raises(ValueError, match="exactly the same recordings"):
        load_training(features, labels)

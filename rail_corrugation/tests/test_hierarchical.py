import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from rail_cdm.hierarchical import HierarchicalFaultClassifier


def test_hierarchical_probabilities_form_three_class_distribution() -> None:
    x = pd.DataFrame(
        {
            "signal": [-3.0, -2.0, -1.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            "side": [0.0, 0.0, 0.0, -2.0, -1.0, 1.0, 2.0, 3.0],
        }
    )
    y = np.array(["Normal", "Normal", "Normal", "Side I", "Side I", "Side II", "Side II", "Side II"])
    model = HierarchicalFaultClassifier(
        fault_estimator=LogisticRegression(),
        side_estimator=LogisticRegression(),
    ).fit(x, y)

    probabilities = model.predict_proba(x)

    assert list(model.classes_) == ["Normal", "Side I", "Side II"]
    assert probabilities.shape == (len(x), 3)
    assert np.allclose(probabilities.sum(axis=1), 1.0)

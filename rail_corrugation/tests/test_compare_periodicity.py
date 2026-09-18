import numpy as np
import pandas as pd

from rail_cdm.features import SAMPLE_RATE_HZ, extract_periodicity_features


def test_periodicity_features_recover_a_known_vibration_frequency() -> None:
    rows = 1_000
    time = np.arange(rows) / SAMPLE_RATE_HZ
    vibration = np.sin(2 * np.pi * 100 * time)
    values = np.zeros((rows, 129), dtype=float)
    values[:, 1::2] = vibration[:, None]

    features = extract_periodicity_features(pd.DataFrame(values))

    assert len(features) == 30
    assert features["periodicity_side1_dominant_frequency_median"] == 100.0
    assert features["periodicity_side2_dominant_frequency_median"] == 100.0
    assert features["periodicity_dominant_frequency_side1_minus_side2"] == 0.0

import numpy as np
import pandas as pd

from rail_cdm.features import extract_cross_car_consensus_features


def test_cross_car_consensus_detects_consistent_side_one_strength() -> None:
    values = np.zeros((4, 129), dtype=float)
    sensor_values = values[:, 1:].reshape(4, 8, 8, 2)
    sensor_values[:, :, [0, 2, 4, 6], :] = 2.0
    sensor_values[:, :, [1, 3, 5, 7], :] = 1.0
    frame = pd.DataFrame(values)

    features = extract_cross_car_consensus_features(frame)

    assert len(features) == 24
    assert features["car_consensus_vibration_rms_difference_median"] > 0
    assert features["car_consensus_vibration_rms_difference_positive_fraction"] == 1.0

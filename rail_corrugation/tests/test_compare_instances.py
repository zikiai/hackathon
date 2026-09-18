import numpy as np
import pandas as pd

from rail_cdm.features import extract_car_feature_rows


def test_car_feature_rows_preserve_all_eight_cars() -> None:
    values = np.zeros((4, 129), dtype=float)
    sensor_values = values[:, 1:].reshape(4, 8, 8, 2)
    sensor_values[:, :, [0, 2, 4, 6], :] = 2.0
    sensor_values[:, :, [1, 3, 5, 7], :] = 1.0

    rows = extract_car_feature_rows(pd.DataFrame(values))

    assert len(rows) == 8
    assert len(rows[0]) == 41
    assert rows[0]["car_index"] == 1.0
    assert rows[7]["car_index"] == 8.0
    assert rows[0]["vibration_rms_side1_minus_side2"] > 0

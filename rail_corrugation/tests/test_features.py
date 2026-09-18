import numpy as np
import pandas as pd

from rail_cdm.features import extract_features
from rail_cdm.io import EXPECTED_COLUMNS, read_sensor_csv


def test_extract_features_from_expected_layout(tmp_path):
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(
        rng.normal(size=(10_000, EXPECTED_COLUMNS)),
        columns=["Rotating speed"] + [f"sensor_{number}" for number in range(128)],
    )
    path = tmp_path / "Train1.csv"
    frame.to_csv(path, index=False)

    features = extract_features(read_sensor_csv(path))

    assert "side1_vibration_rms_mean" in features
    assert "side2_shock_band_100_250hz_mean" in features
    assert "vibration_rms_mean_side1_over_side2" in features
    assert all(np.isfinite(value) for value in features.values())


def test_loader_rejects_wrong_number_of_columns(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"a": [1], "b": [2]}).to_csv(path, index=False)

    try:
        read_sensor_csv(path)
    except ValueError as exc:
        assert "129 columns" in str(exc)
    else:
        raise AssertionError("Expected an invalid layout to be rejected")

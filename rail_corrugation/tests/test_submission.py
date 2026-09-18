from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from rail_cdm.io import read_sensor_csv
from rail_cdm.predict import validate_prediction_output


@pytest.mark.parametrize("rows", [1, 9999, 10001])
def test_loader_rejects_wrong_recording_duration(rows):
    source = BytesIO(pd.DataFrame(np.zeros((rows, 129))).to_csv(index=False).encode())
    with pytest.raises(ValueError, match="10,000 readings"):
        read_sensor_csv(source)


@pytest.mark.parametrize(
    "filenames,expected,match",
    [
        (["one.csv"], ["one.csv", "two.csv"], "failed validation"),
        (["one.csv", "one.csv"], ["one.csv", "one.csv"], "Duplicate filenames"),
        (["wrong.csv"], ["one.csv"], "failed validation"),
    ],
)
def test_official_export_rejects_incomplete_or_duplicate_batch(filenames, expected, match):
    frame = pd.DataFrame({"file_id": filenames, "prediction": ["Normal"] * len(filenames)})
    with pytest.raises(ValueError, match=match):
        validate_prediction_output(frame, expected)


def test_official_export_accepts_complete_batch():
    frame = pd.DataFrame({"file_id": ["one.csv", "two.csv"], "prediction": ["Normal", "Side I"]})
    validate_prediction_output(frame, ["two.csv", "one.csv"])


class DemoModel:
    classes_ = np.array(["Normal", "Side I", "Side II"])

    def predict(self, x):
        return np.array(["Normal"] * len(x))

    def predict_proba(self, x):
        return np.tile([0.8, 0.1, 0.1], (len(x), 1))


@pytest.mark.parametrize(
    "bad_file,duplicate,download_count", [(False, False, 1), (True, False, 0), (False, True, 0)]
)
def test_app_download_requires_every_uploaded_file(bad_file, duplicate, download_count):
    def uploads(*args, **kwargs):
        good = BytesIO(pd.DataFrame(np.random.default_rng(42).normal(size=(10000, 129))).to_csv(index=False).encode())
        good.name = "recording.csv"
        items = [good]
        if bad_file:
            bad = BytesIO(b"wrong,column\n1,2\n")
            bad.name = "bad.csv"
            items.append(bad)
        if duplicate:
            other = BytesIO(good.getvalue())
            other.name = good.name
            items.append(other)
        return items

    app_file = Path(__file__).resolve().parents[1] / "app.py"
    # Allow the UI test to run without a committed model artifact.
    real_exists = Path.exists

    def exists(path):
        return True if path.name == "rail_model.joblib" else real_exists(path)

    bundle = {"model": DemoModel(), "feature_columns": ["side1_vibration_rms_mean"]}
    with (
        patch("streamlit.file_uploader", side_effect=uploads),
        patch("joblib.load", return_value=bundle),
        patch.object(Path, "exists", exists),
    ):
        app = AppTest.from_file(str(app_file)).run(timeout=30)
    assert len(app.exception) == 0
    assert len(app.get("download_button")) == download_count
    if bad_file:
        assert len(app.error) >= 1
    if bad_file or duplicate:
        assert len(app.warning) >= 1

import pandas as pd

from rail_cdm.audit_shift import feature_shift_table


def test_identical_feature_distributions_have_no_shift() -> None:
    training = pd.DataFrame({"signal": [1.0, 2.0, 3.0, 4.0]})
    test = training.copy()

    result = feature_shift_table(training, test, ["signal"]).iloc[0]

    assert result["ks_statistic"] == 0.0
    assert result["standardized_mean_shift"] == 0.0

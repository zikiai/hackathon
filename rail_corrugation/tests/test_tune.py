import pandas as pd
from sklearn.feature_selection import SelectKBest

from rail_cdm.tune import make_candidate_model, stage_candidates, summarize_results


def test_tree_count_stage_keeps_other_settings_fixed() -> None:
    candidates = stage_candidates("tree-count")

    assert list(candidates) == ["200_trees", "500_trees", "1000_trees"]
    assert [parameters["n_estimators"] for parameters in candidates.values()] == [200, 500, 1000]


def test_tree_shape_stage_changes_one_control_at_a_time() -> None:
    candidates = stage_candidates("tree-shape")

    assert candidates["baseline_unlimited"] == {}
    assert candidates["max_depth_10"] == {"max_depth": 10}
    assert candidates["min_leaf_3"] == {"min_samples_leaf": 3}
    assert candidates["min_split_8"] == {"min_samples_split": 8}


def test_max_features_stage_carries_forward_provisional_split_size() -> None:
    candidates = stage_candidates("max-features")

    assert candidates["sqrt_features"] == {
        "min_samples_split": 4,
        "max_features": "sqrt",
    }
    assert candidates["50pct_features"] == {
        "min_samples_split": 4,
        "max_features": 0.50,
    }


def test_class_imbalance_stage_keeps_resampling_inside_validation() -> None:
    candidates = stage_candidates("class-imbalance")

    assert candidates["balanced_weights"]["class_weight"] == "balanced"
    assert candidates["random_over_48"]["sampling_target"] == 48
    assert candidates["smote_2_neighbors"]["smote_neighbors"] == 2
    assert candidates["balanced_random_forest"]["sampling"] == "balanced_random_forest"


def test_smote_calibration_changes_only_decision_multiplier() -> None:
    candidates = stage_candidates("smote-calibration")

    assert candidates["side_i_multiplier_1"]["side_i_multiplier"] == 1.0
    assert candidates["side_i_multiplier_1.5"]["side_i_multiplier"] == 1.5
    assert all(parameters["sampling"] == "smote" for parameters in candidates.values())
    assert all(parameters["sampling_target"] == 48 for parameters in candidates.values())


def test_feature_selection_stage_keeps_selection_inside_validation_pipeline() -> None:
    candidates = stage_candidates("feature-selection")
    parameters = candidates["top_60_features"]
    model = make_candidate_model(parameters)

    assert list(candidates) == [
        "top_30_features",
        "top_60_features",
        "top_100_features",
        "all_features",
    ]
    assert isinstance(model.named_steps["feature_selector"], SelectKBest)
    assert model.named_steps["feature_selector"].k == 60
    assert model.named_steps["sampler"].sampling_strategy == {"Side I": 48, "Side II": 48}


def test_hierarchical_stage_compares_side_specialists() -> None:
    candidates = stage_candidates("hierarchical-model")

    assert candidates["hierarchical_rf_side_10"]["side_feature_count"] == 10
    assert candidates["hierarchical_logistic_side_20"]["side_model"] == "logistic_regression"
    assert candidates["hierarchical_rf_side_20_adjusted"]["side_i_multiplier"] == 1.5


def test_summary_orders_candidates_by_average_macro_f1() -> None:
    results = pd.DataFrame(
        {
            "candidate": ["lower", "lower", "higher", "higher"],
            "macro_f1": [0.7, 0.72, 0.8, 0.82],
            "accuracy": [0.8, 0.8, 0.8, 0.8],
            "normal_f1": [0.8, 0.8, 0.8, 0.8],
            "side_i_precision": [0.5, 0.5, 0.5, 0.5],
            "side_i_recall": [0.5, 0.5, 0.5, 0.5],
            "side_i_f1": [0.5, 0.5, 0.5, 0.5],
            "side_ii_recall": [0.7, 0.7, 0.7, 0.7],
            "side_ii_f1": [0.7, 0.7, 0.7, 0.7],
            "training_seconds": [1.0, 1.1, 2.0, 2.1],
        }
    )

    summary = summarize_results(results)

    assert summary.iloc[0]["candidate"] == "higher"
    assert summary.iloc[0]["macro_f1_mean"] == 0.81

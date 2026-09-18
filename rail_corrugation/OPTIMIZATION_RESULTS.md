# Rail Random Forest optimization — 19 September 2026

## Decision

Retain the active 30-feature Random Forest. None of 19 tested variants improves its average macro F1 across the five required validation arrangements. The active model, validation artifacts, and official prediction CSV remain unchanged.

## Validation

- 272 complete labelled recordings; one recording is the split unit.
- Stratified five-fold validation with seeds 7, 19, 42, 73, and 101.
- Forest and SMOTE random seeds fixed at 42; 500 trees.
- Imputation, selection, optional scaling, and SMOTE fitted only on each training fold.
- Baseline reproduces all five previously recorded scores to numerical precision.
- Screening rule: more than 0.01 mean macro F1 gain and wins in at least four of five arrangements. No candidate passed; no model was promoted.
- Repeated validation reuses the same small dataset and has informed prior model choices. These are development scores, not independent estimates of hidden-test performance.

## Results

The first pass tested nearby feature counts, SMOTE distance scaling, entropy splits, feature subsampling, and smaller bootstrap samples. The second tested modest sampling, decision-adjustment, and tree-size changes using the selected features. The earlier tuning of these settings predated the 30-feature pipeline.

| Candidate | Mean macro F1 | Change (percentage points) | Wins / 5 | Side I precision | Side I recall |
|---|---:|---:|---:|---:|---:|
| baseline | 0.822854 | +0.000 | 0 | 0.5276 | 0.7286 |
| smote_target_32 | 0.821113 | -0.174 | 3 | 0.5460 | 0.7000 |
| entropy_splits | 0.820768 | -0.209 | 2 | 0.5367 | 0.7143 |
| max_depth_6 | 0.817362 | -0.549 | 0 | 0.5106 | 0.7286 |
| bootstrap_75pct | 0.817362 | -0.549 | 0 | 0.5106 | 0.7286 |
| features_40 | 0.816349 | -0.650 | 1 | 0.5112 | 0.7000 |
| min_leaf_2 | 0.816112 | -0.674 | 0 | 0.5122 | 0.7143 |
| smote_target_64 | 0.814831 | -0.802 | 2 | 0.5137 | 0.7286 |
| min_split_8 | 0.814654 | -0.820 | 0 | 0.5053 | 0.7143 |
| robust_scaled_smote | 0.814465 | -0.839 | 1 | 0.5106 | 0.7286 |
| features_20 | 0.814300 | -0.855 | 2 | 0.5396 | 0.7000 |
| side_i_multiplier_1_75 | 0.813235 | -0.962 | 0 | 0.4995 | 0.7286 |
| min_split_2 | 0.813144 | -0.971 | 0 | 0.5048 | 0.7143 |
| smote_neighbors_3 | 0.811789 | -1.106 | 3 | 0.5094 | 0.7143 |
| features_25 | 0.810276 | -1.258 | 2 | 0.5011 | 0.7143 |
| features_35 | 0.809183 | -1.367 | 0 | 0.5011 | 0.7000 |
| smote_neighbors_1 | 0.806312 | -1.654 | 0 | 0.4947 | 0.7000 |
| side_i_multiplier_1_3 | 0.804742 | -1.811 | 0 | 0.5061 | 0.6571 |
| features_per_split_25pct | 0.799590 | -2.326 | 0 | 0.4952 | 0.6714 |
| standard_scaled_smote | 0.796237 | -2.662 | 0 | 0.4746 | 0.7000 |

The closest variant, SMOTE target 32, reduces mean macro F1 from 0.822854 to 0.821113 and Side I recall from 0.728571 to 0.700000. Its seed-42 score falls to 0.781195 from 0.823353. This does not justify promotion.

## Baseline reproduction

| Validation seed | Macro F1 |
|---|---:|
| 7 | 0.808885 |
| 19 | 0.860872 |
| 42 | 0.823353 |
| 73 | 0.818234 |
| 101 | 0.802927 |

Fixed dashboard macro F1 remains **0.823353**. Repeated mean macro F1 remains **0.822854**. The 68-row official CSV remains 58 Normal, 6 Side I, and 4 Side II.

## Evaluation safeguard

The experiment runner uses explicit fold fitting and aligns probabilities by class name. An initial runner using `cross_val_predict(method="predict_proba")` encoded class labels as integers, bypassing the wrapper’s named Side I multiplier. That run failed baseline reproduction, was discarded, and is excluded from every table above. A regression test now verifies that held-out probabilities retain the named adjustment. This issue was in the new research runner; the active training code already fits folds explicitly.

## Reproduce

Run from the rail_corrugation workspace after activating its environment:

```bash
python -m rail_cdm.optimize_rf \
  --features data/processed/rail_features.csv \
  --labels data/raw/rail/Train_Labels.csv \
  --output-dir outputs/rf_refinement
```

The command evaluates the baseline plus 19 variants and saves paired summaries, individual arrangement scores, out-of-fold predictions, and a settings manifest. It never replaces active model artifacts. Use `--candidates` to limit the run, or `--forest-seeds` and `--validation-seeds` for explicit sensitivity checks.

The active selected measurements did not change, so the existing train/test distribution audit still applies. No hidden test labels or test-feature comparisons were used to select candidates.

## Scope of the conclusion

This bounded search found no better configuration; it does not establish a global optimum. Further broad tuning risks fitting the repeated validation choices. A materially different feature hypothesis or more labelled faults would provide stronger grounds for another round. Physical order tracking remains deferred until the rotating-speed unit is confirmed.

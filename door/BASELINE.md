# Door baseline: training and validation

From the repository root:

```bash
python3 -m pip install -r door/requirements-baseline.txt
python3 door/src/train_baseline.py
```

Only `door/data/raw/Train.csv` and `Train_Segments_Answer.csv` are read.
There is no test-data inference command in this script.

## What it does

1. Checks timestamp order and labelled row counts.
2. Splits the 110 complete movements into five consecutive validation blocks.
3. For each block, learns from the other four blocks, including any feature/model fitting.
4. Detects validation movements from timestamp gaps without their individual answer boundaries.
   The gap threshold is ten times the median within-movement sample interval from the training folds.
5. Compares a learned single mean-current threshold with a fixed small Random Forest.
6. Evaluates complete predicted segments using same-label, highest-IoU-first greedy matching
   and the organiser's IoU-weighted F1 formula. Small synthetic checks cover perfect matches,
   wrong labels, duplicate predictions, partial overlaps, and missed movements.
7. Saves a Random Forest trained on all labelled training movements after validation.

Features describe duration, current, electrical energy proxy, position direction and speed,
plus early/middle/late current, power and back-EMF. Direction comes from position, not the
answer file's operation column. Speed uses a five-reading median-smoothed position signal;
its units are native position units per second. Voltage-current products use the documented
mA and 10 mV conversions. Switch flags and controller opening/closing time fields are audited
but not included as classifier inputs in this first baseline.

## Outputs

`door/outputs/baseline/` contains fold scores, metrics, boundary/flag audit, out-of-fold
predictions, descriptive feature importances and the feature table. Validation CSVs are
for development, not official submission files. Confusion matrices use Normal, Abnormal
resistance order for both true rows and predicted columns.

`door/artifacts/door_baseline.joblib` holds the model and feature contract. Keep the matching
source code and dependency versions with the model. Only load trusted joblib files.

## Practical limits

These are exploratory results: all training examples were previously visualised. The blocked
validation checks disjoint movements, but it uses later as well as earlier training blocks;
it does not establish prospective forecasting performance. No door identifiers are supplied,
so this does not validate unseen-door generalisation. Unknown recording provenance or near-
duplicate movements can make results optimistic. The timestamp-gap detector depends on
this dataset's recording format and is not yet suitable for a gap-free live telemetry feed.
Feature importances describe model usage, not causal evidence. No obstruction type is labelled.

Before further tuning, inspect errors and check near-duplicate/provenance risks. Build the app
around the same feature and detection functions once the baseline is understood.

## First run results

| Model | Pooled IoU-weighted F1 | Missed abnormal movements | False alarms |
|---|---:|---:|---:|
| Learned mean-current threshold | 0.8909 | 12 / 30 | 0 / 80 |
| Random Forest | 0.9909 | 1 / 30 | 0 / 80 |

Boundary-only F1 was 1.0 in each of the five blocks. Random Forest fold scores were
1.0, 1.0, 1.0, 0.9545, 1.0. The missed abnormal movement was `train_seg_081`.
No exact duplicate feature rows were found; this does not rule out near-duplicate
signals or common recording provenance. Middle current, middle power, and energy
were the top mean fold impurity importances, which can be affected by correlated features.

Within-movement timestamp gaps were all 0.02 seconds; between-movement gaps were
10.215–58.823 seconds. Opening/closing flags changed at only 52 of 109 boundaries.
Each close/lock switch also changed inside all 110 movements, so switch changes are
not equivalent to movement boundaries. These observations support the gap-based
baseline for this data format, not a universal segmentation algorithm.

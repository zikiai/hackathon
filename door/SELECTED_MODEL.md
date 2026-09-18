# Selected Door model

Use `src/selected_model.py` and `artifacts/door_selected.joblib` for the current selected
pipeline. `train_baseline.py` and `door_baseline.joblib` remain historical baseline references.

## Why this candidate

The current-pattern Random Forest plus position-inferred direction is tied for the best
IoU-weighted F1 in all three training validation designs and uses only seven features.
It is selected for classification performance and simplicity, not because its uncalibrated
probability estimates dominate: normal-reference features had better Brier scores in the
forward and similarity-purged checks. Selection does not use test predictions.

| Training evaluation | IoU-weighted F1 | Missed abnormal | False alarms |
|---|---:|---:|---:|
| Five chronological blocks, 110 movements | 1.0000 | 0 | 0 |
| Earlier-to-later, 66 movements | 1.0000 | 0 | 0 |
| Similar-curve exclusion, 110 movements | 1.0000 | 0 | 0 |

These are exploratory results on reused training examples, not guaranteed test or deployment
performance. No claim that this is uniquely or universally the best model is warranted.

## Features and settings

Mean absolute current, peak absolute current, current standard deviation, mean absolute
current in each elapsed-time third, and direction from net position change. Current is
converted from mA to A. There are no fixed position bins or power/EMF classifier inputs.

Random Forest: 200 trees, depth at most 4, minimum leaf size 3, balanced class weights,
seed 42. Decision threshold 0.5. The movement detector separates readings at gaps greater
than 0.2 seconds for the supplied 0.02-second sampling. It assumes the supplied recording
format; it is not validated for continuous idle telemetry or missing packets.

## Commands

From the repository root:

```bash
python3 -m pip install -r door/requirements-baseline.txt
python3 door/src/selected_model.py train
python3 door/src/selected_model.py predict --input PATH_TO_INPUT.csv --output PATH_TO_OUTPUT.csv
```

The predict command defaults to `door/artifacts/door_selected.joblib`. It emits only
`start_time,end_time,prediction` using original timestamps. Input must be explicitly supplied.
Training reads only the two training CSVs and saves a model plus a verification JSON.
App integration should call `predict_frame(frame, bundle)` from the same module. The organiser
requires final submission predictions to be generated through the app; the CLI alone does not
fulfil that app requirement.

## Verification

Feature values exactly match the previously audited current-only candidate for all 110
training movements. Save/load prediction parity passes. The actual prediction function
achieves 1.0 in each of the five held-out blocks. Empty data, malformed timestamps and duplicate
timestamps are rejected. The audit model settings were unchanged. No test data was read for
this promotion. Old models and prior predictions were preserved.

The function checks structural validity but does not provide a calibrated confidence or an
unfamiliar-input flag. A Normal prediction does not rule out operating conditions outside
training experience. Keep that limitation visible when integrating the app.

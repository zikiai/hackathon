# Training-only robustness audit

## Run

From the repository root, install both existing baseline and plot requirements, then:

```bash
python3 -m pip install -r door/requirements-baseline.txt -r door/requirements-plots.txt
python3 door/src/audit_robustness.py
python3 door/src/plot_audit.py
```

Results appear in `door/outputs/robustness/`. Neither script accesses test data.
The existing saved baseline model is not replaced by this audit.

## Fixed comparisons

All six variants use the same Random Forest settings: 200 trees, maximum depth 4,
minimum leaf size 3, balanced class weights and seed 42. No tuning search was run.

- **Current only:** current summaries by elapsed-time thirds, plus position-inferred direction.
  This is not a single mean-current threshold.
- **Current + position:** current summaries, direction, displacement, speed and duration.
- **Baseline:** original full electrical and movement feature set.
- **Baseline without EMF:** removes the three back-EMF summaries.
- **Position augmented:** baseline plus current, power and speed in five fixed absolute-position
  bins (35–665 native units), stationary current/fraction and reverse-motion fraction.
- **Normal reference:** position-augmented features plus positive current/power deviations
  from same-direction normal median bin values. Reference medians are learned only from
  normal movements in each training fold. Stationary endpoints are handled separately.

Missing values are imputed using training-fold medians only. The position scale assumption
is specific to the supplied training data and must not be assumed universal across doors.

## Validation designs

1. **Blocked:** five consecutive blocks of 22 movements; hold out one, train on the other four.
2. **Forward:** train on first 44, 66 or 88 movements and validate on the next 22. Each of the
   final 66 movements is evaluated once. This is prospective ordering within this recording,
   not proof of future fleet performance.
3. **Similarity-purged:** same five held-out blocks, but remove training movements in connected
   waveform-similarity groups represented in validation. Training sizes become 43, 37, 54,
   46 and 40. This is an intentionally strict diagnostic stress test, not known source grouping.

Every evaluation runs the gap detector on its held-out stream; all detected boundaries matched
exactly. Classification diagnostics explicitly assert this correspondence. Official-style
same-label IoU matching is still used for the reported score.

## Similarity audit

Curves are resampled to 101 elapsed-time points. Distance is RMS difference across current,
voltage, EMF and position, divided by fixed scales 2500 mA, 10000 logged voltage units,
2500 logged EMF units and 700 position units. Only same-direction curves are compared.
Pairs below 0.01 distance are linked and transitive connected groups are kept out of training.
This threshold is an exploratory convention, not a statistical proof of duplicate source data.
Validation waveforms participate only in defining the stress-test split, not feature fitting.

There were no exact aligned duplicates, but 433 close pairs and a largest connected group
of 32 movements. Similar physical movements naturally resemble one another; this does not
establish duplication or synthetic generation. See `nearest_waveforms.csv` and `similarity_groups.csv`.

## Results

| Features | Blocked IoU F1 (110) | Forward IoU F1 (66) | Similarity-purged IoU F1 (110) |
|---|---:|---:|---:|
| Current only + direction | 1.0000 | 1.0000 | 1.0000 |
| Current + position | 1.0000 | 1.0000 | 1.0000 |
| Original baseline | 0.9909 | 1.0000 | 1.0000 |
| Baseline without EMF | 0.9909 | 1.0000 | 1.0000 |
| Position augmented | 0.9909 | 0.9848 | 0.9909 |
| Normal reference | 1.0000 | 1.0000 | 1.0000 |

All observed mistakes were missed abnormalities; no false alarms occurred. These are small,
previously explored samples. Zero observed errors is not a guarantee of zero deployment errors.
Compare feature sets within a validation design: the forward design covers a different subset.

The Brier score measures squared probability error, lower being better. Normal-reference
features scored 0.00427, 0.00380 and 0.00797 across blocked, forward and purged designs.
Current-only features scored 0.00386, 0.00718 and 0.02012. Thus the reference approach showed
more stable probability estimates in the two stress tests, but was not best in every design.
Brier scores do not by themselves establish calibration.

## The ambiguous movement

Every error involved `train_seg_081`, an abnormal opening. In blocked validation its abnormal
probability was 0.4903 with the original baseline, 0.5828 with current-only features,
0.4504 with position-augmented features and 0.5979 with normal-reference features.
These are uncalibrated model outputs, not true fault probabilities. The model disagreement
identifies a borderline example rather than establishing a general uncertainty cutoff.

`movement_081_position.png` compares its current/power curves with normal opening references
from original fold-4 training movements only. `movement_consistency.csv`, `errors.csv` and
`validation_predictions.csv` preserve all outcomes. Distances from training examples are
included as exploratory diagnostics; they are not a validated out-of-distribution detector.

## Decision

Keep current-pattern + direction as the simple challenger and normal-reference features as
the richer challenger. More features did not consistently improve results; back-EMF added
no observed classification advantage in this comparison. Do not tune a custom threshold
around movement 081 or replace the saved baseline solely to reach a perfect exploratory score.
The next practical step is to freeze candidates and integrate the reproducible pipeline into
the app, preserving uncertainty information for review without changing required labels.

All training data has been inspected, so none of these evaluations is an untouched final
holdout. Source/door identifiers and fault-cause labels are absent. Performance outside this
recording format remains unknown, particularly segmentation in gap-free telemetry.

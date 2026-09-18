# Unlabelled test comparison — fixed training models

User authorised test access after the training-only robustness audit. No settings, decision
thresholds or feature definitions were tuned using test data. Models and normal references
were fitted on all labelled training movements using the previously specified settings.
The saved baseline was not replaced. Outputs are diagnostic candidate predictions, not an
app-generated competition submission.

## Reproduce

From the repository root, using the baseline and plotting requirements already provided:

```bash
python3 door/src/compare_unlabelled.py --input /Users/maahipatangiya/Downloads/Test.csv
```

The input path is explicit; the script does not search for test files. Results are saved in
`door/outputs/test_comparison/`. Training inputs remain in `door/data/raw/`.

## Findings

- Training: 18,036 readings, 110 labelled movements.
- Test: 6,253 readings, 38 detected movements, no missing cells, matching column schema.
- Test direction inferred from position: 18 openings, 20 closings.
- Within detected movements: 0.02-second sampling, matching training.
- Between detected movements: gaps of 11.110–55.356 seconds. Fixed detector threshold 0.2 s.
- Original baseline, current-pattern candidate, and normal-reference candidate agree on every
  test movement: 30 Normal and 8 Abnormal resistance. These are predictions, not known labels.
- No exact cross-set matches under the 101-point aligned waveform comparison.
- Median nearest-training waveform distance is 0.0152 for test versus 0.00646 for training
  leave-one-out neighbours. The test maximum is 0.1988 versus the training maximum 0.05098.
  Distances use the same fixed signal scales and same-direction restriction as the audit.
  They are descriptive, not calibrated distribution-shift probabilities.

## Notable unfamiliar movement

`test_detected_033`, from `2023-7-5-0-20-55-731` to `2023-7-5-0-20-59-411`, is the only
movement whose nearest-waveform distance exceeds the training leave-one-out maximum.
Its position increases, so the pipeline infers opening. Duration is 3.68 seconds compared
with training openings 2.72–2.92 seconds; position change is 807 compared with 695–705.
All three candidates predict Normal, with abnormal scores 0.0880, 0.0843 and 0.0243.
Those scores are uncalibrated, and agreement does not resolve the unfamiliarity.
Do not relabel or tune around this example without independent evidence.

Some other features also extend beyond training ranges: five closings are shorter than the
training closing minimum, and several back-EMF summaries exceed prior ranges. Most test
movements nevertheless have close waveform neighbours under the chosen distance measure.
Differences can reflect class mixture, operating conditions, measurement shifts or other
unknown factors; cause cannot be identified from the available labels.

Both files start at the same timestamp. Timestamp overlap does not establish shared source
recordings, duplicated movements, or a real chronological relationship between the files.

## Interpretation

The schema and sampling match; distributions are broadly overlapping but not identical.
Use the fixed candidates as-is and preserve a separate unfamiliar-input indicator for review.
Do not choose a model because it agrees with other test predictions. Without answers we
cannot calculate test IoU-weighted F1, accuracy, recall, false alarms or validate the boundaries.

See `candidate_predictions.csv`, `feature_ranges.csv`, `comparison.json` and
`train_test_distributions.png`. The JSON records the input SHA-256 for reproducibility.

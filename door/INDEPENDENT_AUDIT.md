# Independent re-audit of the train/test comparison

## What the comparison means

Training (110 labelled movements) and test (38 detected, unlabelled movements) are two samples.
Neither is established as a subset of the other or as the full population of possible doors.
The useful question is whether test inputs are covered by training experience in signal and
movement characteristics. Timestamps do not establish membership or chronological provenance.
Unknown test labels prevent assessment of class-conditional coverage and predictive correctness.

## Verification performed

- Read the loader, feature extraction, segmentation, validation and comparison implementation.
- Re-ran `compare_unlabelled.py` with unchanged settings. All candidate output values reproduced
  exactly against the previous CSV. No model was chosen or tuned from this comparison.
- Loaded the existing saved baseline independently: all 38 labels match the newly fitted
  baseline; maximum floating-point score difference was 1.11e-16.
- Used a separate datetime parser and segmentation implementation to inspect original files.
  All 110 training groups match answer start/end timestamps and row counts exactly.
- Test has 38 gap-separated groups and all 6,253 readings are accounted for. Numeric values
  are finite. This checks internal consistency, not hidden ground-truth boundaries.
- Compared full original sensor sequences (timestamps excluded): no exact cross-set movement
  matches. This is stronger than the earlier resampled-curve check, but does not exclude related
  source recordings, near-duplicates, common templates or common operating conditions.
- Rechecked the documented mA and 10 mV conversions: the V*I and trapezoidal energy calculations
  are consistent with those units. They remain logged electrical proxies, not mechanical work.
- Examined movement 33 row by row and plotted it against all 40 normal training openings in
  actual elapsed seconds, avoiding the earlier duration-normalisation effect.

## Leakage and evaluation

No direct test-to-training fitting leakage was found in the comparison code: feature columns
are fixed; medians, normal references and forest fitting use training only; test predictions do
not supply labels to any fitting step. Same settings and 0.5 decision threshold were retained.

This does NOT make the earlier validation scores an untouched performance estimate. All
training examples were plotted, features were subsequently chosen and six feature sets compared
on reused folds. This is exploratory model development with selection optimism risk. Time blocks
and similarity exclusion are useful stress tests, not independent external validation. The
forward test covers 66 movements from the same recording, not a new door or deployment.

The similarity-purged split intentionally uses unlabelled held-out waveforms to define groups.
That does not fit the classifier on held-out data, but its threshold/scales are heuristic and
cannot establish true source independence. There is no verified source/door identity grouping.

Three candidate models agree on 30 Normal and 8 Abnormal resistance predictions. All three are
Random Forests sharing training records and overlapping features. Their errors can be correlated;
this agreement is not three independent confirmations. Scores are uncalibrated classifier outputs.

## Movement 33: direct evidence

- Timestamp range: `2023-7-5-0-20-55-731` to `2023-7-5-0-20-59-411`.
- 185 readings at 0.02-second intervals; duration 3.68 seconds.
- Position rises monotonically from 0 to 807.
- Open command=1, close command=0, opening flag=1, closing flag=0 throughout.
- Final reading has Door Opened=1. Thus opening inference is corroborated by control telemetry.
- Gaps before/after are 30.731 and 26.093 seconds. No internal sampling break is present.
  This supports treating it as one captured opening; hidden annotation correctness remains unknown.
- Every training opening lasts 2.72–2.92 seconds and ends at 695–705.
- Movement 33 first passes position 705 at 2.16 seconds. 41.6% of its readings are above 705;
  zero training opening readings are above that position.
- The plotted initial current profile resembles normal openings; later it continues moving
  past their endpoint, with the terminal current rise occurring later. This is descriptive,
  not a physical diagnosis.

## Important feature assumptions exposed

1. **Fixed position-bin coverage.** `position_features` in `audit_robustness.py` uses positions
   35–665. For movement 33 those bins cover only 38.4% of readings, versus 57.6–60.6% for
   training openings. The whole extended portion above 705 is absent from the added bin/reference
   measurements. Baseline duration, displacement and electrical summaries still include it;
   the entire pipeline is not blind to the tail. But calling the reference comparison coverage
   of the whole movement would be wrong. Absolute position scale transfer is unvalidated.
2. **Time-normalised phase.** Early/middle/late features use thirds of total duration, and the
   waveform distance resamples each movement to 0–100% elapsed time. A longer movement shifts
   which physical actions land in each third. Distance 0.1988 therefore combines shape, timing
   and endpoint differences; it is not a calibrated fault or novelty probability.
3. **One-sided reference deviations.** Reference features retain positive current/power excess
   only. They are designed to highlight extra electrical effort, not every kind of unusual
   movement or sensor behaviour. Absence of excess is not evidence of mechanical health.
4. **Recording gaps.** The fixed 0.2-second detector matches the supplied training boundaries
   and captures test blocks cleanly, but assumes gaps represent movement boundaries. It has no
   verified behaviour for live streams with continuous idle telemetry, missing packets, or
   truncated movements. The result is an offline completed-movement detector, not a demonstrated
   real-time early fault warning system.
5. **Unknown physical units/provenance.** Back-EMF and position scaling are incompletely
   documented; speed remains native position units/second. A different physical travel length,
   controller setup, sensor scaling, or fault could explain an unfamiliar record. None is proven.

## Interpretation and decision

The evidence supports “unfamiliar opening with a Normal model prediction.” It does not establish
abnormal resistance, obstruction, healthy operation, bad data, or a different door.

Retain all fixed outputs. Do not relabel movement 33 or change bins, thresholds or model selection
in response to it. If the app adds a review indication, distinguish out-of-training-range
conditions from the official binary fault prediction. Its thresholds and usefulness would
require validation; the largest training neighbour distance is only a descriptive comparator.

The useful next external evidence would be organiser clarification about position units,
variation in door travel/controller settings, and whether labels cover resistance only.
Independent labelled recordings would be needed to assess unseen-door reliability. No hidden
answers should be sought or used for model development.

## Files and reproducibility

`independent_checks.json` records hashes and raw checks; `movement_33_raw_signals.png` shows the
movement. `independent_checks.py` performs no fitting and takes explicit input/output paths.
The code, saved models, raw data and existing predictions were not altered by the audit.

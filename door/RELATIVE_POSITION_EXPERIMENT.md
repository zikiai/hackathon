# Documentation check and relative-position experiment

The supplied Door Info Kit section 1.2 states that distributions differ among doors.
Section 2.1 describes test as the same format and built the same way. Neither statement
specifies that position scales or travel limits differ. The supplied header guide leaves
Door leaf position undescribed (a dash), with no unit or mandated 700 endpoint.
Different scaling or mechanical travel is a hypothesis, not a documented explanation of
movement 33. We have not established that the labelled training data is bad or skewed.
The limitations are narrow observed coverage, undocumented provenance and feature assumptions.

We tested five relative-position bins over 5–95% of signed start-to-end travel instead of
fixed positions 35–665. Current/power amplitude, raw displacement and actual duration remain
available. Normal references, imputation and fitting use training folds only. All 110 examples
are retained. Same Random Forest settings, split schedules and detector are reused through
`audit_robustness.py`; only the position feature function is substituted. No model artefacts
or prior predictions are replaced. The script defaults to a separate results folder.

This experiment was motivated after unlabelled-test inspection: it is a test-informed design
idea checked on reused training folds, not a new independent performance estimate. The run
itself reads only the two training files.

| Candidate | Blocked | Forward | Similarity-purged |
|---|---:|---:|---:|
| Existing current patterns + direction | 1.0000 | 1.0000 | 1.0000 |
| Relative-position augmentation | 0.9909 | 0.9848 | 0.9909 |
| Relative-position normal reference | 0.9909 | 1.0000 | 0.9818 |

The relative reference missed one abnormal in blocked validation and two in similarity-purged
validation; no false alarms. Under the same procedure the previous fixed-position normal
reference scored 1.0 on all three schemes. Normalisation does not consistently help on the
available data. Do not promote this experiment or discard difficult labelled examples.
Keep the current-pattern candidate as the simpler candidate supported by existing evidence.

Run from the repository root after installing existing baseline requirements:

```bash
python3 door/src/audit_relative_position.py
```

Results: `door/outputs/relative_position_audit/`. These remain exploratory scores and do not
establish performance on other doors, travel ranges, or gap-free recordings. Genuine wider
coverage requires additional correctly labelled examples, not pseudo-labels from test.

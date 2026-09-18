# NebulaX PS3 — Rail Corrugation Baseline

This repository is the team's shared starting point for the Rail Corrugation part of Problem Statement 3.

It turns each 10,000-row sensor recording into a small row of useful signal summaries, trains a feature-selected Random Forest, checks it with stratified cross-validation, predicts the test files, and creates the required `rail_predictions.csv`.

## What the model does

```text
Raw CSV recording
  -> validate its 129-column sensor layout
  -> calculate time- and frequency-domain features
  -> compare Side I with Side II
  -> select 30 measurements and apply moderate SMOTE
  -> Random Forest classifier with a fixed Side I adjustment
  -> Normal / Side I / Side II
```

The model is a conventional machine-learning classifier trained on the supplied labels. Gemini is not used to decide the rail condition.

## 1. First-time setup

Install Python 3.11 or newer, then run:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## 2. Add the supplied data

Do not commit the large organizer datasets to Git. Copy the Rail Corrugation folder into this layout:

```text
data/raw/rail/
├── Train/
│   ├── Train1.csv
│   └── ...
├── Test/
│   ├── Test1.csv
│   └── ...
└── Train_Labels.csv
```

## 3. Inspect the data

```bash
rail-inspect \
  --train-dir data/raw/rail/Train \
  --labels data/raw/rail/Train_Labels.csv
```

This checks file-label matching, prints the class counts, validates a sample CSV, and saves beginner-friendly plots in `outputs/inspection/`.

## 4. Train and validate

```bash
rail-train \
  --train-dir data/raw/rail/Train \
  --labels data/raw/rail/Train_Labels.csv \
  --artifact-dir artifacts
```

Training creates:

- `artifacts/rail_model.joblib` — fitted feature/model pipeline.
- `artifacts/cross_validation_predictions.csv` — honest validation predictions.
- `artifacts/metrics.json` — macro F1 and per-class results.
- `data/processed/rail_features.csv` — one feature row per recording.

The headline metric is macro F1. Always inspect the individual Side I and Side II scores too.

The fitted Random Forest first keeps the 30 strongest measurements inside each validation fold,
then uses moderate fold-safe SMOTE oversampling (Side I and Side II are each expanded to 48
training rows). It requires four samples before splitting a node and applies a fixed `1.5×`
multiplier to Side I probability before choosing the final class. Repeated five-fold validation
selected this configuration. More aggressive full balancing performed worse. The tested Welch,
robust-statistic, and short-window feature families were also rejected and are not used by the
final model.

Run one reproducible tuning stage at a time. For example, compare 200, 500, and 1,000 trees
across five shuffled five-fold validations with:

```bash
rail-tune \
  --features data/processed/rail_features.csv \
  --labels data/raw/rail/Train_Labels.csv \
  --stage tree-count
```

Detailed and averaged results are written under `outputs/tuning/`. Tuning does not replace the
active model automatically.

Check whether the selected measurements have a major train/test distribution shift without using
the hidden test answers:

```bash
rail-audit-shift \
  --train-features data/processed/rail_features.csv \
  --test-dir data/raw/rail/Test \
  --model artifacts/rail_model.joblib
```

An audit classifier AUC near `0.5` means it cannot reliably distinguish training files from test
files, which is reassuring but does not guarantee the hidden-label score.

## 5. Produce test predictions

```bash
rail-predict \
  --test-dir data/raw/rail/Test \
  --model artifacts/rail_model.joblib \
  --output outputs/rail_predictions.csv
```

The command validates that every prediction is exactly `Normal`, `Side I`, or `Side II`, and writes the required columns:

```csv
file_id,prediction
Test1.csv,Normal
Test2.csv,Side II
```

## 6. Run the app

```bash
streamlit run app.py
```

The app has two tabs:

- **Predict files** — upload Rail CSV files, view predictions and confidence, and download `rail_predictions.csv`.
- **Model performance** — see macro F1, ordinary accuracy, per-class precision/recall/F1, class imbalance, the confusion matrix, incorrect validation files, tuning experiments, and model comparisons.

The dashboard reads the files created by `rail-train` and `rail-compare`, so rerunning those commands automatically refreshes the displayed results. The same saved model is used by both the command line and the app.

## Team workflow

Read [`../docs/team-workflow.md`](../docs/team-workflow.md) before the first group coding session.

Short version:

1. Protect `main`; it should always run.
2. Each task gets a short branch such as `feature/speed-features`.
3. Pull requests must include the validation result before and after the change.
4. Never tune using the unlabeled Test folder.
5. Never commit datasets, trained models, API keys, or `.env` files.

## Project layout

```text
app.py                         Streamlit user interface
src/rail_cdm/dashboard.py      Dashboard data preparation
src/rail_cdm/io.py             Loading and validation
src/rail_cdm/features.py       Signal-to-feature conversion
src/rail_cdm/inspect_data.py   Dataset report and plots
src/rail_cdm/train.py          Cross-validation and final training
src/rail_cdm/predict.py        Required CSV generation
tests/                         Fast checks with synthetic data
docs/team-workflow.md          Four-person collaboration process
```

## Final model status

The active model is frozen at fixed five-fold macro F1 **0.823353**, repeated mean
macro F1 **0.822854**, and fixed-split Side I recall **78.6%**. The 68 test predictions
were reproduced exactly during the final readiness pass. Additional model complexity
was rejected when repeated validation did not support it. Rotating-speed units remain
unconfirmed, so physical order tracking is deferred.

The app rejects recordings that do not contain 10,000 rows and blocks batch download
if any upload fails or filenames are duplicated. Its side-comparison chart shows measured
vibration evidence, while adjusted class scores are explicitly labelled as model scores.

See [final readiness](FINAL_READINESS.md), [Cloud Run deployment](DEPLOYMENT.md), and
[demo script and write-up](../docs/rail-demo-and-writeup.md). Cloud configuration is prepared;
the container build and hosted URL still require verification in the assigned project.

## Random Forest refinement (19 September 2026)

A bounded comparison of 19 variants retained the active 30-feature model: none improved
its five-seed mean macro F1 of **0.822854**. See [results and reproduction steps](OPTIMIZATION_RESULTS.md).
The research runner is available as `python -m rail_cdm.optimize_rf`; it saves experiment
reports without replacing the active model or official predictions.

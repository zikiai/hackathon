# NebulaX PS3 team workflow

This document records the original team workflow. For the final architecture and selected models, see the [project README](../README.md).

- **Programming language:** use Python for all four prediction pipelines.
- **Machine-learning model:** the model trained on the supplied sensor files to produce the official predictions.

## 1. Shared technology choices

Keep the shared stack small:

| Need | Team choice |
|---|---|
| Programming | Python 3.11+ |
| Data handling | pandas, NumPy |
| Signal processing | SciPy |
| Machine learning | scikit-learn; add XGBoost only if validation shows a benefit |
| Experiment environment | Google Colab or Vertex AI Workbench |
| Source control | This GitHub repository with pull requests |
| UI prototype | Stitch |
| Working application | Streamlit first; deploy to Cloud Run |

Prediction generation uses the saved subsystem pipelines and has no language-model API dependency.

## 2. What is graded

Each attempted subsystem contributes up to 25% of the four-subsystem Overall Score.

| Subsystem | Required output | Official technical metric | What it rewards |
|---|---|---|---|
| Door | `door_predictions.csv` with `start_time,end_time,prediction` | IoU-weighted F1 | Correct cycle boundaries and correct Normal/Abnormal label, without missing or inventing cycles |
| ACV | `acv_predictions.csv` with `file_id,ranked_cars` | Linear rank-decay score | Putting the true faulty car as high as possible while ranking every car |
| Rail Corrugation | `rail_predictions.csv` with `file_id,prediction` | Macro F1 over Normal, Side I, and Side II | Performing well on both rare fault classes, not merely predicting Normal |
| SHM | `shm_predictions.csv` with `file_id,prediction` | `max(0, 1 - MAPE)` | Keeping percentage error small for every cumulative-damage prediction |

The organizers also report:

- **Overall Score:** sum across all four subsystems divided by four. A skipped subsystem contributes zero.
- **Average Score:** average across only the subsystems attempted, rewarding depth.
- **Per-subsystem leaderboards:** each model is also compared independently.

The broader judging rubric considers:

1. **Problem Fit:** coverage, predictive-maintenance usefulness, sound model comparison, explainability, UI, and code quality.
2. **Technical Execution:** held-out prediction performance using the official metrics.
3. **Ease of Use:** non-technical upload-to-result experience, clarity, and usefulness, judged through the app and demo video.

This means a leaderboard model without a working app is incomplete, while a beautiful app with weak or invalid predictions is also incomplete.

## 3. Four independent workstreams

### Member A — Door

**Workspace:** `door/`

**Problem:** first find each door-open/close cycle in one continuous stream, then classify it as `Normal` or `Abnormal resistance`.

**Recommended first approach:**

1. Detect candidate cycles using door position, commands, and movement state.
2. Extract cycle duration, peak/mean current, current area, stalls, position speed, voltage, and back-EMF features.
3. Train a class-weighted Random Forest, Extra Trees, or gradient-boosted classifier.
4. Score the complete segmentation-plus-classification pipeline with the official IoU-weighted F1 logic.

**Later experiments:** change-point detection, Hidden Markov Models, or a 1D CNN only after the rule/feature baseline works.

**Validation:** hold out contiguous groups of complete cycles or time blocks. Do not randomly split sensor rows.

**Gemini use:** help document the state machine, write tests for boundary cases, and review visualizations. It should not decide cycle labels in production.

### Member B — ACV

**Workspace:** `acv/`

**Problem:** identify and rank which of eight cars has a refrigerant leak. There are only six labelled cases, and files may have different columns.

**Recommended first approach:**

1. Parse each file's actual headers and group columns by car.
2. Compare every car with the median behavior of its seven peers.
3. Calculate temperature deviation, cooling response, trend, variability, mode-response mismatch, and persistence features.
4. Create a robust anomaly score and rank all eight cars.

**Candidate algorithms:** robust z-scores and weighted anomaly scoring first; Isolation Forest or a small regularized ranking/classification model as comparisons. Avoid a large neural network with six cases.

**Validation:** leave one complete case out, train/tune on the remaining five, and measure the official rank-decay score. Repeat for all six cases.

**Gemini use:** help interpret unfamiliar telemetry names, generate loader tests, and write a grounded explanation of calculated anomalies. Verify all domain interpretations against the info kit.

### Member C — Rail Corrugation

**Workspace:** `rail_corrugation/`

**Problem:** classify every one-second recording as `Normal`, `Side I`, or `Side II` from axle-box vibration and shock data.

**Recommended first approach:**

1. Extract time-domain features such as RMS, standard deviation, peaks, and kurtosis.
2. Extract FFT frequency-band energy.
3. Aggregate odd positions as Side I and even positions as Side II.
4. Add side differences and ratios.
5. Train a class-weighted Extra Trees model, then compare Random Forest and gradient boosting.

**Later experiments:** speed-normalized frequency/order features, cross-car agreement, better frequency bands, and feature selection. A 1D CNN is optional and high-risk because there are only 272 labelled files.

**Validation:** stratified five-fold cross-validation at file level. Track macro F1 and the individual Side I and Side II F1 scores.

**Gemini use:** explain signal-processing code, review feature definitions, generate test cases, and help interpret error groups. Do not use an LLM to classify the numeric signals.

### Member D — SHM

**Workspace:** `shm/`

**Problem:** predict one numeric cumulative-fatigue-damage value per dynamic-stress file.

**Recommended first approach:**

1. Extract stress ranges, RMS, percentiles, peaks, energy, and rainflow-cycle summaries.
2. Build a physics-informed baseline related to Miner's damage rule.
3. Compare regularized regression, Random Forest/Extra Trees regression, and gradient boosting.
4. Consider predicting log damage if it improves MAPE consistently.

**Later experiments:** tune S-N-inspired power features and blend the physics estimate with the best ML model.

**Validation:** repeated file-level K-fold validation. Report MAPE and the official `max(0, 1 - MAPE)` score. Pay special attention to small true values because percentage errors can become large.

**Gemini use:** help explain rainflow/Miners-rule code, create calculation tests, and improve the plain-language result explanation. Numerical results must come from the tested pipeline.

## 4. Common development stages

Every member follows the same gates even though the modelling differs.

### Gate 1 — Data contract

Produce a one-page note answering:

- What is one example?
- Where is its label?
- What must be predicted?
- What validation split prevents leakage?
- What is the official metric?
- What exact CSV must be generated?

### Gate 2 — Data audit

- Match every training file with exactly one label.
- Report shapes, types, missing values, and label distribution.
- Plot representative examples.
- Confirm that the test data is never used for model selection.

### Gate 3 — Reproducible baseline

- One command builds features and trains the model.
- Validation produces the official metric.
- One command produces the exact official CSV.
- Save the model and preprocessing together.

### Gate 4 — Evidence-led improvement

Maintain a shared experiment log:

| Date | Owner | Branch | Feature/model change | Validation design | Official score | Per-class/error detail | Decision |
|---|---|---|---|---|---:|---|---|

Change one major idea at a time. Keep an improvement only when it is reproducible across folds, not because it wins on one lucky split.

### Gate 5 — Integration-ready handoff

Each owner provides:

- A prediction function or command that works without a notebook.
- A saved model plus preprocessing/version information.
- Input validation and readable failures.
- A small synthetic fixture for integration tests.
- The exact official CSV.
- A short explanation of safe UI outputs.

## 5. Integration workflow

Do not wait until all modelling is finished to agree on interfaces. Use `shared/PIPELINE_CONTRACT.md` from the beginning.

The integrated flow is:

```text
User selects subsystem
        -> integrated app validates upload type
        -> calls that subsystem's prediction pipeline
        -> receives structured result plus official CSV
        -> shows result and grounded visualization
        -> offers the CSV for download
```

Integration order:

1. **Freeze output contracts:** exact filenames, columns, class capitalization, and error behavior.
2. **Integrate one subsystem first:** Rail is a good first candidate because it already has a working app and predictor.
3. **Add the other pipelines one at a time:** do not copy feature code into `integrated_app/`; import or call the owner pipeline.
4. **Add integration tests:** one valid and one invalid synthetic upload per subsystem.
5. **Generate `predictions.zip`:** place only attempted `*_predictions.csv` files at its top level.
6. **Run a clean-machine rehearsal:** another member follows the README without help.

Each model should return enough information for the UI without changing the official CSV, for example:

```text
official_prediction
confidence_or_ranking
calculated_evidence
warnings
downloadable_csv
```

Confidence is for display only unless the official schema explicitly accepts it.

## 6. UX workflow

Start UX after at least one real prediction pipeline works. Use Stitch to explore the screens, but implement the selected design in `integrated_app/`.

### Required user journey

1. Landing screen explains the four monitoring tasks in plain language.
2. User selects a subsystem.
3. Upload area states the accepted file type and expected input clearly.
4. App validates the file before running a model.
5. Processing state explains what is happening.
6. Results show the prediction, useful calculated evidence, and any warning.
7. User downloads the exact official CSV.

### Result presentation

- Door: timeline with detected cycles and Normal/Abnormal colors.
- ACV: ranked list of all cars with anomaly scores.
- Rail: Normal/Side I/Side II result, class confidence, and a Side I-versus-Side II signal comparison.
- SHM: predicted damage value, context range, and stress/cycle summary.

Avoid ungrounded generative explanations. Prefer deterministic text based on actual calculated features. If Gemini is used to rewrite explanations, pass only structured evidence and retain a non-LLM fallback.

### Demo-video sequence

In no more than three minutes:

1. State the maintenance problem.
2. Select a subsystem and upload a file.
3. Show the prediction and one meaningful visualization.
4. Download the output CSV.
5. Briefly show that the same app supports every attempted subsystem.

## 7. Git workflow

Everyone clones the same repository but works on a short branch inside their assigned folder.

```bash
git switch main
git pull
git switch -c rail/short-description
```

Recommended prefixes are `door/`, `acv/`, `rail/`, `shm/`, `app/`, and `shared/`.

Open a pull request with:

- What changed and why.
- Validation score before and after.
- Files affected.
- How another member can test it.

Never commit organizer datasets, trained artifacts, credentials, `.env` files, or hidden answers.

## 8. Rail Corrugation workflow for Ziqiai

Your first objective is not to beat every possible model. It is to establish a trustworthy end-to-end baseline and then improve it with evidence.

### Rail milestone R0 — Local setup

From `rail_corrugation/`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Copy the organizer files locally into:

```text
rail_corrugation/data/raw/rail/
├── Train/
├── Test/
└── Train_Labels.csv
```

The data is ignored by Git.

### Rail milestone R1 — Audit and visualize

Run:

```bash
rail-inspect \
  --train-dir data/raw/rail/Train \
  --labels data/raw/rail/Train_Labels.csv
```

Confirm:

- 272 labelled files are matched.
- Each sensor file has 129 columns.
- Labels contain only Normal, Side I, and Side II.
- The class imbalance is visible.
- The sample heatmap and signal plot are sensible.

Then manually compare at least two files from each class. Write down three observations before adding features.

### Rail milestone R2 — Understand the baseline features

Read `src/rail_cdm/features.py` and be able to explain:

- RMS: overall vibration strength.
- Standard deviation: variation.
- Peak: largest shock/vibration.
- Kurtosis: unusual sharp spikes.
- FFT bands: repeating vibration energy at different frequencies.
- Side aggregation: odd positions are Side I; even positions are Side II.
- Side ratio/difference: which rail side has stronger evidence.

Do not add a feature that you cannot explain or reproduce on test files.

### Rail milestone R3 — Train the baseline

Run:

```bash
rail-train \
  --train-dir data/raw/rail/Train \
  --labels data/raw/rail/Train_Labels.csv \
  --artifact-dir artifacts
```

Record:

- Macro F1.
- Normal, Side I, and Side II F1.
- Confusion matrix.
- Which minority class is confused with what.

The baseline uses class-weighted Extra Trees. Do not tune against Test files.

### Rail milestone R4 — Improve one idea at a time

Use this order:

1. Compare Extra Trees with class-weighted Random Forest.
2. Test alternative FFT bands.
3. Add cross-car agreement features.
4. Add speed-aware or wheel-order features.
5. Remove unstable/unhelpful features.
6. Only then consider gradient boosting or a neural model.

For every experiment, reuse the same cross-validation folds and record the per-class scores. Prefer an improvement that helps Side I and Side II consistently over one that only increases Normal accuracy.

### Rail milestone R5 — Error analysis

Use `artifacts/cross_validation_predictions.csv` to inspect:

- Side I files predicted Normal.
- Side II files predicted Normal.
- Side I and Side II confused with each other.
- Whether errors share speed, amplitude, frequency, or particular sensor patterns.

Form the next feature hypothesis from these errors, not from random model tuning.

### Rail milestone R6 — Freeze and predict

Once the final approach is chosen, retrain on all labelled files and run:

```bash
rail-predict \
  --test-dir data/raw/rail/Test \
  --model artifacts/rail_model.joblib \
  --output outputs/rail_predictions.csv
```

Verify:

- Exactly one row per test file.
- Columns are exactly `file_id,prediction`.
- Original filenames and extensions are preserved.
- Every prediction is exactly `Normal`, `Side I`, or `Side II`.
- There is no accidental index column.

### Rail milestone R7 — Integrate with UX

First run the existing Rail prototype:

```bash
streamlit run app.py
```

Then hand the integrated-app owner:

- `rail_cdm.features.extract_features`.
- The saved model bundle.
- The prediction/output validation code.
- A synthetic valid CSV for app testing.
- Recommended UI evidence: Side I/Side II comparisons and model probabilities.

The integrated app should call your pipeline, not recreate it.

### Your personal definition of done

Rail is complete when a teammate can clone the repository, install it, supply the data, train the model, reproduce your validation score, upload a new file through the app, and download a valid `rail_predictions.csv` without asking you how the code works.

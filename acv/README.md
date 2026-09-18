# ACV subsystem workspace

Owner task: rank all eight cars from most to least likely to have a refrigerant leak.

Required output:

```csv
file_id,ranked_cars
acv_test_case.xlsx,03|01|05|02|04|06|07|08
```

Current layout:

```text
acv/
├── data/raw/            Local organizer data; do not commit
├── notebooks/           Exploration only
├── predict.py           File/folder prediction entry point
├── src/baseline.py      Selected ranking rule
├── src/                 Exploration and comparison scripts
├── docs/                Official references and modelling notes
├── artifacts/           Saved parameters/models; do not commit
└── outputs/             Generated predictions; do not commit
```

The example above is illustrative, not a generated test prediction.

## Prediction interface

For a fresh checkout, use Python 3.11 or newer. From the repository root:

```bash
python3 -m venv acv/.venv
acv/.venv/bin/python -m pip install -r acv/requirements.txt
```

For charts and exploratory comparisons, also install:

```bash
acv/.venv/bin/python -m pip install -r acv/requirements-exploration.txt
```

Obtain the data from the official repository linked below. Keep training workbooks in `acv/data/raw/train/`, training labels at `acv/data/raw/Train_Labels.csv`, and test inputs separately in `acv/data/raw/test/`. Do not commit these files.

Run from the repository root. First check the output format with a training file:

```bash
acv/.venv/bin/python acv/predict.py --input acv/data/raw/train/acv_case_01.xlsx --output acv/outputs/check_case01/acv_predictions.csv
```

Expected case 01 content based on the previously run original baseline:

```csv
file_id,ranked_cars
acv_case_01.xlsx,01|02|03|04|07|05|06|08
```

`--input` also accepts a folder: all directly contained `.xlsx` files are processed in filename order, excluding Excel `~$` lock files. Subfolders are not searched. For submission, supply only the organiser's test case file/folder and use the output filename `acv_predictions.csv`. This training example is not a test submission.

The CLI preserves exact source filenames and header car IDs, and writes only `file_id,ranked_cars`, with pipe-separated car IDs and no index column. Existing destination CSVs are overwritten on success. All input files are scored before writing begins; invalid files abort the batch rather than being skipped.

## Standalone ACV screen

From the repository root, install the app dependencies and launch:

```bash
acv/.venv/bin/python -m pip install -r acv/requirements-app.txt
acv/.venv/bin/python -m streamlit run acv/app.py
```

Upload original Excel cases, select **Analyse cars**, review the inspection order,
select a car to view raw indoor/control temperatures, and download
`acv_predictions.csv`. The app calls the existing baseline; it does not change
the ranking rule. Missing evidence and provisional mappings are displayed.
Changing uploads clears previous results. Invalid batches produce no download.
Temporary uploaded files are removed after processing; results remain in the
browser session. Chart readings include all operating modes, while scoring uses
the baseline's eligibility filters. Processing currently reads workbooks more
than once, so large batches may take several minutes.

This screen has been written but not launched or runtime-tested yet. Start with
one training case and check the displayed ranking and downloaded CSV against
your earlier CLI output before using it for the final submission. Integration
into the shared app remains separate work.

## Fixed algorithm and app integration

- Rule version: original-positive-gap-v1. Score is mean max(indoor minus cooling control, 0), including zero gaps in the denominator.
- Standard layout requires Information Valid = Valid and Running Mode = Automatic Cooling, with finite temperatures.
- Rich layout provisionally uses passenger cabin minus target, Full Cooling or Half Cooling, and finite temperatures. No equivalent validity flag has been established.
- Highest score first; exact ties use ascending car ID. Unscored cars are placed last by ID with a warning, not interpreted as healthy. Entirely unscorable cases fail.
- This is the original sample-average baseline, not the time-weighted challenger. Pressure, valves, and peer-gap features do not enter the ranking.
- No learned parameters or saved model file are needed. Dependencies are in `requirements.txt`; exploratory plots additionally require matplotlib.
- App entry point: `create_predictions(input_path)` exported from `predict.py` returns the same two-column pandas table. The app should surface warnings and should not describe rankings as calibrated probabilities.
- `src/baseline.py` also accepts `--input` and required `--output`; earlier commands without `--output` must now include it.
- Checks cover eight distinct header car IDs, recognised fields, nonempty measurements, and present, unique, increasing timestamps. Labels are never read during prediction.

## Sources, limitations, and execution status

The official schema comes from the [ACV kit section 3](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/main/PS3/03_References/ACV/ACV_Subsystem_Info_Kit.md) and [PS3 specification section 4](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/main/PS3/01_Problem_Statement_3_Specifications.md). File/folder input follows the team contract in `shared/PIPELINE_CONTRACT.md`.

The kit references a required `predict.py` interface, while the main specification makes code optional and requires an app, a demo video, and predictions generated through the app. This command supports app integration; it does not complete those deliverables. See `docs/SOURCE_NOTES.md` for documentation conflicts and `docs/BASELINE_RULE.md` for modelling assumptions.

Both fixed temperature methods placed the faulty car first in five of six training cases and second in case 04 in the user's development comparison. This is not new independent validation. Case 04's pressure findings remain exploratory.

The user ran both single-file and six-file-folder prediction checks and shared the resulting CSVs. They matched the expected two-column format and earlier baseline rankings. No automated regression suite or fresh-environment installation has been run for this handoff. Test input was downloaded after the rule was selected; plot commands accept it for display only. No test-based tuning or test accuracy is claimed. A final test CSV has not been verified in this handoff.

## Reproduce the development comparison

```bash
acv/.venv/bin/python acv/src/compare_temperature_methods.py
```

The original and time-weighted relative rules both placed the faulty car first in cases 01, 02, 03, 05 and 06, and second in case 04: mean official rank score 0.9792 across six cases. All-six-case results are development results because those cases informed exploration. Earlier, the unchanged original rule placed the faulty car first in four whole cases (02, 03, 05, 06) held aside during initial development. This is a fixed-rule evaluation, not fitted leave-one-case-out cross-validation.

The additional scripts in `src/` are retained for reproducible learning and diagnostics. They are not dependencies of `predict.py` unless imported by `baseline.py`; prediction requires no plotting library. To compare original and relative control gaps for a training case:

```bash
acv/.venv/bin/python acv/src/plot_relative_control_gap.py --case 1
```

The team's app integration, final test CSV verification, video, and submission packaging remain separate work. See [integration handoff](docs/INTEGRATION_HANDOFF.md).

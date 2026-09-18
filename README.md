# rookies — NebulaX Train Condition Monitoring

One maintenance workspace for four train subsystems: rail corrugation, door
operation, air conditioning and structural health. Built for Nebula X PS3.

**[Open the public prototype](https://nebulax-workspace-1029817906638.asia-southeast1.run.app/)** ·
**[Model details](docs/rail-model-release.md)** ·
**[Deployment details](integrated_app/CLOUD_DEPLOYMENT.md)**

## Try it

1. Open **Review findings** and select a component. The page initially shows
   the complete prepared batch: 68 rail recordings, 38 detected door movements,
   one ACV workbook and 16 structural-health recordings.
2. Choose **New analysis** and upload recordings. Rail, Door and SHM use CSV;
   ACV uses XLSX. Door takes one continuous recording.
3. Click **Output predicted result**. Review the prediction, measured evidence
   and suggested technician check. New upload predictions open immediately.
   Reload the page to return to the complete official test results.
4. Choose **Download predictions → Download CSV**. The export matches the
   displayed results; a one-file upload does not export the full test set.

No login is required. Files are limited to 28 MiB each. Uploads use the saved
pipelines without retraining. Results are private to the current browser and
accessible for seven days; review notes are temporary.

## Approaches and development evidence

| Component | Selected approach | Development metric |
|---|---|---|
| Rail | Shared-side Random Forest, 20 fold-selected features, threshold 0.40 | Training macro F1 0.827808 (three split seeds); 0.818237 on two additional splits |
| Door | Gap segmentation, seven current/direction features, small Random Forest | IoU-weighted F1 1.0000 in reused chronological and robustness checks |
| ACV | Rank cars by mean positive temperature gap during eligible cooling | Linear rank-decay 0.9792 over six development cases |
| SHM | Rainflow cycle features and Ridge correction of a damage proxy | Teammate-reported grouped MAPE 2.020%; derived score 0.9798 |

These are **not held-out test scores**. Development data informed model choices.
Door's perfect development result is not a promise of perfect predictions. SHM's
reported validation has not been independently rerun during integration.
Only the organiser holds the official test answers.

## Architecture

HTML/CSS/JavaScript dashboard → Flask service → saved subsystem pipeline →
on-screen evidence and competition CSV. Google Cloud Run hosts the container;
private Cloud Storage holds the 86 official test inputs; private Firestore stores
browser-scoped results. Storage, database access and credentials are not public.
The AI improvement tab describes a planned human-reviewed capability;
Gemini/Vertex AI are not running the predictions.

## Run the shared app

The submission app bundle includes the trusted trained models. The selected Rail
bundle is tracked at `rail_corrugation/artifacts/rail_model.joblib`; see the
[rail model release](docs/rail-model-release.md) for validation and reproduction.
Before building from a Git clone, supply the ignored Door bundle at
`door/artifacts/door_selected.joblib`. SHM's bundle is tracked.
Never load an untrusted uploaded pickle/joblib model.

From the repository root, with Docker installed:

```sh
docker build -t nebulax-workspace .
docker run --rm -p 8080:8080 nebulax-workspace
```

Open `http://localhost:8080`. Local results use memory unless cloud variables are
configured. See [deployment notes](integrated_app/CLOUD_DEPLOYMENT.md) for runtime
limits and permissions. No raw dataset is included in the submission bundle;
judges can upload their organiser-provided inputs.

## Repository and checks

`rail_corrugation/`, `door/`, `acv/`, `shm/`: component pipelines.
`integrated_app/`: shared UI/service. `tools/`: submission checks.

Install `integrated_app/requirements-cloud.txt` in an isolated environment, then:

```sh
python -m unittest discover -s integrated_app -p 'test_*server.py'
node integrated_app/test-result-sources.mjs
```

`tools/build_submission.py` runs the official cloud test catalogue through the
app's inference endpoint and validates all four submission CSVs.

This is a decision-support prototype, not a certified diagnostic system or
remaining-useful-life forecaster. Technicians must confirm findings. Keep the
temporary cloud project active through judging; instance limits are not a hard
spending cap.

## References

- [Official PS3 specifications](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/main/PS3/01_Problem_Statement_3_Specifications.md)
- [Subsystem info kits](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/tree/main/PS3/03_References)
- [Required example schemas](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/tree/main/PS3/04_Example_Submission)

Raw datasets, credentials and environments must not be committed.
The required video is prepared separately and is not included in this package.

# NebulaX PS3 Team Repository

One shared repository contains four independent subsystem workspaces. Each member can develop and test their own pipeline without repeatedly editing the same files.

```text
hackathon/
├── door/                 Door cycle segmentation and classification
├── acv/                  Refrigerant-leak car ranking
├── rail_corrugation/     Rail Side I / Side II classification
├── shm/                  Cumulative fatigue-damage regression
├── integrated_app/       Final shared upload and results application
├── shared/               Agreements used by all four pipelines
└── docs/                 Team process and Git workflow
```

## Current delivery status

Rail has a working upload-to-download Streamlit application and a frozen 30-feature
Random Forest pipeline. It achieved fixed five-fold macro F1 **0.8234**, accuracy
**94.1%**, and Side I recall **78.6%**; mean macro F1 across five fold arrangements
was **0.8229**. These are development validation scores, not hidden-test results.
All 68 official test predictions were reproduced and validated. The latest suite has
34 passing tests, including upload and complete-batch download checks.

Architecture: recording CSV → validation → signal summaries → fold-fitted feature
selection and SMOTE during training → Random Forest → class result and official CSV.
The app uses the saved pipeline directly and displays measured side-to-side vibration evidence.

Start with [Rail setup and results](rail_corrugation/README.md),
[release status](rail_corrugation/FINAL_READINESS.md), and
[demo narration/write-up](docs/rail-demo-and-writeup.md).
[Cloud Run configuration](rail_corrugation/DEPLOYMENT.md) is prepared but deployment
is not yet verified. Add the hosted URL and recorded video link once available.
Door and SHM pipeline contributions are merged. Door lives in `door/`; the SHM contribution currently lives in `shm_work/`. ACV is awaiting its contribution.
The shared UX outline is runnable from `integrated_app/`, with dedicated component UX folders and sample findings. The merged pipelines are not yet connected to that outline. See [shared UX setup and ownership](integrated_app/README.md).

Ownership below identifies workstreams. Replace role labels with the actual team members
and describe their completed contributions before submitting the final team README.

## Ownership

| Workspace | Main owner | Required output |
|---|---|---|
| `door/` | Door member | `door_predictions.csv` |
| `acv/` | ACV member | `acv_predictions.csv` |
| `rail_corrugation/` | Rail member | `rail_predictions.csv` |
| `shm/` | SHM member | `shm_predictions.csv` |
| `integrated_app/` | Shared near the end | One app calling all completed pipelines |

Each owner decides the internal modelling approach but must follow [`shared/PIPELINE_CONTRACT.md`](shared/PIPELINE_CONTRACT.md). This is what makes later integration predictable.

## Getting started

1. Clone the repository.
2. Read [`docs/team-workflow.md`](docs/team-workflow.md).
3. Enter your assigned directory.
4. Follow that directory's README.
5. Work on a branch and open a pull request rather than editing `main` directly.

The Rail workspace already contains a complete beginner-friendly baseline. The other workspaces begin with their data contract and task checklist so their owners can add code independently.

Before the event, review the [participant-pack readiness audit](docs/participant-pack-audit.md) and the [Google tools guide](docs/google-tools-guide.md).

## Repository rules

- Do not commit organizer datasets; every member copies them into their own ignored `data/raw/` directory.
- Do not commit trained models, generated outputs, `.env` files, or credentials.
- Do not use hidden test answers to select features or models.
- Keep the exact organizer filenames and prediction labels.
- A subsystem is integration-ready only when its command can turn an input path into the exact required CSV.

## Sync the shared UX before starting component design

The combined baseline is on this repository’s `main` branch. In GitHub Desktop, fetch and pull `main`, then create your component design branch. If working in a fork, first use **Sync fork → Update branch** on GitHub, then fetch/pull locally. Commit or stash unfinished local work before switching branches.

Component design folders: `integrated_app/components/rail/`, `door/`, `acv/`, and `shm/`. Each has its own README and page module. Keep shared navigation/style changes coordinated with the integrator.

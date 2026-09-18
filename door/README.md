# Door subsystem workspace

## Current selected model

Use [`src/selected_model.py`](src/selected_model.py), which defaults to
`artifacts/door_selected.joblib`. This is the current-pattern Random Forest plus movement
direction, selected using training validation performance and simplicity. See
[SELECTED_MODEL.md](SELECTED_MODEL.md) for commands, verification and limitations.
The earlier baseline scripts and model are retained for comparison.

Owner task: detect door-cycle start/end boundaries in a continuous stream and classify every detected cycle as `Normal` or `Abnormal resistance`.

Required output:

```csv
start_time,end_time,prediction
```

Suggested internal layout:

```text
door/
├── data/raw/            Local organizer data; do not commit
├── notebooks/           Exploration only
├── src/door_cdm/        Reusable loading, segmentation and classification code
├── tests/               Synthetic and format checks
├── artifacts/           Saved models; do not commit
└── outputs/             Generated predictions; do not commit
```

First milestone: plot door position/current with the supplied true segment boundaries and implement an end-to-end validation score that includes both segmentation and classification.


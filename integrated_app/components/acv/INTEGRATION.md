# ACV integration from PR #5

The shared header, navigation, component cards, review layout, Model evidence,
AI improvement and other components retain the main branch design. No global
stylesheet or HTML shell changes were taken from the PR. ACV-specific evidence
and charts use the shared theme variables and stay inside the ACV detail panel.

New analysis accepts Excel files for ACV. A successful batch opens Review
findings → Air conditioning, with one finding per workbook, selectable cars,
temperature-gap charts, review notes and the shared CSV download bar.
Changing files clears stale predictions/downloads. Results and notes remain
in browser memory; they are not yet connected to Firestore.

Run the local server from the repository root using a Python environment with
`acv/requirements.txt` installed:

```sh
python integrated_app/server.py --port 8502
```

Stop any static server on that port first. The adapter binds to localhost only;
it is not the production cloud backend. No cloud deployment is included here.

Tests: `python -m unittest discover -s integrated_app -p 'test_acv_server.py'`.
These check a synthetic workbook's ranking, exact CSV columns, evidence and
invalid batch handling; they do not constitute model-accuracy validation.

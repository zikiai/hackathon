# Air conditioning UX ownership

Edit `index.js` in this folder to develop your component without changing your teammates' pages.

- `config`: page labels, sample finding, upload guidance and interpretation text.
- `renderInterpretation(state)`: numerical evidence and explanation for the selected finding.
- `renderMethod()`: model choice, preprocessing, experiments, validation splits and measured results.
- Add component-specific assets/helpers in this folder. Scope styles to this component.

These functions return trusted HTML templates. Escape any filenames, notes or other user-provided text before inserting it. Shared code already escapes review notes.

The common shell owns navigation, review state, downloads and feedback. Coordinate changes to `../../app.js` with the integrator. Your Python analysis remains in the existing repository subsystem directory; do not duplicate it here.

The ACV workspace supports uploads through `integrated_app/server.py`. Until analysis succeeds it shows no results. Its methodology describes the existing fixed baseline and previously user-run training evaluations. Those figures are development evidence, not measured test performance. This new integration has not been executed yet.

The train-shaped selector separates inspection priority from car number. Clicking
a numbered carriage shows its evidence panel with both identifiers, gap, usable
readings, data quality and a temperature-chart placeholder. Native buttons work
with Tab and Enter/Space; the selected state uses both text and colour. The train
uses the full ACV content width, with eight cars in one row or two rows of four
when the available panel width is 760px or less. It remains in car-number order (not a
claim about physical formation). Component styles live in styles.css. The eight numbered slots are
layout examples, not uploaded data. No ranking or readings are fabricated.
When connecting the backend, use actual header IDs, show the returned rank separately,
show “Not assessed” for unavailable scores, and populate charts from the same
recording. Do not turn the slot position into an inspection priority.

The adapter calls the same `create_predictions(input_path)` and `rank_file` functions in `acv/src/baseline.py` used by the CLI. Input is original `.xlsx` cases; output is `acv_predictions.csv` with `file_id,ranked_cars` and pipe-separated two-digit IDs. Provisional mappings and missing-data warnings are displayed. `upload.js` manages batch selection, loading/error states, CSV downloads and raw temperature SVG charts. It does not calculate ranking scores.

The shared shell routes ACV review and analysis to this real upload workspace instead of sample review controls. Other components remain previews. The Model evidence page contains the recorded evaluation results. Coordinate the shell and local server changes with the integrator. These edits have not been run or browser-tested. See `../../README.md` for launch instructions and the handoff checklist.

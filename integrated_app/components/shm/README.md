# Structural health UX ownership

Edit `index.js` in this folder to develop your component without changing your teammates' pages.

- `config`: page labels, sample finding, upload guidance and interpretation text.
- `renderInterpretation(state)`: numerical evidence and explanation for the selected finding.
- `renderMethod()`: model choice, preprocessing, experiments, validation splits and measured results.
- Add component-specific assets/helpers in this folder. Scope styles to this component.

These functions return trusted HTML templates. Escape any filenames, notes or other user-provided text before inserting it. Shared code already escapes review notes.

The common shell owns navigation, review state, downloads and feedback. Coordinate changes to `../../app.js` with the integrator. Your Python analysis remains in the existing repository subsystem directory; do not duplicate it here.

All displayed findings are sample data. Replace examples only when your tested backend supplies results. Do not mark a prediction operational merely because it has a high score. See `../../README.md` for the handoff checklist.

The merged SHM prediction utility currently lives in repository-root `shm_work/predict_shm.py`; the original `shm/` directory remains a scaffold.

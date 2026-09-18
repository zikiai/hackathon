# Shared maintenance UX outline

A runnable, dependency-free version of the agreed UI design. This is a development outline with clearly marked sample findings, not a live monitoring or inference service. The existing Rail Streamlit app remains the working prediction application.

## Run locally

From the repository root:

```sh
python3 -m http.server 8502 --bind 127.0.0.1 --directory integrated_app
```

Open http://127.0.0.1:8502/. Serve over HTTP; opening index.html directly will not load JavaScript modules reliably. No npm install, cloud credentials or model files are needed.

## Dedicated ownership folders

| Component | UX folder | Analysis pipeline folder |
|---|---|---|
| Rail | `components/rail/` | `../rail_corrugation/` |
| Doors | `components/door/` | `../door/` |
| Air conditioning / refrigerant leaks | `components/acv/` | `../acv/` |
| Structural health | `components/shm/` | `../shm_work/` (merged contribution) |

Each component exports `config`, `renderInterpretation(state)` and `renderMethod()` from its own `index.js`. Edit that file and add local assets/helpers in your component folder. Refresh the browser to see changes. These are plain JavaScript modules with HTML templates, so no frontend build system is required.

The integrator owns `app.js` (common interaction and routing), `styles.css` (shared visual system) and `index.html` (application shell). Component-specific page content belongs in component folders to reduce merge conflicts. Scope any component CSS to that component and coordinate shared style changes.

## Included behavior

- Centred review screen, component selection and recording selection.
- Numerical interpretation with example values clearly distinguished from real validation results.
- Per-component methodology pages; Rail has existing research results, others have explicit placeholders.
- Review notes and reviewed/reopened state, retained in memory while navigating. Reloading resets this outline.
- Downloadable sample Rail prediction CSV and per-component text reports including notes. Sample filenames begin `demo_`; these are not competition submissions.
- Feedback collection and an AI-improvement concept page across all components. No AI API, retraining, source-code modification or deployment runs from the interface.

## What each teammate should deliver

1. Complete the input requirements and numerical interpretation in your component UX.
2. Document your actual model, preprocessing/features, training procedure, validation split, baseline comparisons, test metrics and representative mistakes.
3. Expose your tested existing prediction function/command through the eventual backend adapter. Keep model logic in your subsystem, not the browser or shared app.
4. Provide a synthetic example, expected prediction CSV, model version and safe numerical evidence for each result. Define units, reference values and score semantics.
5. Provide loading, invalid-input, failed-analysis, empty-result and completed-result states when connecting the backend.
6. Follow `../shared/PIPELINE_CONTRACT.md`: exact columns, labels, file identifiers and output filenames. Only enable production downloads after full-batch validation; do not add review notes to official CSVs. Confirm ACV ranking serialization with the team contract.

The final UI should offer the official component CSV and a separate operator report. Package completed component CSVs in `predictions.zip` for submission. Do not export placeholder or incomplete components as final results.

## AI improvement scope

Review notes are feedback, not automatically verified labels. The intended flow is: collect note and prediction context → engineer verification → AI proposes a candidate change on a development branch → evaluation and regression tests → reviewed, versioned release. Preserve a fixed evaluation set and previous model version. This outline only demonstrates feedback collection; implement the backend and release workflow separately.

## Checks

With Node installed, run `npm run check` in this folder for JavaScript syntax checks (no dependencies to install). Browser smoke check: switch all four components, inspect their methodology pages, write a note, mark a finding reviewed, collect feedback, and download a sample report/CSV. Check narrow and desktop widths.

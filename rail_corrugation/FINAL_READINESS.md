# Rail final readiness — 19 September 2026

## Complete

- Active model frozen: 30 selected measurements, moderate SMOTE, 500-tree Random Forest, fixed 1.5× Side I adjustment.
- Fixed validation macro F1 0.823353; five-arrangement mean 0.822854. No final refinement surpassed it.
- All 68 test recordings reprocessed; every prediction exactly matches the saved official CSV.
- Verified columns `file_id,prediction`, unique filenames, exact test-inventory coverage, and allowed labels.
- Predictions: 58 Normal, 6 Side I, 4 Side II.
- `predictions.zip` contains only `rail_predictions.csv` at its root. This is a Rail-only package; add other completed subsystem CSVs for the team submission.
- App rejects wrong recording lengths and blocks partial or duplicate-file exports.
- App shows measured side-to-side RMS evidence and explains that adjusted model scores are not calibrated correctness probabilities.
- 34 tests, lint, and whitespace checks pass. Upload UI checks cover valid, malformed, and duplicate inputs.
- Demo narration and short write-up prepared in `demo-and-writeup.md`.

## Error review

The fixed validation has 16 mistakes: 9 Normal recordings flagged as faults, 3 Side I recordings classified Normal, 1 Side II recording classified Normal, and 3 Side II recordings classified Side I.

All mistakes have mean speed values between 0.5042 and 0.5112. All three missed Side I examples have Side I/Side II vibration-RMS ratios below one. Two missed Side I recordings have model scores above 0.9 for Normal, so a low-score threshold alone would not catch these misses. These are descriptive observations from the same development data, not evidence for a new physical rule. `validation-mistakes.csv` lists the files for mentor review. Keep the active model and ask the mentor to confirm the rotating-speed unit.

## Still needed for the team submission

1. Supply the assigned Google Cloud project ID and deployment owner. Configuration is prepared, but no hosted URL has been created or verified. See `rail-deployment.md`.
2. Collect any other attempted subsystem CSVs. Door, ACV, SHM, and the integrated app are placeholders in this local checkout; teammates may have newer work elsewhere.
3. Record and upload the 2–3 minute video using the real app, then verify access to the link.
4. Fill in actual team-member contributions and the hosted/video URLs in the final team README or portal.
5. Upload the verified package through the organizer portal and confirm its receipt. No competition submission has been sent by this task.

## Local demo

From the repository's `rail_corrugation` directory:

```bash
source .venv/bin/activate
streamlit run app.py
```

Use organizer Test recordings for a live demonstration. Their predictions are model outputs; their true labels are unavailable. Show validation performance separately from test inference.

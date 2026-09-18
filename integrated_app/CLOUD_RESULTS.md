# Model evidence handoff

The Model evidence page reads `evaluation-results.json` on page load, on opening
the tab. Raw datasets are not downloaded by the UI.

After a cloud evaluation job completes, publish its results to this JSON file
beside the deployed app. Uploading raw data alone does not update scores.
No Google Cloud job, credentials or deployment is configured by this UI change.

Each component key (`rail`, `door`, `acv`, `shm`) has:

- `score`: number from 0 to 1, or null when not evaluated.
- `model`: selected model name.
- `evaluation`: labelled-training evaluation method, sample count and limitations.
- `rationale`: why the model was selected, or the planned approach if pending.

Use macro F1 for Rail, IoU-weighted F1 for Door, official linear rank-decay
score for ACV, and max(0, 1 − MAPE) for SHM (MAPE as a fraction, not percent).
The app escapes text and rejects malformed entries. Failed loads show Pending
rather than invented scores. Publish the artifact atomically after validation.

Initial evidence sources: Rail component's existing five-fold and five-seed
results; Door selected-model chronological validation; ACV README's six-case
development evaluation (0.9792). No SHM score is currently available.

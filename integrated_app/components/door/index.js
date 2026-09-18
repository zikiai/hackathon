export { getRecords, renderStatistics, statisticsText, recommendation } from './view.js';
// Component-owned UX. Keep prediction and feature-extraction logic in the existing Python pipeline.
export const config = {
  "name": "Door operation",
  "short": "Doors",
  "icon": "panel-left-close",
  "status": "38 calculated reference movements",
  "input": "A continuous door recording",
  "format": "CSV columns: Datetime, Motor current(mA), Door leaf position",
  "output": "Normal / Abnormal resistance, by cycle",
  "title": "Unusual resistance in a door cycle",
  "finding": "This example highlights a cycle classified as abnormal resistance, with a time interval for investigation.",
  "scope": "Example interval: 12.4–15.8 s. Door identity not supplied.",
  "next": "Open the flagged cycle and compare it with a normal cycle.",
  "why": "Resistance describes a model-detected pattern during a door cycle. It does not establish the underlying mechanical cause.",
  "evidence": "The integrated view will show cycle boundaries and the supporting signal. Validation results will be added when the door pipeline is connected.",
  "file": "door-example-01.csv"
};
const evaluation = {
  "metric": "IoU-weighted F1",
  "steps": [
    "Validate and segment continuous recordings into door cycles.",
    "Classify each cycle as Normal or Abnormal resistance.",
    "Compare predicted intervals and labels with reference cycles using IoU-weighted F1."
  ]
};
export function renderMethod(){return `<h2>Current-pattern Random Forest</h2><p>200 trees · maximum depth 4 · minimum leaf size 3 · balanced class weights · seed 42</p><h3 class="nx-spaced">Which files go in?</h3><ol class="nx-method"><li><strong>Train.csv</strong><p>18,036 timestamped readings covering 110 labelled movements, according to the Door audit.</p></li><li><strong>Train_Segments_Answer.csv</strong><p>Training movement boundaries and Normal / Abnormal resistance labels. Used for training and validation, not inference.</p></li><li><strong>Test.csv or a new recording</strong><p>The prediction command accepts an explicitly supplied CSV. Required columns: Datetime, Motor current(mA), Door leaf position. Timestamps must be strictly increasing; numeric inputs must be finite.</p></li></ol><h3>How the result is calculated</h3><ol class="nx-method"><li>Validate input, then split movements at timestamp gaps above the saved threshold (0.2 s for the supplied 0.02-second data).</li><li>Convert current from mA to A. Calculate mean absolute current, peak absolute current, current standard deviation, and mean absolute current over each elapsed-time third.</li><li>Infer opening versus closing from net position change. These seven features feed the selected model; voltage and back-EMF from the earlier baseline are not selected-model inputs.</li><li>Classify Abnormal resistance at abnormal score ≥ 0.5; otherwise Normal. Export original start/end timestamps and the prediction.</li></ol><h3>Reported tests</h3><p>The selected candidate reports IoU-weighted F1 1.0000 across chronological blocks (110 movements), earlier-to-later evaluation (66), and similar-curve exclusion (110). These are exploratory reused-training evaluations, not hidden-test accuracy.</p><div class="nx-notice">Unlabelled test: 6,253 readings → 38 detected movements → 29 Normal, 9 Abnormal resistance. Ground-truth test labels are unavailable.</div><p>One Normal prediction had an unusually long movement and large position change. The interface therefore exposes measurement context for both classes.</p><p class="nx-spaced nx-small">Sources: door/src/selected_model.py, SELECTED_MODEL.md and TEST_COMPARISON.md. Raw Door data and the reproduced selected model are available locally. Reference findings were recalculated from Test.csv. The new 29/9 class count differs from the historical 30/8 audit; test labels remain unknown. Gap-free live telemetry and new-door generalisation are not established.</p>`;}

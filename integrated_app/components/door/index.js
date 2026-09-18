// Component-owned UX. Keep prediction and feature-extraction logic in the existing Python pipeline.
export const config = {
  "name": "Door operation",
  "short": "Doors",
  "icon": "panel-left-close",
  "status": "Integration pending",
  "input": "A continuous door recording",
  "format": "Input schema to be confirmed with the door team",
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
export function renderInterpretation(state) { return `<div class="nx-evidence"><div class="nx-metric"><strong>12.4–15.8 s</strong><span>Example flagged interval</span></div><div class="nx-metric"><strong>3.4 s</strong><span>Interval duration</span></div></div><p>The interval identifies where to inspect the recording. Duration alone does not establish abnormal resistance. Signal statistics, normal-cycle comparisons and model scores await the door pipeline.</p>`; }
export function renderMethod() { return `<div class="nx-sectionhead"><h2>${config.name} methodology</h2><span class="nx-pill">Team details pending</span></div><p>Model name, features, split strategy and measured results await the component owner.</p><h3 class="nx-spaced">Planned evaluation structure</h3><ol class="nx-method">${evaluation.steps.map(s=>`<li>${s}</li>`).join('')}</ol><div class="nx-notice"><strong>Competition metric: ${evaluation.metric}</strong><p>No measured score is available in this outline.</p></div><h3>What judges should see</h3><p>The chosen model, preprocessing, features, training setup, validation split, baseline comparisons, measured results and representative errors.</p>`; }

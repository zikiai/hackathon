// Component-owned UX. Keep prediction and feature-extraction logic in the existing Python pipeline.
export const config = {
  "name": "Structural health",
  "short": "Structure",
  "icon": "activity",
  "status": "Integration pending",
  "input": "One or more structural recordings",
  "format": "Input schema to be confirmed with the SHM team",
  "output": "Estimated cumulative fatigue damage",
  "title": "Fatigue estimate ready for interpretation",
  "finding": "The structural module will return a cumulative fatigue damage estimate for each recording.",
  "scope": "No operational threshold or remaining-life estimate has been established.",
  "next": "Interpret the estimate with the engineer responsible for the structure.",
  "why": "Cumulative fatigue damage is a model estimate. A maintenance threshold and remaining useful life cannot be inferred from the number alone.",
  "evidence": "The final view will show the estimate, its definition and validation error. Threshold-based alerts require an agreed engineering rule.",
  "file": "shm-example-01.csv"
};
const evaluation = {
  "metric": "max(0, 1 − MAPE)",
  "steps": [
    "Validate structural recordings and derive the model’s inputs.",
    "Estimate cumulative fatigue damage for each file.",
    "Compare estimates with reference damage using the competition’s MAPE-based score."
  ]
};
export function renderInterpretation(state) { return `<div class="nx-notice">Numerical result awaiting structural pipeline</div><p>The connected view will show the fatigue estimate, its definition, validation error and any supported reference value. No fatigue value or maintenance threshold has been invented for this preview.</p>`; }
export function renderMethod() { return `<div class="nx-sectionhead"><h2>${config.name} methodology</h2><span class="nx-pill">Team details pending</span></div><p>Model name, features, split strategy and measured results await the component owner.</p><h3 class="nx-spaced">Planned evaluation structure</h3><ol class="nx-method">${evaluation.steps.map(s=>`<li>${s}</li>`).join('')}</ol><div class="nx-notice"><strong>Competition metric: ${evaluation.metric}</strong><p>No measured score is available in this outline.</p></div><h3>What judges should see</h3><p>The chosen model, preprocessing, features, training setup, validation split, baseline comparisons, measured results and representative errors.</p>`; }

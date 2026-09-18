// Component-owned UX. Keep prediction and feature-extraction logic in the existing Python pipeline.
export const config = {
  "name": "Air conditioning",
  "short": "ACV",
  "icon": "wind",
  "status": "Integration pending",
  "input": "One or more air-conditioning recordings",
  "format": "Input schema to be confirmed with the ACV team",
  "output": "All eight cars ranked by suspected leak",
  "title": "Car 3 ranks first for leak review",
  "finding": "In this example, Car 3 is ranked ahead of the other cars for investigation of a possible air leak.",
  "scope": "Relative ranking across eight cars; not a confirmed leak.",
  "next": "Review the highest-ranked car against the supporting signals.",
  "why": "A ranking prioritises inspection. The first-ranked car is not necessarily faulty, and rank is not a calibrated probability.",
  "evidence": "The final view will show all eight ranked cars and the model evidence supplied by the ACV team.",
  "file": "acv-example-01.csv"
};
const evaluation = {
  "metric": "Linear rank-decay score",
  "steps": [
    "Validate inputs and derive features for all eight cars.",
    "Rank all eight cars by the model’s leak evidence.",
    "Evaluate ranking quality with the competition’s linear rank-decay metric."
  ]
};
export function renderInterpretation(state) { return `<div class="nx-schematic" aria-label="Example car ranking: 3, 6, 1, 8, 2, 5, 4, 7">${[3,6,1,8,2,5,4,7].map((n,i)=>`<span class="nx-car ${i===0?'flagged':''}">${n}</span>`).join('')}</div><p class="nx-small">Illustrative ranking · Highest priority first</p><div class="nx-evidence"><div class="nx-metric"><strong>1 of 8</strong><span>Car 3’s rank</span></div><div class="nx-metric"><strong>8 cars</strong><span>Complete ranking coverage</span></div></div><p>Rank identifies review order, not leak size or probability. Per-car signal statistics and the score gap between cars await the ACV pipeline.</p>`; }
export function renderMethod() { return `<div class="nx-sectionhead"><h2>${config.name} methodology</h2><span class="nx-pill">Team details pending</span></div><p>Model name, features, split strategy and measured results await the component owner.</p><h3 class="nx-spaced">Planned evaluation structure</h3><ol class="nx-method">${evaluation.steps.map(s=>`<li>${s}</li>`).join('')}</ol><div class="nx-notice"><strong>Competition metric: ${evaluation.metric}</strong><p>No measured score is available in this outline.</p></div><h3>What judges should see</h3><p>The chosen model, preprocessing, features, training setup, validation split, baseline comparisons, measured results and representative errors.</p>`; }

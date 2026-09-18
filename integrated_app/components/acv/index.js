// ACV-owned presentation. Prediction logic remains in acv/src/baseline.py.
import {renderUpload, renderChart, getResult} from './upload.js';
export {downloadPredictions} from './upload.js';
export function getRecords() {
  return (getResult()?.cases || []).map(recording => ({
    ...recording, id: recording.file_id, file: recording.file_id,
    prediction: 'Inspection ranking',
    title: `Car ${recording.ranking[0].car} ranks first for inspection`,
    provenance: 'Calculated from uploaded workbook using the fixed ACV baseline'
  }));
}
export function renderStatistics(recording) { return renderInterpretation(recording); }
export function recommendation(recording) { return `Inspect Car ${recording.ranking[0].car} first, then follow the ranked inspection order. Check the cooling system and confirm the cause; temperature gaps alone do not prove a refrigerant leak.`; }
export function statisticsText(recording) { return recording.ranking.map(row => `Car ${row.car}: ${row.evidence === 'scored' ? 'priority '+row.rank+', average positive gap '+row.average_positive_gap : 'insufficient evidence'}`); }
export function renderWorkspace() { return renderUpload(renderInterpretation); }
const stylesheet = document.createElement('link');
stylesheet.rel = 'stylesheet';
stylesheet.href = new URL('./styles.css', import.meta.url).href;
document.head.appendChild(stylesheet);

// Update only the ACV selector: preserve focus, notes and shared page state.
document.addEventListener('click', event => {
  const button = event.target.closest('button[data-acv-car]');
  if (!button) return;
  const explorer = button.closest('[data-acv-explorer]');
  if (!explorer) return;
  explorer.querySelectorAll('[data-acv-car]').forEach(item => {
    item.setAttribute('aria-pressed', String(item === button));
  });
  explorer.querySelectorAll('[data-acv-panel]').forEach(panel => {
    panel.hidden = panel.dataset.acvPanel !== button.dataset.acvCar;
  });
});
export const config = {
  name: 'Air conditioning', short: 'ACV', icon: 'wind',
  status: 'Local upload available',
  input: 'One or more original Excel case files',
  format: '.xlsx recordings with Time and all eight car identifiers. Keep original filenames and column headers. Timestamps must be present, unique and increasing. The pipeline checks supported temperature and operating-mode fields.',
  output: 'acv_predictions.csv — file_id and ranked_cars; eight two-digit car IDs separated by |',
  title: 'Cooling inspection order — awaiting analysis',
  finding: 'The baseline suggests which cars to inspect first for a possible refrigerant leak. This preview is not connected to uploaded recordings, so no current car ranking is available.',
  scope: 'Inspection priority, not a confirmed leak diagnosis or leak probability.',
  next: 'Connect the ACV prediction pipeline, then review the car comparison and supporting temperatures.',
  why: 'A larger average positive gap means a car stayed further above its cooling target during eligible readings. Other causes can also produce a gap.',
  evidence: 'Show gap scores, usable reading counts and data limitations. Missing evidence is different from a zero gap.',
  file: 'No recording analysed'
};

export function renderInterpretation(recording = null) {
  // The shared shell passes its navigation state; only actual result objects count.
  if (!recording?.ranking) recording = null;
  // These are layout slots, not inferred identifiers or results from a workbook.
  // The backend must replace them with the case's own validated car identifiers.
  const carSlots = recording ? recording.ranking.map(row => row.car).sort() : ['01', '02', '03', '04', '05', '06', '07', '08'];
  const rows = Object.fromEntries((recording?.ranking || []).map(row => [row.car, row]));
  const firstCar = recording ? recording.ranking[0].car : carSlots[0];
  const priority = car => !recording ? 'Awaiting analysis' : rows[car].evidence === 'unavailable' ? 'Not assessed' : `${rows[car].rank} of 8`;
  const best = recording?.ranking[0];
  const tied = recording ? recording.ranking.filter(row => row.average_positive_gap === best.average_positive_gap).length : 0;
  return `${recording ? `<section class="acv-result-summary" aria-label="Inspection result">
    <h2>Car ${firstCar}</h2>
    <p class="acv-result-subtitle">Suggested first inspection</p>
    <p class="nx-small">${tied > 1 ? 'Top score tied; car number determines the order.' : 'Largest average gap above the cooling target.'} This is not a confirmed leak.</p>
    <h3>Overall inspection order</h3>
    <ol class="acv-ranking-list" aria-label="Overall inspection order">
      ${recording.ranking.filter(row => row.evidence === 'scored').map(row => `<li><span class="acv-rank-number" aria-label="Priority ${row.rank}">${row.rank}</span><strong>Car ${row.car}</strong></li>`).join('')}
    </ol>
    ${recording.ranking.some(row => row.evidence === 'unavailable') ? `<p class="nx-small"><strong>Not assessed:</strong> ${recording.ranking.filter(row => row.evidence === 'unavailable').map(row => `Car ${row.car}`).join(', ')}. Insufficient data; placed last by car number in the export.</p>` : ''}
  </section>` : '<div class="nx-notice"><strong>No recording analysed</strong><p>Choose New analysis to upload a recording using the local ACV server.</p></div>'}
  <section class="acv-explorer" data-acv-explorer aria-label="Train car evidence">
    <h3>Select a car to inspect</h3>
    <p>All eight cars are shown below. Choose a numbered carriage to see its evidence.</p>
    <p class="nx-small">Schematic in car-number order, not inspection-priority order or a confirmed physical formation.</p>
    <div class="acv-train-scroll" role="group" aria-label="Choose a car">
      <div class="acv-train">
        ${carSlots.map(car => `<button type="button" class="acv-car" data-acv-car="${car}" aria-pressed="${car === firstCar}" aria-controls="acv-evidence-${car}" aria-label="Car ${car}, inspection priority ${priority(car)}. Show evidence.">
          <span class="acv-car-body" aria-hidden="true">
            <svg viewBox="0 0 300 86" focusable="false">
              <rect x="35" y="65" width="230" height="8" rx="2" fill="#293237"/>
              <rect x="90" y="68" width="120" height="9" rx="2" fill="#354047"/>
              ${[43, 64, 236, 257].map(x => `<circle cx="${x}" cy="76" r="7" fill="#20292e"/><circle cx="${x}" cy="76" r="3" fill="#59656b"/>`).join('')}
              <rect x="3" y="9" width="294" height="59" rx="7" fill="#d9dedd" stroke="#7f8a8e" stroke-width="1.5"/>
              <path d="M10 10 H290" stroke="#f7f9f8" stroke-width="6" stroke-linecap="round"/>
              <rect x="33" y="5" width="42" height="5" rx="2" fill="#e6eae8"/>
              <rect x="225" y="5" width="42" height="5" rx="2" fill="#e6eae8"/>
              <path d="M4 50 H296" stroke="#bf204a" stroke-width="7"/>
              ${[17, 132, 247].map(x => `<rect x="${x}" y="19" width="35" height="45" rx="1" fill="none" stroke="#778286"/><path d="M${x + 17.5} 19 V64" stroke="#536066"/>${[x + 4, x + 21].map(wx => `<rect x="${wx}" y="23" width="10" height="20" rx="1.5" fill="#34454e" stroke="#8c999d"/><path d="M${wx + 3} 26 V38" stroke="#8098a1" stroke-width="2"/>`).join('')}`).join('')}
              ${[67, 180].map(x => `<rect x="${x}" y="22" width="49" height="22" rx="2" fill="#34454e" stroke="#869296" stroke-width="2"/><path d="M${x + 24.5} 23 V43" stroke="#b6bfc0" stroke-width="3"/><path d="M${x + 5} 26 H${x + 19} M${x + 30} 26 H${x + 43}" stroke="#7f98a2" stroke-width="2"/>`).join('')}
              <path d="M9 64 H291" stroke="#f4f6f5" stroke-width="2"/>
            </svg>
          </span>
          <span class="acv-car-identity">Car <strong>${car}</strong></span>
          <span class="acv-car-priority">Priority <b>${priority(car)}</b></span>
          <span class="acv-selection">Selected</span>
        </button>`).join('')}
      </div>
    </div>
    <div aria-live="polite" aria-atomic="true">
    ${carSlots.map(car => `<section class="acv-car-evidence" id="acv-evidence-${car}" data-acv-panel="${car}" aria-labelledby="acv-heading-${car}" ${car === firstCar ? '' : 'hidden'}>
      <div class="nx-sectionhead"><h3 id="acv-heading-${car}">Car ${car} · Supporting evidence</h3><span class="nx-pill">Priority: ${priority(car)}</span></div>
      <dl class="acv-evidence-grid">
        <dt>Inspection priority</dt><dd>${priority(car)}</dd>
        <dt>Average positive temperature gap</dt><dd>${!recording ? 'Not calculated' : rows[car].average_positive_gap === null ? 'Unavailable' : rows[car].average_positive_gap.toFixed(4)}</dd>
        <dt>Usable readings</dt><dd>${recording ? rows[car].usable_rows.toLocaleString() : 'Not checked'}</dd>
        <dt>Data coverage</dt><dd>${!recording ? 'Not checked' : rows[car].evidence === 'unavailable' ? 'Insufficient data; not confirmed healthy' : 'Eligible readings available; completeness not guaranteed'}</dd>
      </dl>
      <h3>Car ${car}: temperature gap over time</h3>
      ${recording ? renderChart(recording, car) : '<p>No recording loaded. Analyse a file to see its temperatures.</p>'}
      ${recording && rows[car].layout === 'rich (provisional)' ? '<div class="nx-notice">Provisional cabin/target mapping. No confirmed information-valid flag is available for this layout.</div>' : ''}
    </section>`).join('')}
    </div>
  </section>`;
}

export function renderMethod() {
  return `<div class="nx-sectionhead"><h2>Average positive temperature gap</h2><span class="nx-pill">Fixed baseline · No fitted model</span></div>
  <p>Rule version: original-positive-gap-v1. This is our modelling choice, not a competition-mandated algorithm.</p>
  <ol class="nx-method">
    <li><strong>Check the recording</strong><p>Validate timestamps, car identifiers and supported fields. Reject unfamiliar layouts instead of guessing.</p></li>
    <li><strong>Select eligible readings</strong><p>Standard layout: Valid information, Automatic Cooling, and finite indoor and cooling-control temperatures. Rich layout: finite passenger-cabin and target temperatures during Full Cooling or Half Cooling. The rich mapping is provisional, with no confirmed validity flag.</p></li>
    <li><strong>Measure the gap</strong><p>Subtract target from indoor temperature. Negative gaps contribute zero. Average all eligible readings, including zero gaps. This averages samples, not elapsed time.</p></li>
    <li><strong>Order the cars</strong><p>Largest score first; exact ties use car ID. Missing scores remain unavailable and go last by ID. Entirely unscorable cases fail.</p></li>
  </ol>
  <h3>Recorded evaluation results</h3>
  <p>Previously user-run training-data results, not a new run in this interface or measured test performance.</p>
  <div class="nx-evidence"><div class="nx-metric"><strong>4 of 4</strong><span>Faulty car ranked first in initially held-aside cases 02, 03, 05 and 06</span></div><div class="nx-metric"><strong>5 of 6</strong><span>Faulty car ranked first across all six development cases</span></div></div>
  <p>Case 04 is the key error: Car 04 ranks first, while the labelled faulty Car 01 ranks second. The all-six mean official rank score is 0.9792. These cases informed exploration, so this is development evidence, not independent validation. This fixed rule has no fitted training stage.</p>
  <details><summary>Alternatives and limitations</summary><p>The time-weighted relative-gap challenger gave the same faulty-car ranks across these six cases. The original sample-average rule remains selected. Pressure, valves and peer comparisons are exploratory and do not affect predictions.</p><p>Case 04 has provisional field meanings and no usable temperature evidence for Cars 05–08. Units and control semantics remain incompletely documented. Test data was not used to tune the rule. Automated regression and fresh-environment installation checks have not been completed.</p></details>
  <h3>Competition requirements and sources</h3>
  <p>Export file_id and ranked_cars in acv_predictions.csv, preserving original filenames and all eight header car identifiers. The official rank score is (8 − (faulty-car rank − 1)) / 8.</p>
  <p><a href="https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/main/PS3/03_References/ACV/ACV_Subsystem_Info_Kit.md">Official ACV information kit</a> · <a href="https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/main/PS3/01_Problem_Statement_3_Specifications.md">Official PS3 specification</a></p>
  <p>Documentation conflict: the kit describes a required predict.py/code handoff; the main specification makes code optional and requires an app, demonstration video and predictions generated through the app. See acv/docs/SOURCE_NOTES.md for the recorded comparison.</p>`;
}

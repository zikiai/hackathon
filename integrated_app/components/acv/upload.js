const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let result = null, files = [], busy = false, message = '', selected = 0, evidenceRenderer;

export function renderUpload(renderer) {
  evidenceRenderer = renderer;
  const recording = result?.cases[selected];
  return `<section class="nx-detail" id="acv-live-workspace">
    ${recording ? `<header class="acv-recording-summary">
      <span class="nx-pill quiet">Analysis complete</span>
      <h2>${escape(recording.file_id)}</h2>
      <p>${recording.ranking.length} cars · ${recording.times.length.toLocaleString()} recorded timestamps · ${recording.ranking.filter(row => row.evidence === 'scored').length} cars with usable evidence</p>
      <p class="nx-small">${escape(recording.times[0].replace('T', ' '))} to ${escape(recording.times.at(-1).replace('T', ' '))} · Singapore time (SGT, UTC+8)</p>
    </header>` : '<h2>Analyse air-conditioning recordings</h2>'}
    <details class="acv-upload-controls" ${recording ? '' : 'open'}>
    <summary>${recording ? 'Change files' : 'Choose recordings'}</summary>
    <p>Upload original Excel cases to compare all eight cars. Your files are processed by the local Python server.</p>
    <div class="acv-file-picker">
      <input id="acv-files" class="acv-file-input" type="file" accept=".xlsx" multiple aria-label="Choose Excel recordings" aria-describedby="acv-selected-files" ${busy ? 'disabled' : ''}>
      <label for="acv-files" class="nx-action">${files.length ? 'Choose different files' : 'Choose Excel files'}</label>
      <span id="acv-selected-files" role="status">${files.length ? files.map(f => escape(f.name)).join(' · ') : 'No files selected'}</span>
    </div>
    <p class="nx-small">Up to 20 files, 100 MiB total. Keep original filenames and column headers.</p>
    <button type="button" class="nx-action nx-primary" data-acv-analyse ${busy || !files.length ? 'disabled' : ''}>${busy ? 'Analysing…' : 'Analyse cars'}</button>
    <p role="status" class="nx-notice">${escape(message || 'Choose recordings, then select Analyse cars.')}</p>
    </details>
    <div id="acv-live-results">${resultsMarkup()}</div>
  </section>`;
}
function resultsMarkup() {
  if (!result) return '';
  const recording = result.cases[selected];
  return `${result.cases.length > 1 ? `<label for="acv-recording">Displayed recording</label><select id="acv-recording">${result.cases.map((c,i) => `<option value="${i}" ${i === selected ? 'selected' : ''}>${escape(c.file_id)}</option>`).join('')}</select>` : ''}
    ${evidenceRenderer(recording)}
    <details><summary>Processing notes for this batch</summary>${result.warnings.length ? result.warnings.map(w => `<p>${escape(w)}</p>`).join('') : '<p>No pipeline warnings were reported.</p>'}</details>
    <h3>Download results</h3><p>All ${result.cases.length} analysed recording(s). Rankings are inspection priorities, not confirmed diagnoses.</p>
    <button type="button" class="nx-action nx-primary" data-acv-download>Download acv_predictions.csv</button>`;
}
function repaint() {
  const root = document.getElementById('acv-live-workspace');
  if (root) root.outerHTML = renderUpload(evidenceRenderer);
}
function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({name: file.name, content: reader.result.split(',')[1]});
    reader.onerror = () => reject(new Error(`Could not read ${file.name}. Select the file again.`));
    reader.readAsDataURL(file);
  });
}
document.addEventListener('change', event => {
  if (event.target.id === 'acv-files') {
    const chosen = Array.from(event.target.files);
    if (!chosen.length) return;
    files = chosen; result = null; selected = 0;
    message = files.length ? 'Files selected. Their contents will be validated during analysis.' : 'No files selected.';
    repaint();
  }
  if (event.target.id === 'acv-recording' && result) {
    selected = Number(event.target.value);
    repaint();
    document.getElementById('acv-recording')?.focus();
  }
});
document.addEventListener('click', async event => {
  if (event.target.closest('[data-acv-download]') && result) {
    const url = URL.createObjectURL(new Blob([result.csv], {type:'text/csv;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = 'acv_predictions.csv';
    document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  if (!event.target.closest('[data-acv-analyse]') || busy || !files.length) return;
  result = null;
  if (files.length > 20 || files.reduce((n, f) => n + f.size, 0) > 100 * 1024 * 1024) {
    message = 'Select at most 20 files, totalling no more than 100 MiB.'; repaint(); return;
  }
  busy = true; message = 'Reading and analysing your files. Large workbooks may take several minutes. Keep the local server running.'; repaint();
  try {
    const payload = await Promise.all(files.map(readFile));
    const response = await fetch('/api/acv/analyse', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({files:payload})});
    if (!(response.headers.get('content-type') || '').includes('application/json')) {
      throw new Error('Uploads need the ACV server. Stop the old static server and run: acv/.venv/bin/python integrated_app/server.py --port 8503');
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Analysis failed.');
    result = data; selected = 0; message = `Analysis complete: ${data.cases.length} recording(s). Select a car to review its evidence.`;
  } catch (error) {
    message = `${error.message} No results were exported. You can retry.`;
  } finally { busy = false; repaint(); }
});

export function renderChart(recording, car) {
  const readings = recording.charts[car];
  // User confirmed workbook times are Singapore local time. Make parsing
  // independent of the browser's timezone; preserve any explicit offset.
  const times = recording.times.map(t => new Date(/(?:Z|[+-]\d{2}:\d{2})$/i.test(t) ? t : `${t}+08:00`).getTime());
  const temperatureGap = readings.indoor.map((value, i) =>
    Number.isFinite(value) && Number.isFinite(readings.target[i]) ? value - readings.target[i] : null);
  if (!temperatureGap.some(Number.isFinite)) return '<p>No paired temperature readings are available to calculate a gap for this car.</p>';
  const peers = Object.entries(recording.charts).filter(([id]) => id !== car).map(([, series]) => series);
  const medianGap = temperatureGap.map((gap, i) => {
    if (!Number.isFinite(gap)) return null;
    const values = peers.filter(series => Number.isFinite(series.indoor[i]) && Number.isFinite(series.target[i]))
      .map(series => series.indoor[i] - series.target[i]).sort((a, b) => a - b);
    if (values.length < 3) return null;
    const middle = Math.floor(values.length / 2);
    return values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2;
  });
  const all = [...temperatureGap, ...medianGap].filter(Number.isFinite);
  let low = 0, high = 0;
  for (const value of all) { low = Math.min(low, value); high = Math.max(high, value); }
  low -= 1; high += 1;
  const gaps = times.slice(1).map((t,i) => t-times[i]).sort((a,b) => a-b);
  const interval = gaps.length ? gaps[Math.floor(gaps.length/2)] : 0;
  const x = i => 55 + (times[i]-times[0]) / (times.at(-1)-times[0] || 1) * 700;
  const y = value => 210 - (value-low)/(high-low)*175;
  function path(values) {
    let pen = false;
    return values.map((value,i) => {
      if (!Number.isFinite(value)) { pen = false; return ''; }
      if (i && times[i]-times[i-1] > interval*1.5) pen = false;
      const part = `${pen ? 'L':'M'}${x(i).toFixed(1)},${y(value).toFixed(1)}`; pen = true; return part;
    }).join(' ');
  }
  return `<svg class="acv-temperature-chart" viewBox="0 0 800 265" role="img" aria-label="Car ${escape(car)} temperature gap compared with the median gap of other cars over recorded time">
    ${[0,.25,.5,.75,1].map(f => `<line x1="55" x2="755" y1="${210-f*175}" y2="${210-f*175}" stroke="currentColor" opacity=".15"/><text x="48" y="${214-f*175}" text-anchor="end">${(low+f*(high-low)).toFixed(1)}</text>`).join('')}
    <line x1="55" x2="755" y1="${y(0)}" y2="${y(0)}" stroke="currentColor" stroke-dasharray="5 3" opacity=".7"/>
    <path d="${path(temperatureGap)}" fill="none" stroke="#c05a16" stroke-width="1.5"/>
    <path d="${path(medianGap)}" fill="none" stroke="#007f86" stroke-width="1.5" stroke-dasharray="7 3"/>
    <text x="55" y="18">Indoor minus target · temperature gap (units unconfirmed)</text>
    <text x="55" y="235">${escape(recording.times[0].replace('T',' '))}</text>
    <text x="755" y="255" text-anchor="end">${escape(recording.times.at(-1).replace('T',' '))}</text>
  </svg><p><strong>Orange solid:</strong> this car’s gap. <strong>Teal dashed:</strong> median gap of the other cars. Grey dashed: zero.</p>
  <p class="nx-small">Each gap is indoor temperature minus that car’s own target. The median is the middle value at the same timestamp, excluding this car; at least three other cars need finite temperature pairs. Orange above teal means this car is further above its own target than its peers. Negative gaps are retained. This comparison includes all operating modes, not just valid cooling readings, and is descriptive only; it does not change the ranking. The ranking averages nonnegative gaps over eligible cooling readings. Missing pairs and gaps over 1.5 times the median recording interval break the lines. Singapore time (SGT, UTC+8).</p>
  ${medianGap.some(Number.isFinite) ? '' : '<p>No peer median is available: fewer than three other cars have paired readings at the selected car’s recorded points.</p>'}`;
}

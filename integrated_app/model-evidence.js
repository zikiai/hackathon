const metrics = {rail:'Macro F1',door:'IoU-weighted F1',acv:'Linear rank-decay score',shm:'max(0, 1 − MAPE)'};
let results = {};
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// Cloud evaluation jobs can publish this small artifact beside the app.
// Scores must come from labelled training-data evaluations, not unlabelled tests.
export async function loadEvaluationResults(){
  try{
    const response = await fetch('./evaluation-results.json', {cache:'no-store'});
    if(!response.ok)throw new Error('Results unavailable');
    const incoming = await response.json();
    const validated = {};
    for(const key of Object.keys(metrics)){
      const r = incoming[key];
      if(!r)continue;
      if(r.score !== null && (typeof r.score !== 'number' || !Number.isFinite(r.score) || r.score < 0 || r.score > 1))continue;
      if(!['model','evaluation','rationale'].every(field => typeof r[field] === 'string' && r[field].trim()))continue;
      validated[key] = r;
    }
    results = validated;
    return true;
  }catch{
    results = {};
    return false;
  }
}

export function renderModelEvidence(component){
  const r = results[component];
  const score = r?.score;
  return `<h2>${escape(r?.model || 'Evaluation pending')}</h2>
    <h3 class="nx-spaced">Training-data results</h3>
    <div class="nx-evidence"><div class="nx-metric"><strong>${typeof score === 'number' ? score.toFixed(4) : 'Pending'}</strong><span>${escape(metrics[component])} · grading score</span></div></div>
    <p>${escape(r?.evaluation || 'Results will appear here when the evaluation results file is available.')}</p>
    <p class="nx-small">Scores are derived from labelled training data, not the competition test set.</p>
    <h3 class="nx-spaced">${score == null ? 'Model approach' : 'Why we chose this model'}</h3>
    <p>${escape(r?.rationale || 'The model choice and rationale will be supplied with the evaluation results.')}</p>`;
}

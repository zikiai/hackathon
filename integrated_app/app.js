import { loadEvaluationResults, renderModelEvidence } from './model-evidence.js';
import {renderCloudUpload,restoreResults} from './cloud-client.js';
import { predictionDownloads } from './prediction-downloads.js';
import * as rail from './components/rail/index.js';
import * as door from './components/door/index.js';
import * as acv from './components/acv/index.js?v=acv-integrated-1';
import {getResult as getAcvResult} from './components/acv/upload.js';
import * as shm from './components/shm/index.js?v=shm-integrated-1';
const components={rail,door,acv,shm};
const modules=Object.fromEntries(Object.entries(components).map(([key,value])=>[key,value.config]));
const root=document.getElementById('nx-ops'),content=root.querySelector('#nx-content');
let state={page:'review',module:'rail',normal:false,reviewed:{},notes:{},feedback:{},exportOpen:false,message:''};

const design={density:'Comfortable',corners:14,guidance:true};
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const key=()=>components[state.module].getRecords?state.module+':'+selectedRecord().id:state.module+(state.normal?'-normal':'');
function save() {} // In-memory prototype; backend persistence is a separate integration task.
const action=(label,attrs='',primary=false)=>`<button type="button" class="cursor-interaction nx-action ${primary?'nx-primary':''}" ${attrs}>${label}</button>`;
function cards(){return `<div class="nx-components" aria-label="Components">${Object.entries(modules).map(([k,m])=>`<button type="button" class="cursor-interaction nx-component" data-module="${k}" aria-pressed="${state.module===k}"><strong>${m.name}</strong></button>`).join('')}</div>`;}
function title(kicker,heading,sub){return `<div class="nx-title nx-centered"><div><div class="nx-kicker">${kicker}</div><h1>${heading}</h1><p>${sub}</p></div></div>`;}
function stats(){return components[state.module].renderInterpretation(state);}
function exports(){const output=predictionDownloads[state.module];return `<section class="nx-export nx-download-bar" aria-label="Download predictions"><div class="nx-download-file"><span class="nx-file-icon" aria-hidden="true">CSV</span><div><strong>${output?escape(output.filename):'Predictions unavailable'}</strong><p>${output?output.count+' '+escape(output.unit)+' · Ready to download':'This component’s results are not ready yet.'}</p></div></div><div class="nx-download-actions">${output?action('↓ &nbsp; Download CSV','data-download="csv"',true):''}<button type="button" class="nx-dismiss" data-close-export aria-label="Close download panel">×</button></div>${state.message?`<p class="nx-download-status" role="status">${escape(state.message)}</p>`:''}</section>`;}
function selectedRecord(){const records=components[state.module].getRecords();return records.find(r=>r.id===state.selected?.[state.module])||records[0];}
function review(){if(!components[state.module].getRecords)return legacyReview();const component=components[state.module],records=component.getRecords(),r=selectedRecord(),done=state.reviewed[key()];return title('Operations / Review','Know what needs a closer look.','Inspect the statistics, plan the check, and record your review.')+`<div class="nx-toolbar">${action('New analysis','data-go="analyze"',true)}${action('Download predictions','data-export')}</div>`+cards()+(state.exportOpen?exports():'')+`<div class="nx-sectionhead"><h2>${modules[state.module].name}</h2><span class="nx-count">${records.length} findings</span></div><div class="nx-workspace"><section class="nx-list" aria-label="Reference findings">${records.map(item=>`<button class="cursor-interaction nx-record" data-evidence-record="${escape(item.id)}" aria-pressed="${item.id===r.id}"><span class="nx-pill ${item.prediction==='Normal'?'quiet':''}">${state.reviewed[state.module+':'+item.id]?'Reviewed':escape(item.prediction)}</span><strong>${escape(item.title)}</strong><p>${escape(item.file)}</p></button>`).join('')}</section><article class="nx-detail" aria-label="Selected finding"><span class="nx-pill ${r.prediction==='Normal'?'quiet':''}">${done?'Reviewed':escape(r.prediction)}</span><h2>${escape(r.title)}</h2><h3 class="nx-spaced">1. Interpretation of statistics</h3>${component.renderStatistics(r)}<div class="nx-step"><h3>2. Recommendation to the technician</h3><p>${escape(component.recommendation(r))}</p></div><hr class="nx-divider"><label for="nx-note"><strong>3. Review note</strong></label><textarea id="nx-note" placeholder="Record your observation, checks and follow-up…">${escape(state.notes[key()]||'')}</textarea>${action(done?'Reopen review':'Mark as reviewed','data-review',!done)}<p class="nx-toast" role="status">${escape(state.message)}</p></article></div>`;}
function reportText(){const component=components[state.module];if(!component.getRecords)return legacyReportText();return ['NEBULAX — REFERENCE FINDINGS REPORT','Reference examples only. Not a complete competition submission or live analysis.','Component: '+modules[state.module].name,'',...component.getRecords().flatMap(r=>['Recording: '+r.file,'Source: '+r.provenance,'Prediction: '+r.prediction,'Interpretation of statistics:',...component.statisticsText(r),'Technician recommendation: '+component.recommendation(r),'Review status: '+(state.reviewed[state.module+':'+r.id]?'Reviewed':'Not reviewed'),'Review note: '+(state.notes[state.module+':'+r.id]||'None'),''])].join('\n');}

function legacyReview(){const m=modules[state.module],id=key(),done=state.reviewed[id],normal=state.normal;return title('Operations / Review','Know what needs a closer look.','Understand the finding. Record your judgment. Take the results with you.')+`<div class="nx-toolbar">${action('New analysis','data-go="analyze"',true)}${action('Download predictions','data-export')}<span class="nx-small">${m.name} · Sample batch</span></div>`+cards()+(state.exportOpen?exports():'')+`<div class="nx-sectionhead"><h2>${m.name}</h2><span class="nx-count">${state.module==='rail'?'2 sample recordings':'1 sample recording'}</span></div><div class="nx-workspace"><section class="nx-list" aria-label="Sample recordings"><button class="cursor-interaction nx-record" data-record="finding" aria-pressed="${!normal}"><span class="nx-pill ${state.reviewed[state.module]?'quiet':''}">${state.reviewed[state.module]?'Reviewed':'Needs review'}</span><strong>${m.title}</strong><p>${m.file}</p></button>${state.module==='rail'?`<button class="cursor-interaction nx-record" data-record="normal" aria-pressed="${normal}"><span class="nx-pill quiet">${state.reviewed['rail-normal']?'Reviewed':'Normal prediction'}</span><strong>Normal classification</strong><p>rail-example-02.csv</p></button>`:''}</section><article class="nx-detail" aria-label="Selected finding"><span class="nx-pill ${done||normal?'quiet':''}">${done?'Reviewed':normal?'Normal prediction':'Review suggested'}</span><h2>${normal?'No corrugation pattern detected':m.title}</h2><p>${normal?'The model classified this example recording as Normal.':m.finding}</p><div class="nx-step"><h3>Suggested next step</h3><p>${normal?'Include this result in the routine review of the recording.':m.next}</p></div><p class="nx-small">${m.scope}</p><details ${design.guidance?'open':''}><summary class="cursor-interaction">Interpret this finding · Numbers &amp; context</summary>${stats()}<p>${m.why}</p></details><hr class="nx-divider"><label for="nx-note" class="nx-small">Review note</label><textarea id="nx-note" placeholder="What did you observe? Include confirmed findings or corrections…">${escape(state.notes[id]||'')}</textarea><div class="nx-inline">${action(done?'Reopen review':'Mark as reviewed','data-review',!done)}</div>${state.feedback[id]?`<div class="nx-notice"><strong>Feedback saved in this preview</strong><p>Next: an engineer verifies the observation before it enters model development.</p></div>`:''}<p class="nx-toast" role="status">${escape(state.message)}</p></article></div>`;}
function analyze(){const m=modules[state.module];return title('Analysis / New','Start with a record.','Upload a CSV record to predict its condition.')+`<div class="nx-flow"><b>01 Choose component</b><span>02 Upload record</span><span>03 Generate predictions</span></div><section class="nx-detail"><label for="nx-module">Component</label><select id="nx-module">${Object.entries(modules).map(([k,v])=>`<option value="${k}" ${state.module===k?'selected':''}>${v.name}</option>`).join('')}</select><h2>Upload ${escape(m.name.toLowerCase())} records</h2><p>${escape(m.format)}</p><div class="nx-upload-zone"><div class="nx-upload-icon" aria-hidden="true">↑</div><h3>Upload your CSV ${state.module==='door'?'record':'records'}</h3><p class="nx-small">${state.module==='door'?'Select one continuous door recording.':'Select one or more CSV files to analyse together.'}</p><label class="nx-upload-button"><span>Browse files</span><input id="nx-upload" type="file" accept=".csv,text/csv" ${state.module==='door'?'':'multiple'} aria-label="Browse CSV files" aria-describedby="nx-upload-status"></label><p id="nx-upload-status" class="nx-upload-status" role="status">CSV format · No files selected</p></div><div class="nx-sectionhead"><div><h3>Predicted result</h3><p>${escape(m.output)}</p></div>${action('Output predicted result','disabled aria-describedby="nx-processing-status"',true)}</div><p id="nx-processing-status" class="nx-small">Prediction service not connected yet. Once connected, this will process your uploaded records and open their results in Review findings → ${escape(m.name)}.</p></section>`;}
function method(){return title('Model evidence','How the models performed.','Training-data results and the reasoning behind each model.')+cards()+`<section class="nx-detail">${renderModelEvidence(state.module)}</section>`;}
function learning(){return title('AI improvement','Learn from findings.','AI-assisted refinement')+`<section class="nx-detail"><h2>From findings to possible improvements</h2><p>The planned AI capability can process verified findings and technician feedback, identify recurring prediction errors, and suggest refinements to the features, model or code.</p><p>Suggested changes would be tested and reviewed before adoption. AI processing is not connected yet.</p></section>`;}
function legacyReportText(){const m=modules[state.module],keys=state.module==='rail'?['rail','rail-normal']:[state.module];return ['NEBULAX — SAMPLE FINDINGS REPORT','DESIGN PREVIEW ONLY — NOT FOR OPERATIONAL USE OR COMPETITION SUBMISSION','Component: '+m.name,'',...keys.flatMap(id=>['Recording: '+(id==='rail-normal'?'rail-example-02.csv':m.file),'Finding: '+(id==='rail-normal'?'Normal classification':m.title),'Interpretation: '+(id==='rail-normal'?'Illustrative adjusted scores: Normal 0.81, Side I 0.12, Side II 0.07.':state.module==='rail'?'Illustrative adjusted scores: Normal 0.21, Side I 0.68, Side II 0.11.':state.module==='door'?'Illustrative interval: 12.4–15.8 s; duration 3.4 s.':state.module==='acv'?'Illustrative car ranking: 3,6,1,8,2,5,4,7.':'Numerical estimate awaiting integration.'),m.why,'Review status: '+(state.reviewed[id]?'Reviewed':'Not reviewed'),'Review note: '+(state.notes[id]||'None'),'']),state.module==='rail'?'Actual validation context: macro F1 0.8234; Side I recall 11/14 (78.6%); precision 11/21 (52.4%). This does not validate the illustrative findings.':'Model and measured validation results awaiting team integration.'].join('\n');}
function download(kind){
 const output=predictionDownloads[state.module];
 if(kind!=='csv'||!output)return;
 const link=document.createElement('a');link.href=output.url;link.download=output.filename;
 root.appendChild(link);link.click();link.remove();
 state.message='Download requested: '+output.filename;
}
function render(){root.style.setProperty('--nx-radius',design.corners+'px');root.classList.toggle('nx-compact',design.density==='Compact');root.querySelectorAll('[data-page]').forEach(b=>{if(b.dataset.page===state.page)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});content.innerHTML=state.page==='review'?review():state.page==='analyze'?analyze():state.page==='learning'?learning():method();}
root.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;state.message='';if(b.dataset.page||b.dataset.go){state.page=b.dataset.page||b.dataset.go;if(state.page==='method')await loadEvaluationResults();}else if(b.dataset.module){state.module=b.dataset.module;state.normal=false;state.exportPreview=null;}else if(b.dataset.evidenceRecord){state.selected={...(state.selected||{}),[state.module]:b.dataset.evidenceRecord};}else if(b.dataset.record)state.normal=b.dataset.record==='normal';else if(b.hasAttribute('data-review')){state.reviewed[key()]=!state.reviewed[key()];state.message=state.reviewed[key()]?'Review recorded in this preview.':'Review reopened.';}else if(b.hasAttribute('data-feedback')){const note=(state.notes[key()]||'').trim();if(!note)state.message='Add a review note before collecting improvement feedback.';else{state.feedback[key()]={module:state.module,file:state.normal?'rail-example-02.csv':modules[state.module].file,note};state.message='Added to AI improvement → Awaiting verification. No model or code was changed.';}}else if(b.hasAttribute('data-export'))state.exportOpen=!state.exportOpen;else if(b.hasAttribute('data-close-export'))state.exportOpen=false;else if(b.dataset.download)download(b.dataset.download);else return;render();save();});
root.addEventListener('change',e=>{if(e.target.id==='nx-upload'){const files=Array.from(e.target.files||[]);const status=root.querySelector('#nx-upload-status');status.textContent=files.length?files.map(f=>f.name).join(', ')+' — selected locally; not processed.':'No record selected.';return;}if(e.target.id==='nx-module'){state.module=e.target.value;state.normal=false;render();save();}});root.addEventListener('input',e=>{if(e.target.id==='nx-note')state.notes[key()]=e.target.value;});
// Component-only integration: preserve the shared shell and all other workflows.
const sharedReview = review, sharedAnalyze = analyze;
review = function () {
  if (state.module !== 'acv' || acv.getRecords().length) return sharedReview();
  return title('Operations / Review','Know what needs a closer look.','Inspect the statistics, plan the check, and record your review.')+
    `<div class="nx-toolbar">${action('New analysis','data-go="analyze"',true)}</div>`+cards()+
    '<section class="nx-detail"><h2>Air conditioning</h2><p>No recording analysed yet. Upload an Excel record in New analysis to generate car rankings and supporting evidence.</p></section>';
};
analyze = function () {
  if (state.module !== 'acv') return sharedAnalyze();
  return title('Analysis / New','Start with a record.','Upload an Excel record to compare cooling performance.')+
    '<div class="nx-flow"><b>01 Choose component</b><span>02 Upload record</span><span>03 Generate predictions</span></div>'+
    `<label for="nx-module">Component</label><select id="nx-module">${Object.entries(modules).map(([k,v])=>`<option value="${k}" ${state.module===k?'selected':''}>${v.name}</option>`).join('')}</select>`+
    acv.renderWorkspace();
};
document.addEventListener('acv-analysis-complete', () => {
  const result = getAcvResult();
  if (!result) return;
  if (predictionDownloads.acv) URL.revokeObjectURL(predictionDownloads.acv.url);
  predictionDownloads.acv = {filename:'acv_predictions.csv', count:result.cases.length, unit:'recordings',
    url:URL.createObjectURL(new Blob([result.csv],{type:'text/csv;charset=utf-8'}))};
  state.module='acv'; state.page='review'; state.exportOpen=false;
  state.selected={...(state.selected||{}),acv:result.cases[0].file_id};
  render();
});
document.addEventListener('acv-analysis-cleared', () => {
  if (predictionDownloads.acv) URL.revokeObjectURL(predictionDownloads.acv.url);
  delete predictionDownloads.acv;
  for (const entries of [state.notes,state.reviewed]) {
    for (const id of Object.keys(entries)) if (id.startsWith('acv:')) delete entries[id];
  }
});
analyze = function () {
  const m=modules[state.module];
  return title('Analysis / New','Start with a record.','Upload a record to predict its condition.')+
    '<div class="nx-flow"><b>01 Choose component</b><span>02 Upload record</span><span>03 Generate predictions</span></div>'+
    `<label for="nx-module">Component</label><select id="nx-module">${Object.entries(modules).map(([k,v])=>`<option value="${k}" ${state.module===k?'selected':''}>${v.name}</option>`).join('')}</select><p class="nx-small">${escape(m.format)}</p>`+renderCloudUpload(state.module);
};
document.addEventListener('cloud-results', event => {
  const {component,result,navigate}=event.detail;
  if(predictionDownloads[component]?.url.startsWith('blob:'))URL.revokeObjectURL(predictionDownloads[component].url);
  const filename=component==='acv'?'acv_predictions.csv':component==='shm'?'shm_predictions.csv':component==='door'?'door_predictions.csv':'rail_predictions.csv';
  predictionDownloads[component]={filename,url:URL.createObjectURL(new Blob([result.csv],{type:'text/csv;charset=utf-8'})),count:component==='acv'?result.cases.length:result.records.length,unit:component==='door'?'movements':'recordings'};
  if(navigate){state.module=component;state.page='review';state.exportOpen=false;}
  state.selected={...(state.selected||{}),[component]:components[component].getRecords()[0].id};
  if(state.page==='review')render();
});
render();
restoreResults();
loadEvaluationResults().then(()=>{if(state.page==='method')render();});

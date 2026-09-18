// SHM UI only. Stress features and inference run in the Python pipeline.
export const config = {
  name:'Structural health',short:'Structure',icon:'activity',status:'Model available · local server required',
  input:'One or more stress recordings',format:'CSV, one numeric column, no header. Training examples have 581,120 readings.',
  output:'One cumulative fatigue-damage estimate per recording',title:'Structural loading assessment',
  finding:'Upload a recording to obtain a model estimate.',scope:'No operational safety clearance or remaining-life estimate.',
  next:'Review the estimate in its engineering context.',why:'The damage index is not a failure probability or a percentage damaged.',
  evidence:'Held-out grouped validation averaged 2.020% MAPE on the development data.',file:'No recording uploaded'
};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let files=[],results=[],errors=[],busy=false,completed=0,selected=0,notes={},notice='';
const number=(x,d=3)=>Number(x).toLocaleString(undefined,{maximumFractionDigits:d});
const btn=(label,id,primary=false,disabled=false)=>`<button type="button" class="nx-action ${primary?'nx-primary':''}" id="${id}" ${disabled?'disabled':''}>${label}</button>`;
export function renderAnalysis(){return '<section id="shm-live" aria-label="Structural health analysis"></section>';}
export function renderInterpretation(){return '<p>Open New analysis to upload real stress recordings. No sample damage estimate is shown.</p>';}
export function renderMethod(){return `<div class="nx-sectionhead"><h2>Structural health methodology</h2><span class="nx-pill quiet">Measured development results</span></div>
<p>One stress recording becomes 21 model inputs describing stress levels, variation and rainflow cycles. A Ridge regression model (alpha = 1) learns a multiplicative correction to a fifth-power cycle summary. Known damage is the training target, never an input to inference.</p>
<div class="nx-evidence"><div class="nx-metric"><strong>2.020%</strong><span>Average grouped-validation MAPE</span></div><div class="nx-metric"><strong>5.934%</strong><span>Largest observed underestimate across those runs</span></div></div>
<p>The 64 labelled recordings were evaluated using three five-fold partitions. Flagged similar recordings were kept together. Each prediction was made without training on that recording, but model development repeatedly used these same data. Similarity groups are precautionary, not verified operating sessions.</p>
<div class="nx-notice">These are results for the 21-input alpha=1 model, not hidden-Test accuracy. Average error is not a confidence interval or a bound on future errors.</div>
<h3 class="nx-spaced">What the data means</h3><p>Rainflow counting identifies repeated stress cycles. Larger cycle ranges receive more emphasis in the power-sum features. The model estimates the supplied cumulative fatigue-damage reference, not probability of failure or remaining life.</p>
<h3 class="nx-spaced">Checks and experiments</h3><p>No invalid readings or identical recordings were found in the 64-file audit. Feature reduction and five one-term nonlinear extensions did not establish a convincing improvement over the deployed candidate. The largest recurring underestimates included train41.csv and train12.csv.</p>`;}

function stressChart(r){
 const data=r.overview,w=720,h=180,left=65,right=20,top=12,bottom=30;
 const lo=Math.min(...data.map(p=>p.minimum)),hi=Math.max(...data.map(p=>p.maximum));
 const x=p=>left+p.sample/Math.max(1,r.readings-1)*(w-left-right);
 const y=v=>top+(hi-v)/Math.max(1e-12,hi-lo)*(h-top-bottom);
 const line=k=>data.map(p=>`${x(p).toFixed(2)},${y(p[k]).toFixed(2)}`).join(' ');
 return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Stress minimum and maximum by recording position" style="width:100%;color:var(--nx-accent)"><title>Stress envelope, from ${esc(number(lo))} to ${esc(number(hi))}</title>
 <line x1="${left}" y1="${h-bottom}" x2="${w-right}" y2="${h-bottom}" stroke="var(--nx-line)"/>
 <polyline points="${line('maximum')}" fill="none" stroke="currentColor" stroke-width="1.3"/>
 <polyline points="${line('minimum')}" fill="none" stroke="var(--nx-muted)" stroke-width="1.1"/>
 <g fill="var(--nx-muted)" font-size="11"><text x="2" y="20">${esc(number(hi))}</text><text x="2" y="${h-bottom}">${esc(number(lo))}</text><text x="${left}" y="${h-8}">0</text><text x="${w-right}" y="${h-8}" text-anchor="end">${r.readings-1} samples</text></g></svg>`;
}
function cycleChart(r){
 const max=Math.max(...r.cycles.map(c=>c.count),1);
 return `<div class="nx-tablewrap"><table class="nx-results"><caption>Cycle range in source stress units; weighted cycle counts</caption><thead><tr><th>Range</th><th>Frequency</th><th>Count</th></tr></thead><tbody>${r.cycles.map(c=>`<tr><td>${number(c.low,2)}–${number(c.high,2)}</td><td style="width:50%"><div class="nx-track"><div style="width:${100*c.count/max}%"></div></div></td><td>${number(c.count,1)}</td></tr>`).join('')}</tbody></table></div>`;
}
function details(){
 const r=results[selected]||results[0];if(!r)return '';
 const median=results.length>1?[...results].map(x=>x.prediction).sort((a,b)=>a-b):[];
 const mid=median.length? (median[Math.floor((median.length-1)/2)]+median[Math.floor(median.length/2)])/2:0;
 const comparable=results.length>1&&results.every(x=>x.readings===r.readings);
 const relative=comparable?`<p>For context, the middle estimate in these ${results.length} uploaded recordings is <strong>${number(mid,4)}</strong>. This recording is ${r.prediction>mid?'above':r.prediction<mid?'below':'at'} that value. This is a comparison within your uploads, not a maintenance threshold. Operating conditions may differ.</p>`:'';
 return `<article class="nx-detail shm-result"><div class="shm-eyebrow">RECORDING INSIGHT</div><div class="nx-sectionhead"><h2>Your result: ${esc(r.file_id)}</h2><span class="nx-pill quiet">Recording processed</span></div>
 <div class="nx-evidence"><div class="nx-metric shm-damage"><span class="shm-eyebrow">THIS RECORDING</span><strong>${number(r.prediction,4)}</strong><span>Estimated fatigue damage · reference index</span></div><div class="nx-step"><h3>What does this number mean?</h3><p>It summarises estimated fatigue damage from this recording’s repeated loading. Higher values represent more estimated damage on the same reference scale.</p></div></div>
 <p><strong>${number(r.prediction,4)} does not mean ${number(r.prediction*100,1)}% physically damaged.</strong> The number alone cannot tell you whether the train is safe, needs repair, or how long it will last.</p>
 ${relative}
 <div class="nx-step"><h3>What to do next</h3><ol><li>Check that <strong>${esc(r.file_id)}</strong> is the recording you intended to review.</li><li>Look at the loading overview below. Note any part you want to discuss or check against operating records.</li><li>Add an observation and download the findings report for the responsible engineer to interpret with the asset history and maintenance criteria.</li></ol></div>
 ${r.warnings.map(w=>`<div class="nx-notice">${esc(w)}</div>`).join('')}
 <h3 class="nx-spaced">How did the loading change?</h3><p>The two lines show the highest and lowest stress in each short section. A wider gap means stress varied more within that section; it is not automatically a fault.</p>${stressChart(r)}
 <p class="nx-small">Left to right: progress through the recording. Teal: highest stress; grey: lowest stress. Each section retains its extremes, so this is not the full signal. Units are those of the source data; timing information is not supplied.</p>
 <details><summary><strong>Understand repeated loading</strong></summary><p>Loading rises and falls as the train operates. We count these changes as cycles. Their size and frequency help estimate fatigue. A larger cycle means a bigger stress swing; it does not by itself indicate a fault.</p>${cycleChart(r)}<p class="nx-small">Bars show how often each size of stress change occurred. The total is ${number(r.features.rf_cycle_count,1)} cycles; a partly completed cycle counts as half. These bars describe loading, not the damage caused by each band.</p></details>
 <details><summary>Technical measurements</summary><div class="nx-tablewrap"><table class="nx-results"><tbody>${Object.entries(r.features).map(([k,v])=>`<tr><th>${esc(k)}</th><td>${esc(number(v,6))}</td></tr>`).join('')}</tbody></table></div><p class="nx-small">Model ${esc(r.model_version)}. File checks found one numeric column without missing or infinite readings; those checks do not assess structural safety.</p></details>
 <label for="shm-note"><strong>Your observation</strong></label><textarea id="shm-note" placeholder="For example: Confirm whether the large stress changes coincide with a known operating event.">${esc(notes[r.file_id]||'')}</textarea>
 <p class="nx-small">Your note is included in the findings report, not used as a training label. Download it before leaving; reloading clears this session.</p></article>`;
}
function view(){
 const complete=!busy&&files.length>0&&results.length===files.length&&errors.length===0;
 return `<section class="nx-detail shm-upload-card"><div class="shm-eyebrow">START YOUR REVIEW</div><div class="nx-sectionhead"><h2>Add your recording</h2></div>
 <p>Choose the sensor recording you want to understand. You can add several files to review them together.<details><summary>Which files can I use?</summary><p>Use stress recordings saved as CSV: one numeric column, no header, up to 32 MiB per file. Do not upload a damage-label or predictions file.</p></details></p>
 <div id="shm-drop" class="shm-drop ${busy?'is-busy':''}"><span class="shm-upload-icon" aria-hidden="true"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/></svg></span><div><strong>${busy?'Reading your recordings…':'Drop stress recordings here'}</strong><p class="nx-small">CSV files · up to 32 MiB each</p></div><input id="shm-files" type="file" accept=".csv" multiple hidden ${busy?'disabled':''}>${btn(files.length?'Change files':'Browse files','shm-choose',false,busy)}</div>
 <p class="nx-small">${files.length?`${files.length} selected: ${esc(files.slice(0,3).map(f=>f.name).join(', '))}${files.length>3?' …':''}`:'No recordings selected yet.'}</p>
 <div class="nx-inline">${btn(busy?'Reading your recording…':'Review loading','shm-analyse',true,busy||!files.length)}${btn('Download prediction CSV','shm-export',false,!complete)}${btn('Download findings report','shm-report',false,!complete)}</div>
 ${busy?`<progress class="shm-progress" max="${files.length}" value="${completed}" aria-label="Recordings processed"></progress>`:''}<p class="nx-toast" role="status" aria-live="polite">${busy?`Processed ${completed} of ${files.length}. Processing can take several seconds per recording.`:esc(notice)}</p>
 ${errors.map(e=>`<div class="nx-notice" role="alert">${esc(e)}</div>`).join('')}
 ${errors.length?'<p>Resolve the issue shown above and try again. Download becomes available when every selected recording has a result.</p>':''}
 </section>
 ${results.length?`<div class="nx-workspace nx-spaced"><section class="nx-list" aria-label="Analysed recordings">${results.map((r,i)=>`<button type="button" class="nx-record" data-shm-record="${i}" aria-pressed="${selected===i}"><strong>${esc(r.file_id)}</strong><p>Estimated fatigue damage: ${number(r.prediction,4)}</p></button>`).join('')}</section>${details()}</div>`:''}`;
}
function draw(){const host=document.getElementById('shm-live');if(host)host.innerHTML=view();}
function base64(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(',')[1]);r.onerror=()=>reject(new Error('Could not read the file.'));r.readAsDataURL(file);});}
function validate(r,name){
 if(r.file_id!==name||!Number.isFinite(r.prediction)||r.prediction<=0||!Array.isArray(r.overview)||!r.overview.length||!Array.isArray(r.cycles)||!r.features||!Array.isArray(r.warnings)||typeof r.model_version!=='string')throw new Error('Server returned an incomplete or invalid SHM result.');
 return r;
}
async function analyse(){
 if(busy||!files.length)return;
 results=[];errors=[];selected=0;completed=0;notice='';
 if(new Set(files.map(f=>f.name)).size!==files.length){errors=['Duplicate filenames: remove duplicates before analysis.'];draw();return;}
 if(files.some(f=>!f.name.toLowerCase().endsWith('.csv')||f.size===0||f.size>32*1024*1024)){errors=['Choose nonempty CSV files no larger than 32 MiB each.'];draw();return;}
 busy=true;draw();
 for(const file of files){
  try{
   const response=await fetch('/api/shm/analyse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:file.name,data:await base64(file)})});
   const type=response.headers.get('content-type')||'';
   if(!type.includes('application/json'))throw new Error('SHM backend is unavailable. Start shm/ui/serve.py instead of a static HTTP server.');
   const body=await response.json();if(!response.ok)throw new Error(body.error||'Analysis failed.');
   const r=validate(body,file.name);
   if(results.length&&r.model_version!==results[0].model_version)throw new Error('Model version changed during this batch. Analyse the complete batch again.');
   results.push(r);
  }catch(e){const message=/failed to fetch|networkerror|load failed/i.test(e.message)?'Connection to the Python server was lost. Keep the terminal running shm/ui/serve.py open, open http://127.0.0.1:8503, then retry. If it happens again, check the terminal error. This does not mean the Test file is invalid.':e.message;errors.push(file.name+': '+message);}
  completed++;draw();
 }
 busy=false;notice=errors.length?'Batch incomplete. See the details below.':`All ${results.length} recordings analysed. Predictions are ready to download.`;draw();
}
function download(name,text,mime){const u=URL.createObjectURL(new Blob([text],{type:mime}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
function exportBatch(report=false){
 if(busy||!files.length||errors.length||results.length!==files.length)return;
 if(new Set(results.map(r=>r.file_id)).size!==files.length||files.some(f=>!results.some(r=>r.file_id===f.name)))return;
 if(report){download('shm_findings.txt',['SHM FINDINGS — MODEL ESTIMATES FOR ENGINEERING REVIEW','Not a safety clearance or remaining-life assessment.',...results.flatMap(r=>['',`Recording: ${r.file_id}`,`Estimated damage: ${r.prediction}`,`Model: ${r.model_version}`,`Readings: ${r.readings}`,`Review note: ${notes[r.file_id]||'None'}`,...r.warnings])].join('\n'),'text/plain');}
 else {const quote=s=>'"'+String(s).replaceAll('"','""')+'"';download('shm_predictions.csv','file_id,prediction\n'+results.map(r=>`${quote(r.file_id)},${r.prediction}`).join('\n')+'\n','text/csv');}
}
export function mountAnalysis(){
 const host=document.getElementById('shm-live');if(!host)return;
 // Property handlers replace previous handlers when navigation remounts the page.
 host.onclick=e=>{const b=e.target.closest('button');if(!b)return;
  if(b.id==='shm-choose')document.getElementById('shm-files').click();else if(b.id==='shm-analyse')analyse();else if(b.id==='shm-export')exportBatch();else if(b.id==='shm-report')exportBatch(true);
  else if(b.dataset.shmRecord!==undefined){selected=Number(b.dataset.shmRecord);draw();}};
 const choose=chosen=>{if(busy)return;files=Array.from(chosen);results=[];errors=[];notice='';selected=0;draw();};
 host.onchange=e=>{if(e.target.id==='shm-files')choose(e.target.files);};
 host.ondragover=e=>{if(e.target.closest('#shm-drop')){e.preventDefault();if(!busy)document.getElementById('shm-drop').classList.add('is-over');}};
 host.ondragleave=e=>{if(e.target.closest('#shm-drop'))document.getElementById('shm-drop').classList.remove('is-over');};
 host.ondrop=e=>{if(e.target.closest('#shm-drop')){e.preventDefault();choose(e.dataTransfer.files);}};
 host.oninput=e=>{if(e.target.id==='shm-note'){const r=results[selected];if(r)notes[r.file_id]=e.target.value;}};
 draw();
}

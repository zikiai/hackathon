const results={};
const defaults={};
// Always open the complete official test batch, not a previous one-file upload.
const sources={};
const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let files=[], active='', busy=false, message='';
export const resultSource=component=>sources[component]==='uploaded'&&results[component]?'uploaded':'official';
export const hasUploadedResults=component=>Boolean(results[component]);
export const liveResult=component=>resultSource(component)==='uploaded'?results[component]:defaults[component];
export function setResultSource(component,source){
  if(source==='uploaded'&&!results[component])return;
  sources[component]=source==='uploaded'?'uploaded':'official';
  document.dispatchEvent(new CustomEvent('cloud-results',{detail:{component,result:liveResult(component),navigate:false}}));
}
export function renderCloudUpload(component){
  if(active!==component){active=component;files=[];message='';}
  const excel=component==='acv', suffix=excel?'.xlsx':'.csv';
  return `<section class="nx-detail" id="nx-cloud-upload"><div class="nx-upload-zone"><div class="nx-upload-icon" aria-hidden="true">↑</div><h3>Upload your ${excel?'Excel':'CSV'} records</h3><p class="nx-small">${component==='door'?'One continuous door recording.':'Select one or more records.'} Maximum 28 MiB per file.</p><label class="nx-upload-button"><span>Browse files</span><input id="nx-cloud-files" type="file" accept="${suffix}" ${component==='door'?'':'multiple'} ${busy?'disabled':''} aria-label="Choose prediction records"></label><p class="nx-upload-status">${files.length?files.map(f=>escape(f.name)).join(' · '):'No files selected'}</p></div><div class="nx-sectionhead"><p>Results open in Review findings.</p><button class="nx-action nx-primary" data-cloud-analyse ${busy||!files.length?'disabled':''}>${busy?'Analysing…':'Output predicted result'}</button></div><p class="nx-small" role="status">${escape(message||'Raw uploads are processed temporarily. Saved results are private to this browser for seven days.')}</p></section>`;
}
function paint(){const element=document.getElementById('nx-cloud-upload');if(element)element.outerHTML=renderCloudUpload(active);}
function combine(component,parts){
  const csv=parts.map((r,i)=>i?r.csv.trimEnd().split('\n').slice(1).join('\n'):r.csv.trimEnd()).filter(Boolean).join('\n')+'\n';
  return {component,csv,records:parts.flatMap(r=>r.records||[]),cases:parts.flatMap(r=>r.cases||[]),warnings:parts.flatMap(r=>r.warnings||[])};
}
function apply(component,parts,navigate){
  results[component]=combine(component,parts);
  if(navigate)sources[component]='uploaded';
  document.dispatchEvent(new CustomEvent('cloud-results',{detail:{component,result:liveResult(component),navigate}}));
}
document.addEventListener('change',event=>{
  if(event.target.id!=='nx-cloud-files'||busy)return;
  files=Array.from(event.target.files||[]);message='';paint();
});
document.addEventListener('click',async event=>{
  if(!event.target.closest('[data-cloud-analyse]')||busy||!files.length)return;
  const component=active, selected=[...files];
  if(selected.length>68||selected.some(f=>f.size>28*1024*1024||!f.size)||new Set(selected.map(f=>f.name.toLowerCase())).size!==selected.length){message='Choose up to 68 nonempty files, no duplicate names, each at most 28 MiB.';paint();return;}
  busy=true;const parts=[];
  try{
    for(let i=0;i<selected.length;i++){
      message=`Processing ${i+1} of ${selected.length}: ${selected[i].name}`;paint();
      const body=new FormData();body.append('file',selected[i]);
      const response=await fetch(`/api/analyse/${component}`,{method:'POST',body});
      const type=response.headers.get('content-type')||'';
      if(!type.includes('application/json'))throw new Error('Prediction service unavailable. Please try again shortly.');
      const result=await response.json();if(!response.ok)throw new Error(result.error||'Analysis failed');parts.push(result);
    }
    const stored=JSON.parse(localStorage.getItem('nx-result-ids')||'{}');stored[component]=parts.map(r=>r.analysis_id);localStorage.setItem('nx-result-ids',JSON.stringify(stored));
    message='Analysis complete.';apply(component,parts,true);
  }catch(error){message=`${error.message} This batch was not published; previous results are unchanged.`;}
  finally{busy=false;paint();}
});
export async function restoreResults(){
  try{const response=await fetch('./components/acv/test-result.json');if(response.ok){defaults.acv=combine('acv',[await response.json()]);document.dispatchEvent(new CustomEvent('cloud-results',{detail:{component:'acv',result:liveResult('acv'),navigate:false}}));}}catch{/* Upload remains available. */}
  let stored;try{stored=JSON.parse(localStorage.getItem('nx-result-ids')||'{}');}catch{return;}
  for(const [component,ids] of Object.entries(stored)){
    if(!['rail','door','acv','shm'].includes(component)||!Array.isArray(ids)||ids.length>68)continue;
    try{const parts=[];for(const id of ids){const response=await fetch(`/api/results/${encodeURIComponent(id)}`);if(!response.ok)throw new Error('Expired');parts.push(await response.json());}if(parts.length)apply(component,parts,false);}catch{/* Keep saved examples if the session expired. */}
  }
}

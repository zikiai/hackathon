import {renderAnalysis,mountAnalysis,renderMethod} from './shm_page.js';
const content=document.getElementById('nx-content');
content.innerHTML=`<section class="shm-hero"><div class="nx-kicker">Structural health / Recording review</div><h1>Every recording<br>tells a loading story.</h1><p>Explore the stress. Understand the estimate.<br>Bring useful observations to your engineering review.</p><a class="shm-hero-link" href="#shm-analysis">Review a recording <span aria-hidden="true">↗</span></a><div class="shm-hero-mark" aria-hidden="true"><span>SHM</span><small>STRUCTURAL HEALTH</small></div></section>
<section id="shm-guide" class="shm-guide"><div class="shm-section-title"><span class="shm-eyebrow">THE IDEA IN THREE STEPS</span><h2>From stress to understanding.</h2></div><div class="shm-steps"><article><span class="shm-step-number">01</span><h3>Stress changes</h3><p>Sensors record how forces are distributed within the structure as the train operates.</p></article><article><span class="shm-step-number">02</span><h3>Loading repeats</h3><p>Repeated stress changes can contribute to fatigue over time. Their size and frequency matter.</p></article><article><span class="shm-step-number">03</span><h3>Review the estimate</h3><p>The model summarises this recording’s estimated fatigue damage. It is one part of the asset’s history.</p></article></div></section>
<div class="nx-spaced" id="shm-analysis">${renderAnalysis()}</div>
<details id="shm-evidence" class="nx-detail nx-spaced"><summary><strong>How reliable is this estimate?</strong></summary><p>In development checks, average prediction error was about <strong>2%</strong>. Some recordings were underestimated by about <strong>6%</strong>. These describe past evaluation results; they do not give an error range for your recording.</p><details><summary>Technical evidence for engineers and judges</summary>${renderMethod()}</details></details>`;
mountAnalysis();
document.querySelectorAll('[data-jump]').forEach(b=>b.addEventListener('click',()=>{
 const target=document.getElementById(b.dataset.jump);
 if(target.tagName==='DETAILS')target.open=true;
 target.scrollIntoView({behavior:'smooth',block:'start'});
}));

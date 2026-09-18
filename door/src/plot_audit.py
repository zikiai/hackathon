"""Render audit results and the difficult movement against fold-training references."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from train_baseline import load_training

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    root=Path(__file__).resolve().parents[1]
    ap.add_argument('--raw-dir',type=Path,default=root/'data/raw')
    ap.add_argument('--output-dir',type=Path,default=root/'outputs/robustness')
    a=ap.parse_args(); result=pd.read_csv(a.output_dir/'comparison.csv')
    names=['current_only','current_position','baseline','baseline_no_emf','position_augmented','normal_reference']
    fig,axes=plt.subplots(1,2,figsize=(14,5))
    for offset,(scheme,color) in enumerate([('blocked','#2878b5'),('forward','#d95f02'),('similarity_purged','#399470')]):
        frame=result[result.scheme==scheme].set_index('feature_set').loc[names]
        for ax,col in zip(axes,['iou_weighted_f1','brier_score']):
            ax.bar(np.arange(6)+(offset-1)*.24,frame[col],width=.24,label=scheme,color=color)
    for ax in axes:
        ax.set_xticks(range(6),[n.replace('_','\n') for n in names],fontsize=8); ax.grid(axis='y',alpha=.2)
    axes[0].set_ylim(0,1.08); axes[0].set_title('IoU-weighted F1 (higher is better)')
    axes[1].set_title('Probability error: Brier score (lower is better)'); axes[1].legend(fontsize=8)
    fig.suptitle('Exploratory training-only audit — forward evaluation covers 66 movements; others 110')
    fig.tight_layout(); fig.savefig(a.output_dir/'audit_comparison.png',dpi=160); plt.close(fig)
    data,ans=load_training(a.raw_dir)
    # Original blocked fold 4: reference must exclude movements 67..88, including 81.
    valid=np.arange(66,88); normal=ans[(ans.status=='Normal')&(ans.operation=='Open')&~ans.index.isin(valid)]
    target=ans[ans.segment_id=='train_seg_081'].iloc[0]
    sample=data[data.time.between(target.start_time,target.end_time)]
    grid=np.linspace(35,665,100)
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ax,signal,title in zip(axes,['Motor current(mA)','power'],['Current (mA)','Electrical power proxy (W)']):
        def aligned(p):
            values=p['Motor current(mA)']*.001*p['Motor Voltage(10mV)']*.01 if signal=='power' else p[signal]
            # Average repeated position readings for this descriptive position plot.
            grouped=pd.DataFrame({'pos':p['Door leaf position'],'value':values}).groupby('pos').value.mean()
            return np.interp(grid,grouped.index,grouped.values)
        curves=np.stack([aligned(data[data.time.between(r.start_time,r.end_time)]) for r in normal.itertuples()])
        q=np.percentile(curves,[25,50,75],axis=0)
        ax.fill_between(grid,q[0],q[2],color='#2878b5',alpha=.2,label='Normal middle 50%')
        ax.plot(grid,q[1],color='#2878b5',label='Training-normal median')
        ax.plot(grid,aligned(sample),color='#d95f02',label='Abnormal movement 081')
        ax.set_xlabel('Door position (native units; end stops excluded)'); ax.set_ylabel(title); ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.suptitle('Difficult movement: position-aligned comparison\nNormal references use only original fold-4 training movements')
    fig.tight_layout(); fig.savefig(a.output_dir/'movement_081_position.png',dpi=160); plt.close(fig)

if __name__=='__main__': main()

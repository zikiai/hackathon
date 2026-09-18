"""Chronology, electrical-power proxy and back-EMF plots: training files only."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from plot_training import timestamp, COLORS

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir', type=Path, default=ROOT/'data/raw')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'outputs/training_plots')
    args = parser.parse_args()
    data = pd.read_csv(args.raw_dir/'Train.csv')
    labels = pd.read_csv(args.raw_dir/'Train_Segments_Answer.csv')
    data['time'] = data.Datetime.map(timestamp)
    for c in ['start_time', 'end_time']:
        labels[c] = labels[c].map(timestamp)
    labels = labels.sort_values('start_time').reset_index(drop=True)
    # Product of logged readings: a proxy, not calibrated mechanical power.
    data['power_W'] = data['Motor current(mA)'] * .001 * data['Motor Voltage(10mV)'] * .01
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'axes.spines.top':False, 'axes.spines.right':False})
    records, segments = [], []
    origin = data.time.min()
    for i, r in enumerate(labels.itertuples(index=False)):
        p = data.loc[data.time.between(r.start_time, r.end_time)].copy()
        if len(p) != r.n_rows or len(p) < 2:
            raise ValueError(f'Invalid labelled segment: {r.segment_id}')
        t = (p.time-r.start_time).dt.total_seconds().to_numpy()
        if np.any(np.diff(t)<=0):
            raise ValueError('Non-increasing segment timestamps')
        energy = np.sum((p.power_W.to_numpy()[1:] + p.power_W.to_numpy()[:-1]) * .5 * np.diff(t))
        records.append(dict(order=i+1, segment_id=r.segment_id, operation=r.operation,
            status=r.status, start_time=r.start_time.isoformat(),
            elapsed_min=(r.start_time-origin).total_seconds()/60,
            duration_s=t[-1], energy_proxy_J=energy,
            mean_power_proxy_W=energy/t[-1],
            mean_logged_back_emf=p['Motor electrodynamic force'].mean()))
        segments.append((r,p,t))
    table = pd.DataFrame(records)
    fig, axes = plt.subplots(4,1,figsize=(15,10),sharex=True)
    for status, color in COLORS.items():
        for operation, marker in [('Open','^'),('Close','o')]:
            s = table[(table.status==status)&(table.operation==operation)]
            axes[0].scatter(s.order, np.full(len(s), int(status!='Normal')), c=color,marker=marker,s=35)
            for ax, col in zip(axes[1:],['duration_s','energy_proxy_J','mean_logged_back_emf']):
                ax.scatter(s.order,s[col],c=color,marker=marker,s=30)
    axes[0].set_yticks([0,1],['Normal','Abnormal']); axes[0].set_ylim(-.4,1.5)
    axes[0].legend(handles=[Line2D([],[],color='gray',marker=m,linestyle='',label=o)
                           for o,m in [('Open','^'),('Close','o')]],loc='upper right')
    for ax, title in zip(axes[1:],['Duration (s)','Electrical energy proxy (J)','Mean logged back-EMF\n(unit unspecified)']):
        ax.set_ylabel(title)
    for ax in axes: ax.grid(alpha=.2)
    axes[-1].set_xlabel('Movement number in chronological order (equal spacing; time gaps not represented)')
    fig.suptitle('Training chronology — supplied labels; each point is one movement')
    fig.tight_layout(); fig.savefig(args.output_dir/'04_chronological_patterns.png',dpi=160); plt.close(fig)

    grid=np.linspace(0,100,201)
    for column, filename, title, unit in [
        ('power_W','05_power_curves.png','Electrical power proxy: logged voltage × logged current','Power proxy (W)'),
        ('Motor electrodynamic force','06_back_emf_curves.png','Motor electrodynamic force (back-EMF in the Info Kit)','Logged value (unit unspecified)')]:
        fig,axes=plt.subplots(2,2,figsize=(14,9),sharex='row',sharey=True)
        for j,op in enumerate(['Open','Close']):
            for status,color in COLORS.items():
                chosen=[(r,p,t) for r,p,t in segments if r.operation==op and r.status==status]
                curves=[]
                for r,p,t in chosen:
                    axes[0,j].plot(t,p[column],color=color,alpha=.16,lw=.8)
                    curves.append(np.interp(grid,t/t[-1]*100,p[column]))
                if curves:
                    q=np.percentile(curves,[25,50,75],axis=0)
                    axes[1,j].fill_between(grid,q[0],q[2],color=color,alpha=.2)
                    axes[1,j].plot(grid,q[1],color=color,lw=2,label=f'{status} (n={len(curves)})')
            axes[0,j].set_title(f'{op}: all movements, actual elapsed seconds')
            axes[0,j].set_xlabel('Seconds since movement start')
            axes[1,j].set_title(f'{op}: median and middle 50% after time alignment')
            axes[1,j].set_xlabel('Movement progress (% of duration; not position)')
            axes[1,j].legend(fontsize=9)
        for ax in axes.flat: ax.set_ylabel(unit); ax.grid(alpha=.2)
        fig.suptitle(title+'\nTraining labels only; shaded bands show variation, not confidence intervals')
        fig.tight_layout(); fig.savefig(args.output_dir/filename,dpi=160); plt.close(fig)
    abnormal=(table.status=='Abnormal resistance').to_numpy()
    runs=[]; length=0
    for flag in abnormal:
        if flag: length+=1
        elif length: runs.append(length); length=0
    if length: runs.append(length)
    summary={'abnormal_run_lengths':runs,'longest_abnormal_run':max(runs,default=0),
        'adjacent_abnormal_pairs':int(np.sum(abnormal[:-1]&abnormal[1:])),
        'expected_adjacent_pairs_under_random_label_order':float(abnormal.sum()*(abnormal.sum()-1)/len(abnormal)),
        'interpretation':'Descriptive only. Recording order may reflect dataset construction; no causal claim.'}
    table.to_csv(args.output_dir/'chronological_features.csv',index=False)
    (args.output_dir/'chronology_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    print(table.groupby(['operation','status'])[['duration_s','energy_proxy_J','mean_power_proxy_W','mean_logged_back_emf']].median().to_string())

if __name__=='__main__': main()

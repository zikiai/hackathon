"""Read-only independent checks of Door files and movement 33; no model fitting."""
from pathlib import Path
import argparse,hashlib,json
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def parse(s):
    v=list(map(int,s.split('-')))
    return datetime(v[0],v[1],v[2],v[3],v[4],v[5],v[6]*1000)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--training',type=Path,required=True);ap.add_argument('--answers',type=Path,required=True)
    ap.add_argument('--test',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    train=pd.read_csv(a.training);test=pd.read_csv(a.test);labels=pd.read_csv(a.answers)
    sensor=list(train.columns[1:])
    for d in [train,test]:
        d['t']=pd.to_datetime(d.Datetime.map(parse))
        assert d.t.is_monotonic_increasing and not d.t.duplicated().any()
        assert np.isfinite(d[sensor].to_numpy(float)).all()
    # Independently reconstruct gap groups; fixed threshold from existing model.
    def groups(d):return [p.copy() for _,p in d.groupby(d.t.diff().dt.total_seconds().gt(.2).cumsum())]
    tr=groups(train);te=groups(test)
    assert len(tr)==len(labels)
    assert all(p.Datetime.iloc[0]==r.start_time and p.Datetime.iloc[-1]==r.end_time and len(p)==r.n_rows for p,r in zip(tr,labels.itertuples()))
    target=te[32]; pos=target['Door leaf position']; t=(target.t-target.t.iloc[0]).dt.total_seconds().to_numpy()
    opening=[p for p in tr if p['Door leaf position'].iloc[-1]>p['Door leaf position'].iloc[0]]
    normal_open=[p for p,r in zip(tr,labels.itertuples()) if r.operation=='Open' and r.status=='Normal']
    def descriptor(p):
        q=p['Door leaf position'].to_numpy();tt=(p.t-p.t.iloc[0]).dt.total_seconds().to_numpy()
        return {'duration_s':float(tt[-1]),'position_start':int(q[0]),'position_end':int(q[-1]),
                'position_change':int(q[-1]-q[0]),'fraction_rows_in_fixed_position_bins':float(((q>=35)&(q<665)).mean()),
                'fraction_rows_above_705':float((q>705).mean())}
    # Compare raw full sensor sequences, not just resampled curves or timestamps.
    def sig(p):return hashlib.sha256(p[sensor].to_numpy(dtype='<f8').tobytes()).hexdigest()
    hashes={sig(p) for p in tr}; exact=[i+1 for i,p in enumerate(te) if sig(p) in hashes]
    target_stats=descriptor(target); opens=pd.DataFrame([descriptor(p) for p in opening])
    commands=target[['Open command','Close command','Door is opening','Door is closing']].drop_duplicates().to_dict('records')
    summary={'train_groups_match_all_answer_boundaries':True,'train_groups':len(tr),'test_groups':len(te),
      'all_test_rows_accounted_for':sum(map(len,te))==len(test),'all_numeric_values_finite':True,
      'exact_cross_set_sensor_sequence_matches':exact,
      'movement_33':dict(target_stats, rows=len(target),start=target.Datetime.iloc[0],end=target.Datetime.iloc[-1],
          commands=commands,position_monotonic=bool(pos.is_monotonic_increasing),
          ends_with_door_opened=int(target['Door Opened'].iloc[-1]),
          largest_internal_gap_s=float(target.t.diff().dt.total_seconds().max()),
          gap_before_s=float((target.t.iloc[0]-te[31].t.iloc[-1]).total_seconds()),
          gap_after_s=float((te[33].t.iloc[0]-target.t.iloc[-1]).total_seconds()),
          first_time_above_705_s=float(t[(pos>705).to_numpy()][0])),
      'training_opening_ranges':{c:[float(opens[c].min()),float(opens[c].max())] for c in opens},
      'hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.training,a.answers,a.test]}}
    (a.output/'independent_checks.json').write_text(json.dumps(summary,indent=2))
    # Show actual elapsed seconds so duration changes do not distort phase alignment.
    fig,axes=plt.subplots(3,1,figsize=(12,10),sharex=True)
    for p in normal_open:
        tp=(p.t-p.t.iloc[0]).dt.total_seconds()
        for ax,col in zip(axes,['Motor current(mA)','Motor Voltage(10mV)','Door leaf position']):
            ax.plot(tp,p[col],color='#2878b5',alpha=.16,lw=.8)
    for ax,col in zip(axes,['Motor current(mA)','Motor Voltage(10mV)','Door leaf position']):
        ax.plot(t,target[col],color='#d95f02',lw=2,label='Unlabelled movement 33')
        ax.plot([],[],color='#2878b5',label='40 labelled normal training openings')
        ax.set_ylabel(col);ax.grid(alpha=.2);ax.axvline(2.92,color='gray',ls=':',label='Longest training opening: 2.92 s')
    axes[0].legend(fontsize=8);axes[-1].axhspan(35,665,color='gray',alpha=.1)
    axes[-1].axhline(705,color='gray',ls='--');axes[-1].set_xlabel('Actual seconds from detected movement start')
    fig.suptitle('Movement 33: verified opening signals and extended travel\nOrange has no known fault label; grey position band is the fixed-bin feature coverage')
    fig.tight_layout();fig.savefig(a.output/'movement_33_raw_signals.png',dpi=150);plt.close(fig)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()

"""Reproducible training-only Door baseline. Never loads Test.csv."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import confusion_matrix, classification_report

LABELS = ['Normal', 'Abnormal resistance']
ROOT = Path(__file__).resolve().parents[1]

def timestamp(s):
    y,mo,d,h,mi,se,ms=map(int,s.split('-'))
    return pd.Timestamp(y,mo,d,h,mi,se)+pd.Timedelta(milliseconds=ms)

def load_training(raw):
    data=pd.read_csv(raw/'Train.csv')
    answers=pd.read_csv(raw/'Train_Segments_Answer.csv')
    data['time']=data.Datetime.map(timestamp)
    for c in ['start_time','end_time']: answers[c]=answers[c].map(timestamp)
    answers=answers.sort_values('start_time').reset_index(drop=True)
    if not data.time.is_monotonic_increasing or data.time.duplicated().any():
        raise ValueError('Timestamps must be unique and increasing')
    if not set(answers.status).issubset(LABELS): raise ValueError('Unknown labels')
    for r in answers.itertuples():
        p=data[data.time.between(r.start_time,r.end_time)]
        if len(p)!=r.n_rows: raise ValueError('Label row-count mismatch')
    return data,answers

def detect(stream,gap_s):
    groups=stream.time.diff().dt.total_seconds().gt(gap_s).cumsum()
    return [p.copy() for _,p in stream.groupby(groups,sort=False) if len(p)>=2]

def features(p):
    t=(p.time-p.time.iloc[0]).dt.total_seconds().to_numpy()
    current=p['Motor current(mA)'].to_numpy()*0.001
    voltage=p['Motor Voltage(10mV)'].to_numpy()*0.01
    power=current*voltage
    pos=p['Door leaf position'].to_numpy(dtype=float)
    # Five-sample median smoothing; speed retains native position units/s.
    smooth=pd.Series(pos).rolling(5,center=True,min_periods=1).median().to_numpy()
    speed=np.gradient(smooth,t)
    progress=t/t[-1]
    f={'duration_s':t[-1], 'position_change':pos[-1]-pos[0],
       'opening_from_position':float(pos[-1]>pos[0]),
       'mean_abs_current_A':np.abs(current).mean(),
       'peak_abs_current_A':np.abs(current).max(),
       'current_std_A':current.std(),
       'energy_proxy_J':float(np.sum((power[1:]+power[:-1])*.5*np.diff(t))),
       'speed_abs_median':float(np.median(np.abs(speed))),
       'speed_abs_p90':float(np.percentile(np.abs(speed),90))}
    for name,values in [('current_A',np.abs(current)),('power_W',power),
                        ('back_emf',p['Motor electrodynamic force'].to_numpy())]:
        for section,mask in [('early',progress<1/3),('middle',(progress>=1/3)&(progress<2/3)),('late',progress>=2/3)]:
            f[f'{section}_{name}']=float(values[mask].mean())
    return f

def score(truth,pred,ignore_labels=False):
    candidates=[]
    for i,a in enumerate(truth):
        for j,b in enumerate(pred):
            if not ignore_labels and a['status']!=b['prediction']: continue
            inter=max(0.,(min(a['end_time'],b['end_time'])-max(a['start_time'],b['start_time'])).total_seconds())
            union=(a['end_time']-a['start_time']).total_seconds()+(b['end_time']-b['start_time']).total_seconds()-inter
            if inter>0 and union>0: candidates.append((inter/union,i,j))
    used_t,used_p=set(),set(); credit=0.
    for iou,i,j in sorted(candidates,key=lambda x:(-x[0],x[1],x[2])):
        if i not in used_t and j not in used_p:
            used_t.add(i); used_p.add(j); credit+=iou
    return {'iou_weighted_f1':2*credit/(len(truth)+len(pred)) if truth or pred else 0.,
            'iou_credit':credit,'true_segments':len(truth),'predicted_segments':len(pred),
            'matched_segments':len(used_t),'unmatched_true':len(truth)-len(used_t),
            'unmatched_predictions':len(pred)-len(used_p)}

def self_check_score():
    t=pd.Timestamp('2023-01-01'); end=t+pd.Timedelta(seconds=10)
    a=[dict(start_time=t,end_time=end,status='Normal')]
    p=[dict(start_time=t,end_time=end,prediction='Normal')]
    assert score(a,p)['iou_weighted_f1']==1
    assert score(a,[dict(p[0],prediction='Abnormal resistance')])['iou_weighted_f1']==0
    assert score(a,p+p)['iou_weighted_f1']==2/3
    assert score(a,[dict(p[0],end_time=t+pd.Timedelta(seconds=5))])['iou_weighted_f1']==.5
    assert score(a,[])['iou_weighted_f1']==0

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw-dir',type=Path,default=ROOT/'data/raw')
    ap.add_argument('--output-dir',type=Path,default=ROOT/'outputs/baseline')
    ap.add_argument('--artifact-dir',type=Path,default=ROOT/'artifacts')
    args=ap.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True); args.artifact_dir.mkdir(parents=True,exist_ok=True)
    self_check_score()
    data,answers=load_training(args.raw_dir)
    parts=[data[data.time.between(r.start_time,r.end_time)] for r in answers.itertuples()]
    X=pd.DataFrame([features(p) for p in parts]); y=answers.status
    # Fixed architecture and five contiguous validation blocks; no tuning search.
    factories={'current_threshold':lambda:DecisionTreeClassifier(max_depth=1,class_weight='balanced',random_state=42),
               'random_forest':lambda:RandomForestClassifier(n_estimators=200,max_depth=4,min_samples_leaf=3,class_weight='balanced',random_state=42,n_jobs=1)}
    columns={'current_threshold':['mean_abs_current_A'],'random_forest':list(X.columns)}
    folds=[]; predictions={name:[] for name in factories}; classifications={name:[] for name in factories}; importances=[]
    for fold,valid in enumerate(np.array_split(np.arange(len(answers)),5),1):
        train=np.setdiff1d(np.arange(len(answers)),valid)
        # Threshold uses only within-movement sampling intervals from training folds.
        intervals=np.concatenate([parts[i].time.diff().dt.total_seconds().dropna().to_numpy() for i in train])
        gap=float(np.median(intervals)*10)
        start=answers.iloc[valid[0]].start_time; end=answers.iloc[valid[-1]].end_time
        # Mid-gap cuts keep complete movements but do not hand individual boundaries to detector.
        if valid[0]>0: start=answers.iloc[valid[0]-1].end_time+(start-answers.iloc[valid[0]-1].end_time)/2
        if valid[-1]<len(answers)-1: end=end+(answers.iloc[valid[-1]+1].start_time-end)/2
        stream=data[data.time.between(start,end)]
        detected=detect(stream,gap)
        Z=pd.DataFrame([features(p) for p in detected])
        truth=answers.iloc[valid].to_dict('records')
        for name,factory in factories.items():
            model=factory(); cols=columns[name]; model.fit(X.iloc[train][cols],y.iloc[train])
            output=model.predict(Z[cols])
            pred=[dict(start_time=p.time.iloc[0],end_time=p.time.iloc[-1],prediction=str(label),fold=fold)
                  for p,label in zip(detected,output)]
            predictions[name].extend(pred)
            metrics=score(truth,pred)
            folds.append(dict(fold=fold,model=name,gap_threshold_s=gap,**metrics,
                              boundary_only_f1=score(truth,pred,True)['iou_weighted_f1']))
            for idx,label in zip(valid,model.predict(X.iloc[valid][cols])):
                classifications[name].append(dict(segment_id=answers.iloc[idx].segment_id,truth=y.iloc[idx],prediction=str(label),fold=fold))
            if name=='random_forest': importances.append(model.feature_importances_)
    reports={}
    for name in factories:
        p=predictions[name]; c=pd.DataFrame(classifications[name])
        reports[name]={'end_to_end':score(answers.to_dict('records'),p),
                      'boundary_only':score(answers.to_dict('records'),p,True),
                      'classification_on_answer_boundaries':classification_report(c.truth,c.prediction,labels=LABELS,output_dict=True,zero_division=0),
                      'confusion_matrix_normal_abnormal':confusion_matrix(c.truth,c.prediction,labels=LABELS).tolist()}
        pd.DataFrame(p).to_csv(args.output_dir/f'{name}_validation_segments.csv',index=False)
        c.to_csv(args.output_dir/f'{name}_validation_classification.csv',index=False)
    pd.DataFrame(folds).to_csv(args.output_dir/'fold_scores.csv',index=False)
    pd.DataFrame({'feature':X.columns,'mean_fold_importance':np.mean(importances,axis=0)}).sort_values('mean_fold_importance',ascending=False).to_csv(args.output_dir/'feature_importance.csv',index=False)
    X.assign(segment_id=answers.segment_id,status=y).to_csv(args.output_dir/'training_features.csv',index=False)
    gap_rows=data.time.diff().dt.total_seconds(); is_start=data.Datetime.isin(pd.read_csv(args.raw_dir/'Train_Segments_Answer.csv').start_time)
    audit={'within_movement_gap_s':gap_rows[~is_start].describe().to_dict(),'between_movement_gap_s':gap_rows[is_start].describe().to_dict()}
    for col in ['Open command','Close command','Door is opening','Door is closing','DCSR','DCSL','DLSR','DLSL','Door opening time(.1s)','Door closing time(.1s)']:
        changed=data[col].diff().fillna(0).ne(0)
        audit[col]={'changes_at_boundaries':int((changed&is_start).sum()),'changes_inside_movements':int((changed&~is_start).sum()),'unique_values':int(data[col].nunique())}
    reports['boundary_audit']=audit
    reports['limitations']=['Exploratory blocked cross-validation: all training data was previously plotted.',
        'Offline blocks: training may include later movements than validation. Not a prospective forecast test.',
        'Gap detector assumes gaps between movements, as present in supplied training recording.',
        'No door IDs or physical cause labels; cannot establish unseen-door or cause-specific performance.',
        'Voltage-current product is an electrical proxy, not mechanical power.']
    (args.output_dir/'metrics.json').write_text(json.dumps(reports,indent=2))
    # Save the preselected RF baseline after evaluation, trained on all labelled training movements.
    model=factories['random_forest'](); model.fit(X,y)
    joblib.dump({'model':model,'feature_columns':list(X.columns),'gap_threshold_s':.2,
                 'feature_version':1,'labels':LABELS},args.artifact_dir/'door_baseline.joblib')
    for name in factories: print(name,json.dumps(reports[name]['end_to_end']), 'confusion',reports[name]['confusion_matrix_normal_abnormal'])
    print('Saved training-only reports and baseline model. No test file accessed.')

if __name__=='__main__': main()

"""Fixed-model comparison of explicitly supplied unlabelled data with training."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from train_baseline import load_training,timestamp,detect,features
from audit_robustness import position_features,waveform

def main():
    root=Path(__file__).resolve().parents[1]
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw-dir',type=Path,default=root/'data/raw')
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,default=root/'outputs/test_comparison')
    a=ap.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True)
    train,labels=load_training(a.raw_dir); test=pd.read_csv(a.input)
    expected=list(train.drop(columns='time').columns)
    if list(test.columns)!=expected: raise ValueError('Input schema differs from training')
    test['time']=test.Datetime.map(timestamp)
    if not test.time.is_monotonic_increasing or test.time.duplicated().any(): raise ValueError('Invalid timestamp order')
    if test.isna().any().any(): raise ValueError('Missing values require review before inference')
    parts=[train[train.time.between(r.start_time,r.end_time)] for r in labels.itertuples()]
    interval=float(np.median(np.concatenate([p.time.diff().dt.total_seconds().dropna().to_numpy() for p in parts])))
    gap=interval*10; segments=detect(test,gap)
    if sum(map(len,segments))!=len(test): raise ValueError('Detector discarded readings: inspect before inference')
    A=pd.DataFrame([features(p) for p in parts]); B=pd.DataFrame([features(p) for p in segments]); base=list(A)
    current=[c for c in base if 'current' in c]+['opening_from_position']
    A=pd.concat([A,pd.DataFrame([position_features(p) for p in parts])],axis=1)
    B=pd.concat([B,pd.DataFrame([position_features(p) for p in segments])],axis=1)
    y=(labels.status=='Abnormal resistance').to_numpy(int)
    for target in [A,B]:
        for c in ['reference_current_excess','reference_power_excess','reference_current_max_excess']: target[c]=0.
        for op in [0,1]:
            normal=A[(y==0)&(A.opening_from_position==op)]
            mask=target.opening_from_position==op
            for signal in ['current','power']:
                cols=[f'position_{k}_{signal}' for k in range(5)]
                excess=(target.loc[mask,cols]-normal[cols].median()).clip(lower=0)
                target.loc[mask,f'reference_{signal}_excess']=excess.mean(axis=1)
                if signal=='current': target.loc[mask,'reference_current_max_excess']=excess.max(axis=1)
    result=pd.DataFrame({'segment_id':[f'test_detected_{i+1:03d}' for i in range(len(segments))],
        'start_time':[p.Datetime.iloc[0] for p in segments],'end_time':[p.Datetime.iloc[-1] for p in segments],
        'operation_inferred':np.where(B.opening_from_position==1,'Open','Close')})
    for name,cols in [('baseline',base),('current_pattern',current),('normal_reference',list(A))]:
        med=A[cols].median().fillna(0)
        model=RandomForestClassifier(n_estimators=200,max_depth=4,min_samples_leaf=3,class_weight='balanced',random_state=42,n_jobs=1)
        model.fit(A[cols].fillna(med),y)
        prob=model.predict_proba(B[cols].fillna(med))[:,list(model.classes_).index(1)]
        result[name+'_score']=prob
        result[name+'_prediction']=np.where(prob>=.5,'Abnormal resistance','Normal')
    predcols=[c for c in result if c.endswith('_prediction')]
    result['model_disagreement']=result[predcols].nunique(axis=1)>1
    # Same fixed waveform metric as training audit, with same-direction neighbours only.
    W=np.stack([waveform(p) for p in parts]); V=np.stack([waveform(p) for p in segments]); scales=np.array([2500,10000,2500,700])
    D=np.sqrt(np.mean(((V[:,None]-W[None,:])/scales[None,None,:,None])**2,axis=(2,3)))
    D[B.opening_from_position.to_numpy()[:,None]!=A.opening_from_position.to_numpy()[None,:]]=np.inf
    T=np.sqrt(np.mean(((W[:,None]-W[None,:])/scales[None,None,:,None])**2,axis=(2,3)))
    T[A.opening_from_position.to_numpy()[:,None]!=A.opening_from_position.to_numpy()[None,:]]=np.inf; np.fill_diagonal(T,np.inf)
    near=D.argmin(axis=1); result['nearest_training_segment']=labels.segment_id.iloc[near].to_numpy(); result['waveform_distance']=D.min(axis=1)
    ranges=[]
    for op in [0,1]:
        aa=A[A.opening_from_position==op]; bb=B[B.opening_from_position==op]
        for col in base:
            ranges.append(dict(operation='Open' if op else 'Close',feature=col,train_min=aa[col].min(),train_median=aa[col].median(),train_max=aa[col].max(),test_min=bb[col].min(),test_median=bb[col].median(),test_max=bb[col].max(),outside_training_range=int(((bb[col]<aa[col].min())|(bb[col]>aa[col].max())).sum()),test_n=len(bb)))
    pd.DataFrame(ranges).to_csv(a.output_dir/'feature_ranges.csv',index=False)
    result.to_csv(a.output_dir/'candidate_predictions.csv',index=False)
    B.assign(segment_id=result.segment_id).to_csv(a.output_dir/'test_features.csv',index=False)
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    for row,op in enumerate([1,0]):
        for ax,col,title in zip(axes[row],['duration_s','mean_abs_current_A','energy_proxy_J'],['Duration (s)','Mean absolute current (A)','Energy proxy (J)']):
            vals=[A.loc[A.opening_from_position==op,col],B.loc[B.opening_from_position==op,col]]
            ax.boxplot(vals); ax.set_xticks([1,2],['Training','Unlabelled test']); ax.set_title(('Open: ' if op else 'Close: ')+title); ax.grid(axis='y',alpha=.2)
    fig.suptitle('Distribution comparison — test classes are unknown; different class mix can shift distributions')
    fig.tight_layout(); fig.savefig(a.output_dir/'train_test_distributions.png',dpi=160); plt.close(fig)
    tg=test.time.diff().dt.total_seconds()
    summary={'train_rows':len(train),'test_rows':len(test),'training_labelled_segments':len(parts),'test_detected_segments':len(segments),
        'schema_matches':True,'missing_cells':int(test.isna().sum().sum()),'gap_threshold_s':gap,
        'test_within_gap_range_s':[float(tg[tg<=gap].min()),float(tg[tg<=gap].max())],
        'test_between_gap_range_s':[float(tg[tg>gap].min()),float(tg[tg>gap].max())],
        'train_time_range':[str(train.time.min()),str(train.time.max())],'test_time_range':[str(test.time.min()),str(test.time.max())],
        'test_direction_counts':result.operation_inferred.value_counts().to_dict(),
        'candidate_counts':{c:result[c].value_counts().to_dict() for c in predcols},
        'disagreement_segments':result.loc[result.model_disagreement,'segment_id'].tolist(),
        'exact_cross_set_aligned_curve_matches':int((D==0).sum()),
        'train_nearest_distance_quantiles':pd.Series(T.min(axis=1)).quantile([0,.5,.95,1]).to_dict(),
        'test_nearest_distance_quantiles':result.waveform_distance.quantile([0,.5,.95,1]).to_dict(),
        'test_farther_than_train_max':int((result.waveform_distance>T.min(axis=1).max()).sum()),
        'input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),
        'limits':['No test labels: accuracy, recall, IoU or cause cannot be established.','Candidate settings and references fitted on training only. No test tuning.', 'No model selected from test agreement; no submission file generated.','Nearness and agreement do not establish correctness.']}
    (a.output_dir/'comparison.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2))
    print(result[result.model_disagreement].to_string(index=False))

if __name__=='__main__': main()

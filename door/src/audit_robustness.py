"""Training-only robustness audit; fixed experiments, no test access or tuning search."""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import recall_score, brier_score_loss
from train_baseline import load_training, features, detect, score

ROOT=Path(__file__).resolve().parents[1]

def position_features(p):
    t=(p.time-p.time.iloc[0]).dt.total_seconds().to_numpy()
    pos=p['Door leaf position'].to_numpy(float)
    smooth=pd.Series(pos).rolling(5,center=True,min_periods=1).median().to_numpy()
    speed=np.gradient(smooth,t)
    direction=1 if pos[-1]>pos[0] else -1
    current=np.abs(p['Motor current(mA)'].to_numpy(float))*.001
    power=p['Motor current(mA)'].to_numpy(float)*.001*p['Motor Voltage(10mV)'].to_numpy(float)*.01
    # Fixed absolute-position bins (native units), excluding end stops.
    out={}
    for k,(lo,hi) in enumerate([(35,175),(175,315),(315,455),(455,595),(595,665)]):
        mask=(pos>=lo)&(pos<hi)
        for name,signal in [('current',current),('power',power),('speed',speed*direction)]:
            out[f'position_{k}_{name}']=float(np.mean(signal[mask])) if mask.any() else np.nan
    stationary=np.abs(speed)<1.0
    out['stationary_fraction']=float(stationary.mean())
    out['stationary_current']=float(current[stationary].mean()) if stationary.any() else 0.
    out['reverse_fraction']=float((speed*direction < -1).mean())
    return out

def waveform(p):
    t=(p.time-p.time.iloc[0]).dt.total_seconds().to_numpy(); t=t/t[-1]
    return np.stack([np.interp(np.linspace(0,1,101),t,p[c].to_numpy(float))
        for c in ['Motor current(mA)','Motor Voltage(10mV)','Motor electrodynamic force','Door leaf position']])

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw-dir',type=Path,default=ROOT/'data/raw')
    ap.add_argument('--output-dir',type=Path,default=ROOT/'outputs/robustness')
    a=ap.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True)
    data,ans=load_training(a.raw_dir)
    parts=[data[data.time.between(r.start_time,r.end_time)] for r in ans.itertuples()]
    X=pd.DataFrame([features(p) for p in parts]); P=pd.DataFrame([position_features(p) for p in parts])
    full=pd.concat([X,P],axis=1); y=(ans.status=='Abnormal resistance').to_numpy(int)
    direction=X.opening_from_position.to_numpy()
    W=np.stack([waveform(p) for p in parts])
    # Fixed physical scales: 2500 mA, 10000 logged voltage, 2500 logged EMF, 700 position.
    # Diagnostic similarity definition, not a learned fault threshold.
    scales=np.array([2500,10000,2500,700])
    D=np.sqrt(np.mean(((W[:,None]-W[None,:])/scales[None,None,:,None])**2,axis=(2,3)))
    D[direction[:,None]!=direction[None,:]]=np.inf; np.fill_diagonal(D,np.inf)
    pairs=[]
    for i in range(len(ans)):
        j=int(np.argmin(D[i])); pairs.append(dict(segment_id=ans.iloc[i].segment_id,
            nearest_id=ans.iloc[j].segment_id,distance=float(D[i,j]),same_label=bool(y[i]==y[j])))
    pd.DataFrame(pairs).to_csv(a.output_dir/'nearest_waveforms.csv',index=False)
    # Fixed 0.01 normalized RMS threshold used only for a stress test of similarity leakage.
    near=D<.01
    group=np.arange(len(ans))
    for i in range(len(ans)):
        for j in np.where(near[i])[0]:
            old=group[j]; new=group[i]; group[group==old]=new
    pd.DataFrame({'segment_id':ans.segment_id,'similarity_group':group}).to_csv(a.output_dir/'similarity_groups.csv',index=False)
    sets={
        'current_only':[c for c in X if 'current' in c]+['opening_from_position'],
        'current_position':[c for c in X if 'current' in c or 'position' in c or 'speed' in c]+['duration_s'],
        'baseline':list(X.columns),
        'baseline_no_emf':[c for c in X if 'back_emf' not in c],
        'position_augmented':list(full.columns),
        'normal_reference':list(full.columns)+['reference_current_excess','reference_power_excess','reference_current_max_excess']}
    blocks=np.array_split(np.arange(len(ans)),5)
    schedules=[]
    for fold,valid in enumerate(blocks):
        train=np.setdiff1d(np.arange(len(ans)),valid)
        schedules.append(('blocked',fold+1,train,valid))
        # Remove the entire connected similarity groups represented in validation.
        purged=train[~np.isin(group[train],group[valid])]
        schedules.append(('similarity_purged',fold+1,purged,valid))
        if fold>=2: schedules.append(('forward',fold+1,np.concatenate(blocks[:fold]),valid))
    rows=[]; folds=[]; skipped=[]
    for scheme,fold,train,valid in schedules:
        if len(train)<10 or len(np.unique(y[train]))<2:
            skipped.append(dict(scheme=scheme,fold=fold,train_n=len(train),reason='Too few training movements or only one class')); continue
        gap=float(np.median(np.concatenate([parts[i].time.diff().dt.total_seconds().dropna().to_numpy() for i in train]))*10)
        start=ans.iloc[valid[0]].start_time; end=ans.iloc[valid[-1]].end_time
        if valid[0]>0: start=ans.iloc[valid[0]-1].end_time+(start-ans.iloc[valid[0]-1].end_time)/2
        if valid[-1]<len(ans)-1: end=end+(ans.iloc[valid[-1]+1].start_time-end)/2
        detected=detect(data[data.time.between(start,end)],gap)
        # The classifier diagnostics below are valid only if detector boundaries match exactly.
        if len(detected)!=len(valid) or any(p.time.iloc[0]!=ans.iloc[idx].start_time or p.time.iloc[-1]!=ans.iloc[idx].end_time for p,idx in zip(detected,valid)):
            raise ValueError('Boundary mismatch: must use explicit matching before classification diagnostics')
        A=full.iloc[train].copy(); B=pd.DataFrame([{**features(p),**position_features(p)} for p in detected])
        # Normal reference curves are fitted using training normals of each direction only.
        for target in [A,B]:
            for col in ['reference_current_excess','reference_power_excess','reference_current_max_excess']: target[col]=0.
            for op in [0,1]:
                normal=full.iloc[train][(y[train]==0)&(direction[train]==op)]
                if normal.empty: raise ValueError('No training normal reference for direction')
                mask=target.opening_from_position==op
                for signal in ['current','power']:
                    cols=[f'position_{k}_{signal}' for k in range(5)]
                    ref=normal[cols].median()
                    excess=(target.loc[mask,cols]-ref).clip(lower=0)
                    target.loc[mask,f'reference_{signal}_excess']=excess.mean(axis=1)
                    if signal=='current': target.loc[mask,'reference_current_max_excess']=excess.max(axis=1)
        for name,cols in sets.items():
            # Imputation also uses only training data, never validation statistics.
            med=A[cols].median().fillna(0)
            at=A[cols].fillna(med); bt=B[cols].fillna(med)
            model=RandomForestClassifier(n_estimators=200,max_depth=4,min_samples_leaf=3,class_weight='balanced',random_state=42,n_jobs=1)
            model.fit(at,y[train]); prob=model.predict_proba(bt)[:,list(model.classes_).index(1)]; guess=(prob>=.5).astype(int)
            preds=[dict(start_time=p.time.iloc[0],end_time=p.time.iloc[-1],prediction='Abnormal resistance' if g else 'Normal') for p,g in zip(detected,guess)]
            metric=score(ans.iloc[valid].to_dict('records'),preds)
            folds.append(dict(scheme=scheme,fold=fold,feature_set=name,train_n=len(train),valid_n=len(valid),**metric))
            # Distance measured against training only, using training feature IQR scaling.
            scale=(at.quantile(.75)-at.quantile(.25)).replace(0,1)
            distance=np.sqrt(np.mean(((bt.to_numpy()[:,None]-at.to_numpy()[None,:])/scale.to_numpy())**2,axis=2)).min(axis=1)
            for k,idx in enumerate(valid): rows.append(dict(scheme=scheme,fold=fold,feature_set=name,segment_id=ans.iloc[idx].segment_id,
                operation=ans.iloc[idx].operation,truth=int(y[idx]),prediction=int(guess[k]),probability=float(prob[k]),
                nearest_training_feature_distance=float(distance[k])))
    r=pd.DataFrame(rows); r.to_csv(a.output_dir/'validation_predictions.csv',index=False)
    pd.DataFrame(folds).to_csv(a.output_dir/'fold_scores.csv',index=False)
    summaries=[]
    for (scheme,name),g in r.groupby(['scheme','feature_set']):
        f=pd.DataFrame(folds); f=f[(f.scheme==scheme)&(f.feature_set==name)]
        summaries.append(dict(scheme=scheme,feature_set=name,n=len(g),
            iou_weighted_f1=2*f.iou_credit.sum()/(f.true_segments.sum()+f.predicted_segments.sum()),
            missed_abnormal=int(((g.truth==1)&(g.prediction==0)).sum()),false_alarms=int(((g.truth==0)&(g.prediction==1)).sum()),
            abnormal_recall=recall_score(g.truth,g.prediction,zero_division=0),
            false_alarm_rate=float(g.loc[g.truth==0,'prediction'].mean()),brier_score=brier_score_loss(g.truth,g.probability)))
    summary=pd.DataFrame(summaries); summary.to_csv(a.output_dir/'comparison.csv',index=False)
    errors=r[r.truth!=r.prediction]; errors.to_csv(a.output_dir/'errors.csv',index=False)
    consistency=r.groupby('segment_id').agg(evaluations=('truth','size'),errors=('prediction',lambda s:0))
    consistency['errors']=r.assign(error=r.truth!=r.prediction).groupby('segment_id').error.sum()
    votes=r[r.scheme=='blocked'].pivot(index='segment_id',columns='feature_set',values='prediction')
    consistency['blocked_model_disagreement']=votes.nunique(axis=1)>1
    consistency.to_csv(a.output_dir/'movement_consistency.csv')
    by_op=r.groupby(['scheme','feature_set','operation'])[['truth','prediction']].apply(lambda g:pd.Series({'n':len(g),'missed_abnormal':int(((g.truth==1)&(g.prediction==0)).sum()),'false_alarms':int(((g.truth==0)&(g.prediction==1)).sum())}))
    by_op.to_csv(a.output_dir/'by_operation.csv')
    audit={'exact_aligned_curve_pairs':int(np.sum(D==0)//2),'near_pairs_at_001':int(near.sum()//2),
        'similarity_group_sizes':sorted(pd.Series(group).value_counts().tolist(),reverse=True),
        'nearest_distance_quantiles':pd.Series(D.min(axis=1)).quantile([0,.25,.5,.75,1]).to_dict(),
        'skipped_folds':skipped,'notes':['Fixed exploratory experiments; no hyperparameter search.',
        'All training data previously explored. No untouched training holdout remains.',
        'Similarity threshold is a diagnostic convention, not verified shared provenance.',
        'Forward validation covers only final 66 movements; compare feature sets within each scheme.',
        'Probability and feature distance are diagnostic, not calibrated confidence or an abstention policy.',
        'Position bins use native absolute position 35..665; transfer to other position scales unvalidated.']}
    (a.output_dir/'audit.json').write_text(json.dumps(audit,indent=2))
    print(summary.to_string(index=False)); print(json.dumps(audit,indent=2)); print('Error counts:',errors.groupby('segment_id').size().to_dict())

if __name__=='__main__': main()

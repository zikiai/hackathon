"""Selected Door model: current patterns plus position-inferred direction."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import pandas as pd
import joblib
import sklearn
from sklearn.ensemble import RandomForestClassifier
from train_baseline import load_training, timestamp, detect, score

ROOT=Path(__file__).resolve().parents[1]
COLUMNS=['mean_abs_current_A','peak_abs_current_A','current_std_A','early_current_A','middle_current_A','late_current_A','opening_from_position']
DEFAULT_MODEL=ROOT/'artifacts/door_selected.joblib'
PARAMS=dict(n_estimators=200,max_depth=4,min_samples_leaf=3,class_weight='balanced',random_state=42,n_jobs=1)

def extract(p):
    t=(p.time-p.time.iloc[0]).dt.total_seconds().to_numpy()
    if len(t)<3 or t[-1]<=0: raise ValueError('Movement is too short to classify')
    current=p['Motor current(mA)'].to_numpy(float)*.001
    pos=p['Door leaf position'].to_numpy(float)
    progress=t/t[-1]
    values=[np.abs(current).mean(),np.abs(current).max(),current.std()]
    for mask in [progress<1/3,(progress>=1/3)&(progress<2/3),progress>=2/3]:
        if not mask.any(): raise ValueError('Movement lacks readings in one time section')
        values.append(np.abs(current[mask]).mean())
    values.append(float(pos[-1]>pos[0]))
    return dict(zip(COLUMNS,values))

def validate_frame(frame):
    needed=['Datetime','Motor current(mA)','Door leaf position']
    if not set(needed).issubset(frame): raise ValueError('Required columns: '+', '.join(needed))
    if frame.empty: raise ValueError('Input contains no readings')
    p=frame.copy()
    try:
        p['time']=p.Datetime.map(timestamp)
        for c in needed[1:]:p[c]=pd.to_numeric(p[c],errors='raise')
    except (ValueError,TypeError,AttributeError) as exc: raise ValueError('Invalid timestamps or numeric readings') from exc
    if not np.isfinite(p[needed[1:]].to_numpy(float)).all(): raise ValueError('Current and position must be finite')
    if not p.time.is_monotonic_increasing or p.time.duplicated().any(): raise ValueError('Timestamps must be strictly increasing')
    return p

def predict_frame(frame,bundle):
    """App-ready function returning exact official columns; no file writes."""
    if bundle.get('feature_version')!='current-pattern-v1' or bundle['feature_columns']!=COLUMNS:
        raise ValueError('Incompatible model feature contract')
    p=validate_frame(frame);parts=detect(p,bundle['gap_threshold_s'])
    if sum(map(len,parts))!=len(p): raise ValueError('One or more isolated readings cannot form a movement')
    X=pd.DataFrame([extract(q) for q in parts],columns=COLUMNS)
    probs=bundle['model'].predict_proba(X)[:,list(bundle['model'].classes_).index(1)]
    return pd.DataFrame({'start_time':[q.Datetime.iloc[0] for q in parts],
                         'end_time':[q.Datetime.iloc[-1] for q in parts],
                         'prediction':np.where(probs>=.5,'Abnormal resistance','Normal')})

def train(raw,output):
    data,answers=load_training(raw)
    parts=[data[data.time.between(r.start_time,r.end_time)] for r in answers.itertuples()]
    X=pd.DataFrame([extract(p) for p in parts],columns=COLUMNS)
    y=(answers.status=='Abnormal resistance').to_numpy(int)
    interval=np.median(np.concatenate([p.time.diff().dt.total_seconds().dropna().to_numpy() for p in parts]))
    bundle={'feature_version':'current-pattern-v1','feature_columns':COLUMNS,'gap_threshold_s':float(interval*10),
            'model':RandomForestClassifier(**PARAMS).fit(X,y),'parameters':PARAMS,
            'sklearn_version':sklearn.__version__,'training_rows':len(data),'training_movements':len(parts),
            'training_sha256':{name:hashlib.sha256((raw/name).read_bytes()).hexdigest() for name in ['Train.csv','Train_Segments_Answer.csv']},
            'selection_reason':'Tied best IoU-weighted F1 across three exploratory validation designs; fewest selected features. Not chosen using test predictions.'}
    # Confirm deployed feature extraction matches the previously audited candidate.
    from train_baseline import features
    np.testing.assert_allclose(X.to_numpy(),pd.DataFrame([features(p) for p in parts])[COLUMNS].to_numpy(),rtol=0,atol=0)
    output.parent.mkdir(parents=True,exist_ok=True);joblib.dump(bundle,output)
    loaded=joblib.load(output)
    pd.testing.assert_frame_equal(predict_frame(data,loaded),predict_frame(data,bundle))
    # Run the actual app-ready prediction function on held-out chronological blocks.
    folds=[]
    for fold,valid in enumerate(np.array_split(np.arange(len(parts)),5),1):
        fitting=np.setdiff1d(np.arange(len(parts)),valid)
        b=dict(bundle,model=RandomForestClassifier(**PARAMS).fit(X.iloc[fitting],y[fitting]))
        s=answers.iloc[valid[0]].start_time;e=answers.iloc[valid[-1]].end_time
        result=predict_frame(data[data.time.between(s,e)],b)
        pred=result.copy()
        for c in ['start_time','end_time']:pred[c]=pred[c].map(timestamp)
        folds.append({'fold':fold,**score(answers.iloc[valid].to_dict('records'),pred.to_dict('records'))})
    report={'model_file':str(output),'feature_columns':COLUMNS,'blocked_validation':folds,
            'deployment_feature_parity':'exact match with audited current_only features',
            'serialization_parity':'passed','limits':'Exploratory reused training folds; no test labels or new-door validation.'}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    tr=sub.add_parser('train');tr.add_argument('--raw-dir',type=Path,default=ROOT/'data/raw');tr.add_argument('--model',type=Path,default=DEFAULT_MODEL)
    pr=sub.add_parser('predict');pr.add_argument('--input',type=Path,required=True);pr.add_argument('--output',type=Path,required=True);pr.add_argument('--model',type=Path,default=DEFAULT_MODEL)
    a=ap.parse_args()
    if a.command=='train':train(a.raw_dir,a.model)
    else:
        output=predict_frame(pd.read_csv(a.input),joblib.load(a.model))
        a.output.parent.mkdir(parents=True,exist_ok=True);output.to_csv(a.output,index=False)
        print(f'Saved {len(output)} predicted segments to {a.output}')

if __name__=='__main__':main()

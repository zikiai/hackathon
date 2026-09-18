from pathlib import Path
import sys, json, hashlib
import pandas as pd
import joblib

import argparse
parser=argparse.ArgumentParser(description='Recompute Door reference findings using the selected pipeline.')
parser.add_argument('--repo',type=Path,required=True)
repo=parser.parse_args().repo.resolve()
sys.path.insert(0,str(repo/'door/src'))
from selected_model import validate_frame, predict_frame, extract, COLUMNS
from train_baseline import detect, load_training

bundle=joblib.load(repo/'door/artifacts/door_selected.joblib')
raw=repo/'door/data/raw'
train,answers=load_training(raw)
reference=[]
for a in answers.itertuples():
    p=train[train.time.between(a.start_time,a.end_time)]
    reference.append(dict(extract(p), label=a.status))
reference=pd.DataFrame(reference)
frame=pd.read_csv(raw/'Test.csv')
pred=predict_frame(frame,bundle)
p=validate_frame(frame)
records=[]
for i,(part,result) in enumerate(zip(detect(p,bundle['gap_threshold_s']),pred.to_dict('records'),strict=True),1):
    stats=extract(part)
    normal=reference[(reference.label=='Normal')&(reference.opening_from_position==stats['opening_from_position'])]
    ranges={c:[float(normal[c].min()),float(normal[c].max())] for c in COLUMNS[:-1]}
    abnormal=float(bundle['model'].predict_proba(pd.DataFrame([stats],columns=COLUMNS))[0,list(bundle['model'].classes_).index(1)])
    records.append(dict(id=f'test_detected_{i:03d}',file=f'Test.csv · movement {i:02d}',prediction=result['prediction'],start=result['start_time'],end=result['end_time'],duration=float((part.time.iloc[-1]-part.time.iloc[0]).total_seconds()),positionChange=float(part['Door leaf position'].iloc[-1]-part['Door leaf position'].iloc[0]),rows=len(part),stats=stats,ranges=ranges,abnormalScore=abnormal))
evidence=dict(records=records,source_sha256={n:hashlib.sha256((raw/n).read_bytes()).hexdigest() for n in ['Train.csv','Test.csv','Train_Segments_Answer.csv']},model_sha256=hashlib.sha256((repo/'door/artifacts/door_selected.joblib').read_bytes()).hexdigest(),training_rows=len(train),test_rows=len(frame))
(repo/'integrated_app/components/door/evidence.js').write_text('export const evidence = '+json.dumps(evidence,indent=2,allow_nan=False)+';\n')
pred.to_csv(repo/'door/outputs/door_predictions.csv',index=False)
print(json.dumps(dict(train_rows=len(train),test_rows=len(frame),movements=len(pred),counts=pred.prediction.value_counts().to_dict())))

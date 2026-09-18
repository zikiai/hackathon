"""Inference adapters. Uses saved models only; never fits on uploaded files."""
from functools import lru_cache
from pathlib import Path
import base64
import hashlib
import json
import sys
import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'rail_corrugation/src'), str(ROOT/'door/src'), str(ROOT/'shm'), str(ROOT/'shm/ui')]

@lru_cache(maxsize=3)
def model(component):
    paths = {'rail':'rail_corrugation/artifacts/rail_model.joblib', 'door':'door/artifacts/door_selected.joblib'}
    return joblib.load(ROOT/paths[component])

@lru_cache(maxsize=1)
def shm_engine():
    from serve import Engine
    return Engine(ROOT/'shm/shm_shape_model.joblib')

def csv_text(rows, columns):
    return pd.DataFrame(rows, columns=columns).to_csv(index=False)

def analyse_file(component, path, filename):
    if component == 'acv':
        from server import analyse
        result = analyse({'files':[{'name':filename,'content':base64.b64encode(path.read_bytes()).decode()}]})
        # Keep Firestore and browser payloads small. Ranking uses every eligible row.
        for case in result['cases']:
            total = len(case['times'])
            indices = sorted(set(range(0,total,max(1,(total+399)//400))) | {total-1})
            case['total_readings'] = total
            case['chart_sampled'] = len(indices) < total
            case['times'] = [case['times'][i] for i in indices]
            for series in case['charts'].values():
                for key in series: series[key] = [series[key][i] for i in indices]
        return result
    if component == 'rail':
        from rail_cdm.io import read_sensor_csv
        from rail_cdm.features import extract_features
        bundle = model('rail'); frame = read_sensor_csv(path); features = extract_features(frame)
        x = pd.DataFrame([features]).reindex(columns=bundle['feature_columns'])
        label = str(bundle['model'].predict(x)[0])
        record = dict(id=filename,file=filename,prediction=label,rows=len(frame),channels=128,
            stats={k:float(features[k]) for k in ['side1_vibration_rms_mean','side2_vibration_rms_mean','side1_shock_rms_mean','side2_shock_rms_mean','side1_vibration_peak_mean','side2_vibration_peak_mean']},
            scores={str(k):float(v) for k,v in zip(bundle['model'].classes_,bundle['model'].predict_proba(x)[0])})
        if hasattr(bundle['model'], 'side_scores'):
            record['sideScores'] = dict(zip(['Side I','Side II'], map(float, bundle['model'].side_scores(x)[0])))
            record['faultThreshold'] = float(bundle['model'].threshold)
            record['modelVersion'] = 'shared-side-20-t040'
        return dict(records=[record],csv=csv_text([[filename,label]],['file_id','prediction']))
    if component == 'door':
        from selected_model import validate_frame,predict_frame,extract,COLUMNS
        from train_baseline import detect
        bundle=model('door'); frame=pd.read_csv(path); output=predict_frame(frame,bundle); validated=validate_frame(frame)
        source=(ROOT/'integrated_app/components/door/evidence.js').read_text()
        reference=json.loads(source.removeprefix('export const evidence = ').rstrip().removesuffix(';'))['records']
        records=[]
        for i,(part,row) in enumerate(zip(detect(validated,bundle['gap_threshold_s']),output.to_dict('records'),strict=True)):
            stats=extract(part)
            ranges=next(r['ranges'] for r in reference if r['stats']['opening_from_position']==stats['opening_from_position'])
            probability=float(bundle['model'].predict_proba(pd.DataFrame([stats],columns=COLUMNS))[0,list(bundle['model'].classes_).index(1)])
            records.append(dict(id=f'{filename}:{i}',file=f'{filename} · movement {i+1}',prediction=row['prediction'],start=row['start_time'],end=row['end_time'],duration=float((part.time.iloc[-1]-part.time.iloc[0]).total_seconds()),positionChange=float(part['Door leaf position'].iloc[-1]-part['Door leaf position'].iloc[0]),rows=len(part),stats=stats,ranges=ranges,abnormalScore=probability))
        return dict(records=records,csv=output.to_csv(index=False))
    if component == 'shm':
        result=shm_engine().analyse(path.read_bytes())
        return dict(records=[dict(id=filename,file=filename,**result)],csv=csv_text([[filename,result['prediction']]],['file_id','prediction']))
    raise ValueError('Unknown component')

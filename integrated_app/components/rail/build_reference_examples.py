"""Generate UI reference examples from the existing Rail model and local recordings.
No raw samples are copied. Test predictions have no known truth labels.
Run with the Rail virtualenv; pass --repo and --output explicitly.
"""
import argparse, hashlib, json
from pathlib import Path
import joblib
import pandas as pd
from rail_cdm.io import read_sensor_csv
from rail_cdm.features import extract_features

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rail=a.repo/'rail_corrugation'; model_path=rail/'artifacts/rail_model.joblib'
    bundle=joblib.load(model_path); model=bundle['model']
    saved=pd.read_csv(rail/'outputs/rail_predictions.csv'); records=[]
    if saved.file_id.duplicated().any():
        raise ValueError('Duplicate prediction file IDs')
    for filename, label in saved[['file_id','prediction']].itertuples(index=False, name=None):
        source=rail/'data/raw/rail/Test'/filename
        frame=read_sensor_csv(source); features=extract_features(frame)
        x=pd.DataFrame([features]).reindex(columns=bundle['feature_columns'])
        prediction=str(model.predict(x)[0])
        if prediction != label:
            raise ValueError(f'{filename}: model prediction differs from saved output')
        print(f'Processing {filename}', flush=True)
        records.append(dict(id=filename,file=filename,prediction=prediction,rows=len(frame),channels=128,
            stats={k:float(features[k]) for k in ['side1_vibration_rms_mean','side2_vibration_rms_mean','side1_shock_rms_mean','side2_shock_rms_mean','side1_vibration_peak_mean','side2_vibration_peak_mean']},
            scores={str(k):float(v) for k,v in zip(model.classes_,model.predict_proba(x)[0])},
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
        if hasattr(model, 'side_scores'):
            records[-1].update(sideScores=dict(zip(['Side I','Side II'], map(float,model.side_scores(x)[0]))),faultThreshold=float(model.threshold),modelVersion=bundle.get('model_version','shared-side'))
    result={'source':'Computed from local unlabelled Rail Test recordings using the saved pipeline; complete test-file results.','model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),'records':records}
    a.output.write_text('export const evidence = '+json.dumps(result,indent=2)+';\n')
    print([(r['file'],r['prediction']) for r in records])
if __name__=='__main__':main()

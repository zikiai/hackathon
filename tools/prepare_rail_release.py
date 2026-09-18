"""Fit the selected configuration and verify official outputs against its submission hash."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'rail_corrugation/src'), str(ROOT/'integrated_app')]
from rail_cdm.train import make_production_model
EXPECTED_RAIL_SHA256 = '9bf05ffa10472777ecf885c34527144fabf32e0e15b8b64fbf24ca35cf68a147'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    source = args.source/'rail_corrugation'
    features = pd.read_csv(source/'data/processed/rail_features.csv')
    data = pd.read_csv(source/'data/raw/rail/Train_Labels.csv').merge(features, on='filename', validate='one_to_one')
    assert len(data) == 272
    columns = [c for c in features if c != 'filename']
    model = make_production_model().fit(data[columns], data.label)
    artifact = ROOT/'rail_corrugation/artifacts/rail_model.joblib'
    artifact.parent.mkdir(exist_ok=True)
    joblib.dump(dict(model=model, feature_columns=columns, feature_version=1,
                     allowed_labels=['Normal','Side I','Side II'],
                     model_version='shared-side-20-t040', status='promoted',
                     submission_csv_sha256=EXPECTED_RAIL_SHA256), artifact)
    from pipelines import analyse_file
    records = []
    rows = []
    from io import StringIO
    for i in range(1, 69):
        filename = f'Test{i}.csv'
        path = source/'data/raw/rail/Test'/filename
        result = analyse_file('rail', path, filename)
        record = result['records'][0]
        record['source_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append(record)
        rows.extend(pd.read_csv(StringIO(result['csv'])).to_dict('records'))
        print(f'Verified {i}/68', flush=True)
    payload = pd.DataFrame(rows, columns=['file_id','prediction']).to_csv(index=False).encode()
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_RAIL_SHA256, 'Output differs from selected submission'
    (ROOT/'integrated_app/downloads/rail_predictions.csv').write_bytes(payload)
    output = ROOT/'rail_corrugation/outputs'; output.mkdir(exist_ok=True)
    (output/'rail_predictions.csv').write_bytes(payload)
    evidence = dict(source='Computed from all 68 unlabelled test files using shared-side-20-t040.',
                    model_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(), records=records)
    (ROOT/'integrated_app/components/rail/evidence.js').write_text('export const evidence = '+json.dumps(evidence,indent=2,allow_nan=False)+';\n')
    print('PASS: all 68 predictions exactly match selected submission', flush=True)

if __name__ == '__main__':
    main()

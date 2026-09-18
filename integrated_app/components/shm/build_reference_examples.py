"""Generate SHM dashboard evidence and CSV from local official test files.

Run with numpy, pandas, scikit-learn, joblib and rainflow installed.
Uses the merged SHM inference engine without fitting or reading labels.
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--input',type=Path,required=True,help='Directory containing test01.csv through test16.csv')
    args=parser.parse_args()
    sys.path[:0]=[str(args.repo/'shm'),str(args.repo/'shm/ui')]
    from serve import Engine
    engine=Engine(args.repo/'shm/shm_shape_model.joblib')
    records=[]
    for i in range(1,17):
        path=args.input/f'test{i:02d}.csv'
        data=path.read_bytes()
        records.append(dict(id=path.name,file=path.name,**engine.analyse(data),source_sha256=hashlib.sha256(data).hexdigest()))
    app=args.repo/'integrated_app'
    evidence={'records':records}
    (app/'components/shm/evidence.js').write_text('export const evidence = '+json.dumps(evidence,allow_nan=False)+';\n')
    with (app/'downloads/shm_predictions.csv').open('w',newline='') as handle:
        writer=csv.writer(handle)
        writer.writerow(['file_id','prediction'])
        writer.writerows((r['file'],r['prediction']) for r in records)
    print('Generated 16 SHM findings and predictions.')

if __name__=='__main__':main()

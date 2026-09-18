"""Run local official-file parity checks before deployment. No retraining."""
from pathlib import Path
import argparse,json
import pandas as pd
from pipelines import analyse_file

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);args=parser.parse_args()
    cases={'rail':args.source/'rail_corrugation/data/raw/rail/Test/Test1.csv',
      'door':args.source/'door/data/raw/Test.csv','acv':args.source/'acv/data/raw/test/acv_test_case.xlsx',
      'shm':Path('/private/tmp/nebulax-shm-test01.csv')}
    for component,path in cases.items():
        name='test01.csv' if component=='shm' else path.name
        result=analyse_file(component,path,name)
        if component in {'rail','door','shm'}:
            expected=pd.read_csv(args.source/f'integrated_app/downloads/{component}_predictions.csv')
            from io import StringIO
            actual=pd.read_csv(StringIO(result['csv']))
            if component!='door':expected=expected[expected.file_id==name].reset_index(drop=True)
            pd.testing.assert_frame_equal(actual,expected,check_exact=False,rtol=1e-10)
        else:
            from server import create_predictions
            assert result['csv']==create_predictions(path).to_csv(index=False)
            (Path(__file__).parent/'components/acv/test-result.json').write_text(json.dumps(dict(component='acv',**result),allow_nan=False))
            (Path(__file__).parent/'downloads/acv_predictions.csv').write_text(result['csv'])
        print(component,'PASS',len(json.dumps(result)),flush=True)

if __name__=='__main__':main()

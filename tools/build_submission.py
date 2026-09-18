"""Run every official test input through the deployed app, validate and package CSVs.

Uses the same saved-model inference adapter as the upload form. No training,
label access or model selection occurs. Raw files remain in private Cloud Storage.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import re
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPCookieProcessor

EXPECTED={
    'rail': [f'Test{i}.csv' for i in range(1,69)],
    'door':['Test.csv'],
    'acv':['acv_test_case.xlsx'],
    'shm':[f'test{i:02d}.csv' for i in range(1,17)],
}
HEADERS={'rail':['file_id','prediction'],'door':['start_time','end_time','prediction'],
         'acv':['file_id','ranked_cars'],'shm':['file_id','prediction']}
SOURCE='966c976005db2e3e40a691cff268fdb8f396a5df'

def timestamp(value):
    pieces=value.split('-')
    if len(pieces)==7 and all(p.isdigit() for p in pieces):
        y,m,d,h,mi,s,ms=map(int,pieces)
        if not 0<=ms<=999:raise ValueError('Invalid milliseconds')
        return datetime(y,m,d,h,mi,s,ms*1000)
    return datetime.fromisoformat(value)

def validate(component,text):
    reader=csv.DictReader(io.StringIO(text))
    assert reader.fieldnames==HEADERS[component],(component,reader.fieldnames)
    rows=list(reader)
    assert rows and all(None not in row and all(v is not None for v in row.values()) for row in rows)
    if component!='door':
        ids=[row['file_id'] for row in rows]
        assert len(ids)==len(set(ids)) and set(ids)==set(EXPECTED[component]),component
    if component=='rail':assert all(r['prediction'] in {'Normal','Side I','Side II'} for r in rows)
    if component=='shm':assert all(math.isfinite(float(r['prediction'])) and float(r['prediction'])>=0 for r in rows)
    if component=='acv':
        for row in rows:
            cars=row['ranked_cars'].split('|')
            assert len(cars)==8 and set(cars)=={f'{i:02d}' for i in range(1,9)}
    if component=='door':
        previous=None
        for row in rows:
            assert row['prediction'] in {'Normal','Abnormal resistance'}
            start,end=timestamp(row['start_time']),timestamp(row['end_time'])
            assert start<end and (previous is None or start>=previous)
            previous=end
    return rows

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='https://nebulax-workspace-1029817906638.asia-southeast1.run.app')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True,help='Dedicated run directory, not shared between model versions')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True);args.cache.mkdir(parents=True,exist_ok=True)
    client=build_opener(HTTPCookieProcessor(CookieJar()))
    def request(path,payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        for attempt in range(6):
            try:
                with client.open(Request(args.url+path,data=data,headers={'Content-Type':'application/json'}),timeout=900) as response:return json.load(response)
            except HTTPError as error:
                if error.code not in {429,502,503,504} or attempt==5:raise
                time.sleep(min(2**attempt,30))
    assert request('/api/health')['status']=='ok'
    manifest={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'app_url':args.url,'dataset_commit':SOURCE,'method':'POST /api/test-files/<component>; same analyse_file adapter as multipart uploads','inputs':[],'outputs':{}}
    outputs={}
    for component,names in EXPECTED.items():
        assert set(request('/api/test-files/'+component)['files'])==set(names),f'{component}: official inventory changed'
        rows=[]
        for index,name in enumerate(names,1):
            cache=args.cache/f'{component}-{name}.json'
            if cache.exists():result=json.loads(cache.read_text())
            else:
                result=request('/api/test-files/'+component,{'filename':name})
                # Do not persist visitor cookies or private analysis IDs in the package.
                result.pop('analysis_id',None);cache.write_text(json.dumps(result,allow_nan=False))
            assert result['component']==component and re.fullmatch('[a-f0-9]{64}',result['source_sha256'])
            reader=csv.DictReader(io.StringIO(result['csv']));assert reader.fieldnames==HEADERS[component]
            part=list(reader)
            if component!='door':assert len(part)==1 and part[0]['file_id']==name
            rows.extend(part)
            manifest['inputs'].append({'component':component,'filename':name,'sha256':result['source_sha256']})
            print(f'{component} {index}/{len(names)} {name}: OK',flush=True)
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=HEADERS[component],lineterminator='\n');writer.writeheader();writer.writerows(rows)
        text=stream.getvalue();validate(component,text)
        filename=f'{component}_predictions.csv';outputs[filename]=text.encode()
        entry={'rows':len(rows),'columns':HEADERS[component],'sha256':hashlib.sha256(text.encode()).hexdigest()}
        if component in {'rail','door'}:entry['label_counts']=dict(Counter(row['prediction'] for row in rows))
        manifest['outputs'][filename]=entry
    archive=args.output/'predictions.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
        for name,data in outputs.items():zipped.writestr(name,data)
    with zipfile.ZipFile(archive) as zipped:
        assert sorted(zipped.namelist())==sorted(outputs)
        assert zipped.testzip() is None
        for name in zipped.namelist():validate(name.removesuffix('_predictions.csv'),zipped.read(name).decode())
    manifest['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
    optional=args.output/'Optional_Items';optional.mkdir(exist_ok=True)
    (optional/'prediction_validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('VERIFIED',archive,manifest['outputs'],flush=True)

if __name__=='__main__':main()

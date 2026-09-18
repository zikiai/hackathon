"""Standalone SHM interface server. Run from hackathon:
python shm/ui/serve.py
Uses only the SHM model; does not modify or serve the shared app.
"""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlsplit
from collections import OrderedDict
import argparse
import base64
import hashlib
import json
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parent
MAX_FILE = 32 * 1024 * 1024
MAX_BODY = 45 * 1024 * 1024


class Engine:
    def __init__(self, model_path):
        self.model_path = model_path
        self.lock = threading.Lock()
        self.bundle = None
        self.cache = OrderedDict()

    def analyse(self, data):
        # Serialize heavy work; maintain a small in-memory cache of summaries.
        with self.lock:
            import numpy as np
            import pandas as pd
            import rainflow
            from build_features_v2 import extract_features_v2, load_stress
            from predict_shm import load_model
            from train_shm_shape import predict_bundle
            if self.bundle is None:
                self.bundle = load_model(self.model_path)
                self.model_id = hashlib.sha256(self.model_path.read_bytes()).hexdigest()[:12]
            digest = hashlib.sha256(data).hexdigest()
            if digest in self.cache:
                self.cache.move_to_end(digest)
                return self.cache[digest]
            with tempfile.TemporaryDirectory() as temporary:
                p = Path(temporary)/'recording.csv'
                p.write_bytes(data)
                stress = load_stress(p)
            cycles = rainflow.count_cycles(stress)
            # Reuse whichever version of the existing extractor is installed.
            import inspect
            if 'cycles' in inspect.signature(extract_features_v2).parameters:
                features = extract_features_v2(stress, cycles=cycles)
            else:
                features = extract_features_v2(stress)
            prediction = float(predict_bundle(self.bundle,pd.DataFrame([features]))[0])
            if not np.isfinite(prediction) or prediction <= 0:
                raise ValueError('Invalid damage prediction.')
            edges = np.linspace(0,len(stress),min(500,len(stress))+1,dtype=int)
            overview = [dict(sample=int(a),minimum=float(stress[a:b].min()),maximum=float(stress[a:b].max()))
                        for a,b in zip(edges[:-1],edges[1:])]
            ranges = np.array([r for r,n in cycles],dtype=float)
            counts = np.array([n for r,n in cycles],dtype=float)
            hist,bins = np.histogram(ranges,bins=np.linspace(0,float(ranges.max()),13),weights=counts)
            warning = [] if len(stress)==581120 else ['Recording length differs from the 581,120-reading training examples; accuracy for this length has not been established.']
            result = dict(prediction=prediction,readings=len(stress),features=features,
                          overview=overview,cycles=[dict(low=float(a),high=float(b),count=float(n))
                          for a,b,n in zip(bins[:-1],bins[1:],hist)],warnings=warning,
                          model_version='shm-shape-alpha1-'+self.model_id)
            self.cache[digest] = result
            if len(self.cache)>32:
                self.cache.popitem(last=False)
            return result


def make_handler(engine, port):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,directory=str(ROOT),**kwargs)

        def reply(self,status,obj):
            data=json.dumps(obj,allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if urlsplit(self.path).path == '/api/shm/health':
                self.reply(200,dict(service='SHM local inference',model_present=engine.model_path.is_file()))
            else:
                super().do_GET()

        def do_POST(self):
            if urlsplit(self.path).path != '/api/shm/analyse':
                self.reply(404,dict(error='Unknown endpoint.'));return
            origin=self.headers.get('Origin')
            if origin and origin not in {f'http://127.0.0.1:{port}',f'http://localhost:{port}'}:
                self.reply(403,dict(error='Open the interface from this local server.'));return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0 < length <= MAX_BODY:
                    self.reply(413,dict(error='Request too large. Maximum raw CSV size is 32 MiB.'));return
                if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                    self.reply(415,dict(error='Expected a JSON upload.'));return
                body=json.loads(self.rfile.read(length))
                name=body['filename']
                if not isinstance(name,str) or not name.lower().endswith('.csv') or '/' in name or '\\' in name or any(ord(c)<32 for c in name):
                    raise ValueError('Use a plain CSV filename without path separators or control characters.')
                data=base64.b64decode(body['data'],validate=True)
                if not 0<len(data)<=MAX_FILE:
                    raise ValueError('CSV must be nonempty and no larger than 32 MiB.')
                result=engine.analyse(data)
                self.reply(200,dict(file_id=name,**result))
            except (ValueError,TypeError,KeyError) as exc:
                self.reply(400,dict(error=str(exc)))
            except Exception as exc:
                print(f'SHM analysis failed: {exc}',file=sys.stderr)
                self.reply(500,dict(error='SHM could not analyse this recording. '+str(exc)))
    return Handler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8503)
    parser.add_argument('--shm-dir',type=Path,default=ROOT.parent)
    parser.add_argument('--model',type=Path)
    args=parser.parse_args()
    sys.path.insert(0,str(args.shm_dir.resolve()))
    model=args.model or args.shm_dir/'shm_shape_model.joblib'
    required=['build_features.py','build_features_v2.py','predict_shm.py','train_shm_shape.py']
    missing=[f for f in required if not (args.shm_dir/f).is_file()]
    if missing or not model.is_file():
        parser.error(f'Missing SHM setup: {missing}; model exists: {model.is_file()}')
    engine=Engine(model)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(engine,args.port))
    print(f'Open http://127.0.0.1:{args.port}/ — standalone SHM page.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()

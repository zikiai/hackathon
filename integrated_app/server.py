"""Local integrated UI plus ACV upload adapter. No model tuning or labels."""
import argparse
import base64
import binascii
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import threading
import warnings

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'acv' / 'src'))
from baseline import RICH, STANDARD, create_predictions, rank_file

MAX_BODY = 140 * 1024 * 1024  # Base64 overhead for up to 100 MiB of workbooks.
ANALYSIS_LOCK = threading.Lock()


def analyse(payload):
    files = payload.get('files') if isinstance(payload, dict) else None
    if not isinstance(files, list) or not 1 <= len(files) <= 20:
        raise ValueError('Select between 1 and 20 Excel case files.')
    with TemporaryDirectory(prefix='nebulax-acv-') as directory:
        seen, total = set(), 0
        for item in files:
            if not isinstance(item, dict):
                raise ValueError('Invalid upload.')
            name = item.get('name')
            if (not isinstance(name, str) or not name or Path(name).name != name
                    or '/' in name or '\\' in name or '\x00' in name
                    or name.startswith('~$') or Path(name).suffix.lower() != '.xlsx'):
                raise ValueError('Use original .xlsx filenames, without folder paths or Excel lock files.')
            if name.casefold() in seen:
                raise ValueError('Duplicate filenames. Select each case once.')
            seen.add(name.casefold())
            try:
                content = base64.b64decode(item.get('content', ''), validate=True)
            except (ValueError, TypeError, binascii.Error) as exc:
                raise ValueError('Could not read the uploaded file. Select it again.') from exc
            total += len(content)
            if not content or total > 100 * 1024 * 1024:
                raise ValueError('Files must be nonempty and total no more than 100 MiB.')
            (Path(directory) / name).write_bytes(content)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            predictions = create_predictions(directory)
        cases = []
        for name in predictions['file_id']:
            path = Path(directory) / name
            ranking = rank_file(path)
            fields = {'Time'}
            for row in ranking.itertuples():
                names = STANDARD if row.layout == 'standard' else RICH
                fields.update(f'Car {row.car} - {field}' for field in names[:2])
            data = pd.read_excel(path, usecols=lambda col: col in fields)
            times = pd.to_datetime(data['Time'], errors='raise')
            charts = {}
            for row in ranking.itertuples():
                names = STANDARD if row.layout == 'standard' else RICH
                charts[row.car] = {}
                for key, field in zip(('indoor', 'target'), names[:2]):
                    values = pd.to_numeric(data[f'Car {row.car} - {field}'], errors='raise')
                    charts[row.car][key] = [float(v) if np.isfinite(v) else None for v in values]
            cases.append({'file_id': name, 'ranking': json.loads(ranking.to_json(orient='records', double_precision=15)),
                          'times': [t.isoformat() for t in times], 'charts': charts})
        return {'cases': cases, 'warnings': list(dict.fromkeys(str(w.message) for w in caught)),
                'csv': predictions.to_csv(index=False)}


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def send_json(self, status, value):
        body = json.dumps(value, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != '/api/acv/analyse':
            self.send_json(404, {'error': 'Unknown endpoint.'})
            return
        port = self.server.server_port
        allowed = {f'http://127.0.0.1:{port}', f'http://localhost:{port}'}
        if self.headers.get('Origin') not in allowed:
            self.send_json(403, {'error': 'Open the app from its local server address.'})
            return
        if self.headers.get_content_type() != 'application/json':
            self.send_json(415, {'error': 'Expected a JSON upload.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                self.send_json(413, {'error': 'Upload too large. Use a smaller batch (100 MiB maximum).'})
                return
            payload = json.loads(self.rfile.read(length))
            if not ANALYSIS_LOCK.acquire(blocking=False):
                self.send_json(409, {'error': 'Another analysis is running. Wait for it to finish and retry.'})
                return
            try:
                result = analyse(payload)
            finally:
                ANALYSIS_LOCK.release()
            self.send_json(200, result)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            self.send_json(400, {'error': f'Analysis failed: {exc}'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8503)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(ROOT)))
    print(f'Open http://127.0.0.1:{args.port}/ — ACV uploads enabled. Ctrl+C stops the server.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

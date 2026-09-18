"""Shared production entry point. Private Firestore, visitor-scoped results."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import logging
import os
import re
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from flask import Flask, request, jsonify, send_from_directory, g
from werkzeug.exceptions import HTTPException
from pipelines import analyse_file
from google.cloud import storage

ROOT=Path(__file__).resolve().parent
app=Flask(__name__,static_folder=None)
app.config['MAX_CONTENT_LENGTH']=30*1024*1024
LOCK=threading.Lock()
LOCAL={}
DB=None
DATASET_PREFIX='datasets/966c976005db2e3e40a691cff268fdb8f396a5df'

def test_blobs(component):
    if component not in {'rail','door','acv','shm'}: raise ValueError('Unknown component')
    bucket=os.environ.get('DATA_BUCKET')
    if not bucket: raise ValueError('Official cloud test records are unavailable in local mode.')
    return {Path(blob.name).name:blob for blob in storage.Client().list_blobs(bucket,prefix=f'{DATASET_PREFIX}/{component}/test/') if not blob.name.endswith('/')}

@app.get('/api/test-files/<component>')
def list_tests(component):
    try:return jsonify(files=sorted(test_blobs(component)))
    except ValueError as exc:return jsonify(error=str(exc)),400

@app.post('/api/test-files/<component>')
def run_test(component):
    if not LOCK.acquire(blocking=False):return jsonify(error='Another analysis is running. Please retry shortly.'),429
    try:
        files=test_blobs(component);name=(request.get_json(silent=True) or {}).get('filename')
        if name not in files:return jsonify(error='Unknown official test file'),400
        with TemporaryDirectory(prefix='nebulax-test-') as directory:
            path=Path(directory)/name
            files[name].download_to_filename(path)
            result=analyse_file(component,path,name);result['component']=component
            result['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        return jsonify(**result,analysis_id=store(result))
    except ValueError as exc:return jsonify(error=str(exc)),400
    finally:LOCK.release()

def database():
    global DB
    if DB is None:
        from google.cloud import firestore
        DB=firestore.Client(project=os.environ['GOOGLE_CLOUD_PROJECT'],database=os.environ.get('FIRESTORE_DATABASE','nebulax-analyses'))
    return DB

def owner():
    return hashlib.sha256(g.visitor.encode()).hexdigest()

@app.before_request
def visitor():
    token=request.cookies.get('nx_visitor','')
    g.new_visitor=not bool(re.fullmatch(r'[a-f0-9]{64}',token))
    g.visitor=secrets.token_hex(32) if g.new_visitor else token
    if request.method=='POST':
        origin=request.headers.get('Origin')
        if origin and urlsplit(origin).netloc != request.host:
            return jsonify(error='Use the upload form on this website.'),403

@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Cache-Control']='no-store'
    if getattr(g,'new_visitor',False):
        response.set_cookie('nx_visitor',g.visitor,httponly=True,secure=bool(os.getenv('K_SERVICE')),samesite='Strict',max_age=604800)
    return response

@app.errorhandler(Exception)
def failure(exc):
    if isinstance(exc,HTTPException):
        return jsonify(error='File too large; maximum 28 MiB per file.' if exc.code==413 else exc.description),exc.code
    logging.exception('Request failed')
    return jsonify(error='Analysis could not finish. Please check the input or try again.'),500

@app.get('/api/health')
def health():
    return jsonify(status='ok',components=['rail','door','acv','shm'],persistence='firestore' if os.getenv('GOOGLE_CLOUD_PROJECT') else 'local-memory')

def store(result):
    payload=json.dumps(result,allow_nan=False,separators=(',',':'))
    if len(payload.encode())>850_000: raise ValueError('Result too large to save. Use a shorter recording.')
    identifier=secrets.token_hex(16)
    entry=dict(owner=owner(),payload=payload,expires_at=datetime.now(timezone.utc)+timedelta(days=7))
    if os.getenv('GOOGLE_CLOUD_PROJECT'): database().collection('analyses').document(identifier).set(entry)
    else:
        if len(LOCAL)>=100: LOCAL.pop(next(iter(LOCAL)))
        LOCAL[identifier]=entry
    return identifier

@app.get('/api/results/<identifier>')
def retrieve(identifier):
    if not re.fullmatch(r'[a-f0-9]{32}',identifier): return jsonify(error='Result not found'),404
    entry=database().collection('analyses').document(identifier).get().to_dict() if os.getenv('GOOGLE_CLOUD_PROJECT') else LOCAL.get(identifier)
    if not entry or entry['owner']!=owner() or entry['expires_at']<datetime.now(timezone.utc):
        return jsonify(error='Result not found or expired'),404
    return jsonify(**json.loads(entry['payload']),analysis_id=identifier)

@app.post('/api/analyse/<component>')
def analyse(component):
    if component not in {'rail','door','acv','shm'}: return jsonify(error='Unknown component'),404
    upload=request.files.get('file')
    if not upload: return jsonify(error='Choose a recording'),400
    name=upload.filename or ''
    extension='.xlsx' if component=='acv' else '.csv'
    if not name.lower().endswith(extension) or len(name)>180 or name.startswith(('~$','.')) or any(c in name for c in '/\\') or any(ord(c)<32 for c in name):
        return jsonify(error=f'Use a plain {extension} filename.'),400
    if not LOCK.acquire(blocking=False): return jsonify(error='Another analysis is running. Please retry shortly.'),429
    try:
        with TemporaryDirectory(prefix='nebulax-') as directory:
            path=Path(directory)/name
            upload.save(path)
            if not 0<path.stat().st_size<=28*1024*1024: raise ValueError('File must be between 1 byte and 28 MiB.')
            if component=='acv':
                from zipfile import ZipFile, BadZipFile
                try:
                    with ZipFile(path) as archive:
                        if sum(item.file_size for item in archive.infolist())>256*1024*1024: raise ValueError('Expanded workbook is too large.')
                except BadZipFile as exc: raise ValueError('This is not a valid Excel workbook.') from exc
            result=analyse_file(component,path,name)
            result['component']=component
            result['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        identifier=store(result)
        return jsonify(**result,analysis_id=identifier)
    except ValueError as exc:
        return jsonify(error=str(exc)),400
    finally:
        LOCK.release()

@app.get('/')
def home(): return send_from_directory(ROOT,'index.html')

@app.get('/<path:name>')
def assets(name):
    # Never expose source, model bundles, credentials, data directories or listings.
    if Path(name).suffix not in {'.js','.css','.csv','.json','.svg','.png','.ico'} or '..' in Path(name).parts or any(p.startswith('.') for p in Path(name).parts):
        return jsonify(error='Not found'),404
    if name.endswith('.csv') and not name.startswith('downloads/'): return jsonify(error='Not found'),404
    return send_from_directory(ROOT,name)

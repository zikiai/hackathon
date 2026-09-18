"""Bundle the runtime and documents around an already validated predictions.zip."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from build_submission import validate

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--team-dir',type=Path,required=True)
    args=parser.parse_args();team=args.team_dir.resolve()
    assert team.name=='rookies'
    archive=team/'predictions.zip'
    with zipfile.ZipFile(archive) as zipped:
        assert set(zipped.namelist())=={f'{c}_predictions.csv' for c in ('rail','door','acv','shm')}
        for name in zipped.namelist():validate(name.removesuffix('_predictions.csv'),zipped.read(name).decode())
    app=team/'app';app.mkdir(exist_ok=True)
    files=[ROOT/'Dockerfile',ROOT/'.dockerignore',ROOT/'.gcloudignore']
    for folder in ('integrated_app','rail_corrugation/src','door/src','acv/src'):
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    files.extend((ROOT/'shm').glob('*.py'))
    files.extend(ROOT/p for p in ['shm/ui/serve.py','rail_corrugation/artifacts/rail_model.joblib','door/artifacts/door_selected.joblib','shm/shm_shape_model.joblib'])
    for path in files:
        relative=path.relative_to(ROOT)
        assert not any(part in {'.git','.venv','raw','.env'} for part in relative.parts)
        target=app/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    shutil.copy2(ROOT/'docs/submission/APP_README.md',app/'README.md')
    optional=team/'Optional_Items';optional.mkdir(exist_ok=True)
    for name in ('write_up.md','SUBMISSION.md'):shutil.copy2(ROOT/'docs/submission'/name,optional/name)
    manifest={'team':'rookies','video_included':False,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'files':{}}
    for path in sorted(team.rglob('*')):
        if path.is_file() and path.name!='package_manifest.json':manifest['files'][str(path.relative_to(team))]=hashlib.sha256(path.read_bytes()).hexdigest()
    (optional/'package_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    output=team.parent/'rookies-submission.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(team.rglob('*')):
            if path.is_file():zipped.write(path,path.relative_to(team.parent))
    with zipfile.ZipFile(output) as zipped:
        assert zipped.testzip() is None
        assert all(name.startswith('rookies/') for name in zipped.namelist())
        with zipfile.ZipFile(io.BytesIO(zipped.read('rookies/predictions.zip'))) as inner:
            assert len(inner.namelist())==4 and all('/' not in name for name in inner.namelist())
    print(f'VERIFIED {output}: {output.stat().st_size:,} bytes, {len(manifest["files"])} files, no video')

if __name__=='__main__':main()

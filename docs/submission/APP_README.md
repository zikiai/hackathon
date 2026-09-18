# rookies — runnable NebulaX app

- [Public prototype](https://nebulax-workspace-1029817906638.asia-southeast1.run.app/)
- [Repository and methodology](https://github.com/zikiai/hackathon)

Select a component in **Review findings** to see the full official test batch.
Use **New analysis → select component → Browse files → Output predicted result**
to process new records. Choose **Download predictions → Download CSV** to export
the selected batch. Switch between **Official test results** and **Uploaded
results** explicitly; a single upload does not replace the official batch.

## Run locally

This folder includes the runtime code and trusted trained models for all four
components. It excludes raw data and credentials. With Docker installed, run from
this folder:

```sh
docker build -t rookies-nebulax .
docker run --rm -p 8080:8080 rookies-nebulax
```

Open http://localhost:8080. No Google credentials are needed for local uploads;
local result persistence is in-memory. Reuse the organiser's input files, which
are deliberately not included in this package. Rail, Door and SHM use CSV; ACV
uses XLSX. Maximum file size is 28 MiB. Rail/SHM support batches; Door accepts one
continuous recording.

For a Python environment instead, use Python 3.14 (the deployed container version):

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r integrated_app/requirements-cloud.txt
cd integrated_app
python -m gunicorn --bind 127.0.0.1:8080 --workers 1 --threads 2 --timeout 900 cloud_server:app
```

The cloud version uses private Cloud Storage and Firestore. Results are scoped to
the same browser and accessible for seven days. Review notes are not durable and
AI-assisted retraining is not connected. This is a decision-support demo, not a
certified safety tool. Scores in Model evidence use development data, not hidden
test answers. See `../Optional_Items/write_up.md` for assumptions and limitations.

Model bundles are trusted application assets. Never substitute an untrusted
pickle/joblib upload. Public app access does not imply public database access.

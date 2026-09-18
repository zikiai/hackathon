# Shared maintenance workspace

The integrated app supports Rail, Door, ACV and SHM uploads, review and competition
CSV downloads. The production entry point is `cloud_server.py`; `server.py`
contains the ACV adapter/older preview server and is not the full application.

[Public app](https://nebulax-workspace-1029817906638.asia-southeast1.run.app/) ·
[Team README](../README.md) · [Cloud setup](CLOUD_DEPLOYMENT.md)

Use **Official test results** for the complete saved test batch and **Uploaded
results** for the latest successfully processed upload. Downloads follow this
selection. Legacy single-file sessions default to the official batch on upgrade;
saved uploads remain available through the selector.

For local uploads with all four components, install `requirements-cloud.txt`
and ensure the trusted Rail/Door model bundles exist, then run from this folder:

```sh
python -m gunicorn --bind 127.0.0.1:8502 --workers 1 --threads 2 --timeout 900 cloud_server:app
```

No cloud variables means in-memory result storage. Cloud deployment uses private
Firestore and Cloud Storage with the runtime identity; no credentials belong in
the browser. Notes are currently page-memory only. Model evidence describes
development validation, not unknown test-set performance.

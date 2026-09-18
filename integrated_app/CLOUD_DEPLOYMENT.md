# Shared cloud application

## Runtime

The root Dockerfile serves the existing dashboard with Gunicorn/Flask and all
four saved prediction pipelines. No training is performed on uploads.

- Region: `asia-southeast1`
- Service: `nebulax-workspace`
- Public URL: https://nebulax-workspace-1029817906638.asia-southeast1.run.app
- Active revision: `nebulax-workspace-00003-m64`
- Resources: 2 CPUs, 4 GiB RAM, 0–2 instances, request concurrency 8,
  one inference at a time per instance, 900-second request timeout.
- Runtime identity: `nebulax-backend@qwiklabs-gcp-00-27def4c41cb8.iam.gserviceaccount.com`
- Firestore results database: `nebulax-analyses`, collection `analyses`
- Official test files: private bucket `qwiklabs-gcp-00-27def4c41cb8-nebulax-data`
- Existing separate Rail service is not replaced by this deployment.

Runtime environment variables: `GOOGLE_CLOUD_PROJECT`, `FIRESTORE_DATABASE`,
`DATA_BUCKET`; `PORT` is supplied by Cloud Run. No service-account key is needed.

## Behaviour and boundaries

All four components accept new uploads. Each file is sent separately, at most
28 MiB per file and 68 files per batch. Door accepts one continuous recording.
Uploads are temporary and removed after inference. A failed batch does not
replace the previous displayed results or produce a partial combined export.

Saved results are scoped to an opaque HttpOnly browser cookie. Firestore stores
only the cookie hash and compact result JSON, not the raw file. Result IDs in
localStorage retain references to successful batches. The page always opens the
complete official test batch; a new upload displays its predictions immediately.
Results are inaccessible
after seven days; this is application expiry, not automatic database deletion.
Clearing cookies loses access. There is no cross-device user account system.
Review notes are still in-memory; they are not claimed to be durable records.

Official saved examples remain available for all four components. These are
unlabelled test predictions, not accuracy measurements. ACV chart points are
sampled for display; every eligible reading still contributes to its ranking.
The page opens with complete official test results, without a source selector.
New uploads open immediately; reloading restores the full official batch.
Previous one-file browser sessions therefore cannot hide the complete batch.

Only the Cloud Run application is public. Storage, Firestore and credentials
must not be made public. Firestore access uses database-scoped IAM. The static
server allowlist excludes Python source and model files. Upload origins are
checked, files are size-limited, and inference is serialized within each
instance. This is a public hackathon demo, not a production safety system.
Instance limits reduce exposure but are not a hard spending cap.

## Build prerequisites

These two bundles must exist before building:
`rail_corrugation/artifacts/rail_model.joblib` and
`door/artifacts/door_selected.joblib`. Rail is tracked from the selected shared-side release; Door remains gitignored. SHM uses the tracked
`shm/shm_shape_model.joblib`. Copy only trusted trained bundles; never load a
user-uploaded pickle/joblib file. Dependency versions are in
`integrated_app/requirements-cloud.txt`.

Install those dependencies, then run locally from `integrated_app`:

```sh
python -m gunicorn --bind 127.0.0.1:8502 --workers 1 --threads 2 --timeout 900 cloud_server:app
```

Without `GOOGLE_CLOUD_PROJECT`, results use bounded local memory for testing.
Do not set cloud variables for ordinary offline tests.

## Checks

Run `python -m unittest discover -s integrated_app -p 'test_*server.py'`.
`verify_cloud_pipelines.py --source <local-repo>` compares official-file
predictions to previous exports without retraining. It also regenerates the
saved ACV example. Its SHM fixture is documented in that script.

Before releasing, check health, all four upload types, exact CSV columns,
Firestore save/reload, cross-visitor denial, and unauthenticated access to the
website while storage/database remain private.

Verified on 19 September 2026: anonymous website and health access, real
multipart uploads for all four components, saved-result retrieval and
cross-visitor denial. Rail upload and refresh restoration were also checked
through the public browser UI. Cloud-side predictions matched the existing
exports for one Rail and one SHM file, the complete Door test recording and
the ACV workbook. This does not establish hidden-test prediction accuracy.

Submission preparation then reran all 86 official inputs through the deployed
app endpoint: 68 Rail files, Door Test.csv (38 movements), one ACV workbook and
16 SHM files. All predictions matched the saved exports (SHM within numeric
tolerance). Archive validation checks exact headers, complete file coverage,
allowed labels, Door intervals, ACV car IDs and finite SHM values. The manifest
is included in the rookies submission package, outside predictions.zip.

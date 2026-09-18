# Rail Cloud Run deployment handoff

Status: configuration prepared; container build and hosted service have not been verified. The assigned project ID is still needed. The current machine has neither Docker nor gcloud installed. This deploys Rail only; the other subsystems are not integrated here.

The source bundle must contain the saved model and metrics in `artifacts/`. They are Git-ignored and must be transferred privately to the team's deployment environment or recreated with the documented training command. Raw organizer data is excluded from the build context. The runtime file pins the core library versions used with this saved model; transitive dependencies are resolved during the build.

From `rail_corrugation/`, on a machine with authenticated Google Cloud CLI access, replace both placeholders with the team's assigned values:

```bash
gcloud run deploy nebulax-rail \
  --source . \
  --project YOUR_ASSIGNED_PROJECT_ID \
  --region YOUR_ASSIGNED_REGION \
  --port 8080 --memory 2Gi --cpu 1 \
  --concurrency 1 --max-instances 2 --timeout 300 \
  --allow-unauthenticated
```

The final flag makes the demo publicly accessible. Use it for the public judging URL only when that is the team's intended access setting and project policy permits it. Source deployment uses Cloud Build and requires its APIs, permissions, and billing to be available in the assigned project. Use the workshop's setup instructions for project provisioning.

After deployment, open the returned URL in a signed-out browser, upload a valid 10,000-row recording, compare its result with the local app, and download its CSV. Check that a malformed upload and duplicate filenames prevent batch download. Verify the performance tab and record the URL in the root README. Do not mark deployment complete until these checks pass.

The app listens on `0.0.0.0` and the injected `PORT`, as required by the [Cloud Run container contract](https://cloud.google.com/run/docs/container-contract). A Dockerfile in the source directory is used by [Cloud Run source deployment](https://cloud.google.com/run/docs/deploying-source-code).

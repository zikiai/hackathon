# Rail release status

The selected model is the shared-side Random Forest with 20 selected features and a 0.40 fault threshold. The team reported approximately 0.83 on the competition scorer.

- All 68 rail predictions match the selected submission exactly.
- Output columns are `file_id,prediction`; labels are `Normal`, `Side I` and `Side II`.
- The selected output contains 57 Normal, 4 Side I and 7 Side II predictions.
- The shared application serves all four components on Google Cloud Run.
- Cloud-generated CSVs match the selected submission for every component.
- Upload inference, saved-result retrieval and visitor isolation were verified.

Training-validation scores are separate from competition scores. Repeated development splits are not an independent holdout. Model outputs require inspection confirmation.

See [model details](../docs/rail-model-release.md), [deployment checks](../integrated_app/CLOUD_DEPLOYMENT.md) and the [project README](../README.md).

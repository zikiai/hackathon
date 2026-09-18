# Google Cloud services

The shared application runs on Cloud Run in `asia-southeast1`. Cloud Storage holds the official input files privately, and Firestore stores browser-scoped analysis results.

Inference uses saved Python models and deterministic analysis pipelines. It does not require a language-model API or retraining on uploads.

See [deployment configuration](../integrated_app/CLOUD_DEPLOYMENT.md) for the active revision, runtime settings and verification results.

## Operating safeguards

- Keep raw data, Firestore and credentials private.
- Never commit service-account keys or environment secrets.
- Keep the temporary project active through judging.
- Monitor resource usage; instance limits are not a hard spending cap.
- Retain local prediction commands and the selected model for reproducibility.

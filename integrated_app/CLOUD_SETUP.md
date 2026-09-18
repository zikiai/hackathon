# NebulaX cloud setup — 19 September 2026

Project: `qwiklabs-gcp-00-27def4c41cb8` (1029817906638).
Region: `asia-southeast1` (Singapore).

Created:
- Cloud Storage bucket `qwiklabs-gcp-00-27def4c41cb8-nebulax-data`, with uniform bucket-level access and public access prevention.
- Firestore Native, Standard edition, `(default)` database in Singapore.

Test data layout: `datasets/966c976005db2e3e40a691cff268fdb8f396a5df/{rail,door,acv,shm}/test/<filename>`.
Source: organiser repository aochinwen/NebulaX-Hackathon-ProblemStatement at the pinned commit above.
Expected counts: Rail 68 CSV, Door 1 CSV, ACV 1 XLSX, SHM 16 CSV.
Transfer complete: all 86 files matched source sizes and Git blob SHA-1 checksums before upload. SHA-256 digests are stored in object metadata and Firestore. Independent listing confirmed 86 objects and 86 catalogue documents with the expected per-component counts. Public access prevention is enforced and uniform access is enabled.

Firestore `datasets` documents contain component, filename, storage_uri, source_commit, source_path, sha256, size_bytes, split and availability status. These are file catalogue entries, not predictions or ground truth.

Raw files remain private. Existing Rail Cloud Run service and its deployment bucket are unchanged.

The shared application is now deployed to `nebulax-workspace` in Singapore:
https://nebulax-workspace-1029817906638.asia-southeast1.run.app

Public Cloud Run invocation was enabled with the owner's explicit approval.
All four existing pipelines support uploads, result retrieval and CSV exports;
ACV accepts XLSX. The runtime service account has bucket-scoped object read
access and database-scoped access to the separate `nebulax-analyses` database.
It does not have write access to the `(default)` catalogue database. Firestore,
raw objects and credentials are not public.

Private cloud checks passed for one official Rail recording, the full Door test
recording, the ACV workbook and one SHM recording. Predictions matched previous
exports; cloud object reads, Firestore save/read and cross-visitor denial passed.
These are integration checks, not accuracy measurements on hidden test labels.

See `CLOUD_DEPLOYMENT.md` for build prerequisites, limits and remaining demo
boundaries, including temporary review notes and seven-day result access.

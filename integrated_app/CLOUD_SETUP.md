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

Raw files are private. No public access or extra service-account permissions were granted. Existing Rail Cloud Run service and its deployment bucket are unchanged.

Remaining integration: backend upload/validation/inference, analysis ownership and status, prediction persistence/downloads, deployed shared frontend, and permission verification for the runtime service account. Firestore server access uses IAM; browser access must not be opened with permissive rules. ACV requires XLSX support rather than the current generic CSV-only picker.

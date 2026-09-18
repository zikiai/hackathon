# Structural Health integration

The shared app consumes this component through getRecords/renderStatistics and
uses its existing navigation, finding selection, review notes and CSV download.
Only view.css styles SHM content, under .shm-insight. The standalone SHM app's
global styles, navigation and uploader are not imported.

Evidence contains actual predictions from the 16 official test files at organiser
commit 966c976005db2e3e40a691cff268fdb8f396a5df. Computation reuses shm/ui/serve.py
Engine and the merged SHM model. Source SHA-256 and model-version hashes are
included. Stress-chart points are min/max summaries, not raw recordings.
No test accuracy is claimed. New user-upload inference is still not connected.

Regenerate with build_reference_examples.py --repo REPO --input TEST_DIRECTORY.
The training score shown in evaluation-results.json is approximately 0.9798,
derived from the teammate-reported 2.020% grouped-validation MAPE in
shm/ui/shm_page.js; that validation was not independently rerun for integration.

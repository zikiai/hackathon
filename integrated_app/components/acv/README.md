# Air conditioning component

The ACV workspace analyses `.xlsx` recordings and ranks cars for inspection. Its adapter calls the same `create_predictions` and `rank_file` functions in `acv/src/baseline.py` used by the command-line pipeline.

The output is `acv_predictions.csv`, with columns `file_id,ranked_cars`. Car identifiers retain the workbook's two-digit IDs and are separated by `|`.

The review page shows inspection priority, car-specific temperature evidence and the recorded training-data evaluation. Charts are descriptive; temperature gaps do not prove a refrigerant leak. Unavailable measurements must not be presented as healthy results.

Component-specific presentation belongs in this directory. Shared navigation, uploads and exports are maintained in the application shell. Escape filenames and user-provided text before inserting them into HTML.

The component has been integrated and checked through the deployed shared service. See [deployment verification](../../CLOUD_DEPLOYMENT.md).

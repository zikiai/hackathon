# Selected rail model — 19 September 2026

Promoted `shared-side-20-t040` after the team reported approximately **0.83** on the competition scorer. This is a rounded user-reported score, not an independently retrieved exact score or a percentage of correctly classified files.

The saved model and the 68 prepared dashboard predictions reproduce the accepted experimental CSV exactly:

`9bf05ffa10472777ecf885c34527144fabf32e0e15b8b64fbf24ca35cf68a147` (SHA-256).

## Model

One binary Random Forest learns each side's fault target from the original and side-exchanged views of every training recording. Both views stay within their original training fold. Median imputation and ANOVA selection retain 20 features. The forest uses 400 trees, balanced class weights, a minimum leaf size of 2 and seed 42. At inference, the model checks both orientations. The higher-scoring side is selected if its raw score is at least 0.40; otherwise the result is Normal. Side exchange assumes mirror-equivalent sensor roles.

Normalized three-class scores are not calibrated probabilities and their argmax is not the decision rule. The dashboard displays the raw side scores and the threshold.

## Evaluation

Five-fold validation on 272 labelled recordings: mean macro F1 **0.827808** over screening seeds 11, 23 and 59. The previous 30-feature/0.35 model averaged 0.807938. Two additional seeds (79, 101) averaged **0.818237** versus 0.811742; the new model did not win both. Repeated splits reuse development data and are not an untouched holdout. Public competition feedback informed the sequence of experiments; no hidden labels or manual per-file edits were used.

The screen compared feature counts 20, 30, 40 and thresholds 0.30, 0.35, 0.40, 0.45. The highest screening mean selected this configuration before generating test predictions.

## Reproduction and scope

`python -m rail_cdm.train` now builds the promoted model through `make_production_model`. The old `make_final_model` factory remains available as a historical baseline for experiment reproducibility. To rebuild the selected release and verify its exact 68-file output, run `PYTHONPATH=rail_corrugation/src python tools/prepare_rail_release.py --source <repo-with-local-datasets>` with the pinned runtime dependencies.

The trusted, fitted rail bundle is now tracked in Git. It is included in the container build, not served as a public static download. Never load user-supplied joblib/pickle files. Door, ACV and SHM models, prediction files and UI designs are unchanged. Cloud Storage and Firestore remain private.

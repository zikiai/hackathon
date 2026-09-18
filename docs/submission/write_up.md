# rookies — NebulaX maintenance workspace

## Solution and problem fit

Train-maintenance teams must turn different sensor streams into useful inspection
decisions. Our prototype brings all four PS3 tasks into one browser workflow:
select a subsystem, upload a record, review the prediction and supporting
measurements, then download the competition-formatted output.

Rail predicts Normal, Side I or Side II corrugation. Door locates movements in a
continuous stream and classifies each as Normal or Abnormal resistance. ACV ranks
cars for inspection. Structural health estimates cumulative fatigue damage. We
retain these distinctions instead of forcing every task into one anomaly score.

## What differentiates the solution

The contribution combines task-specific pipelines with one evidence-led review
workflow. Rail shows side-by-side vibration/shock measurements; Door shows detected
movements and current-pattern evidence; ACV shows the full inspection order and
temperature-gap comparisons; SHM shows stress/cycle evidence and a damage estimate.
Guidance turns each result into a proposed technician check, not an automatic
maintenance command.

The complete official test batch is shown when the page opens. New uploads open
their predictions immediately; reloading restores the complete test batch rather
than a previous single-file upload. Downloads follow the displayed results and
preserve each component's required output schema.

## Modelling approach

**Rail corrugation.** Multichannel vibration/shock summaries feed a 30-feature,
500-tree Random Forest. Feature selection and moderate SMOTE are fitted inside
training folds. A fixed 1.5× Side I score adjustment addresses missed minority
faults. Candidate preprocessing and model settings were compared on development
data; the selected configuration was frozen before submission inference.
Side-to-side RMS comparisons are descriptive evidence, not deterministic fault
thresholds or causal explanations.

**Door operation.** The detector splits the supplied stream at time gaps greater
than 0.2 seconds. Seven features describe mean/peak absolute current, variability,
current in each elapsed-time third, and direction inferred from position change.
A balanced Random Forest uses 200 trees, maximum depth four and minimum leaf size
three. Segment boundaries retain source timestamps. This detector assumes the
supplied recording construction; missing packets or continuous idle telemetry
could invalidate its gap-based segmentation.

**Air conditioning.** The baseline identifies car IDs from workbook headers and
filters eligible cooling readings. It ranks cars by average positive indoor-to-
target temperature gap; finite zero gaps remain in the average. Exact ties use
car ID. Cars without usable readings appear last by ID without being declared
healthy. The rule has no fitted parameters. Ranking uses all eligible readings,
although charts may be sampled. Temperature deviation suggests inspection
priority, not proof of a refrigerant leak.

**Structural health.** Stress summaries and rainflow cycle-range statistics describe
each recording. A fifth-power cycle-range sum supplies a damage proxy; a
standardised Ridge model learns a log correction using stress/cycle-shape features.
The proxy multiplied by the exponentiated correction gives cumulative damage.
This is not a certified fatigue assessment or remaining-service-life forecast.

## Evaluation and limitations

| Component | Organiser metric | Development evidence |
|---|---|---|
| Rail | Macro F1 over three classes | 0.823353 on fixed five-fold validation of 272 recordings; mean 0.822854 across five split arrangements |
| Door | IoU-weighted F1 for timing and label | 1.0000 on five chronological blocks covering 110 movements; forward and similar-curve-exclusion checks also reported 1.0000 |
| ACV | Linear rank-decay | 0.9792 on six labelled cases: true faulty car first in five cases, second in one |
| SHM | max(0, 1 − MAPE), MAPE as a fraction | Teammate-reported grouped MAPE 2.020%, giving 0.9798 |

These are development results, not held-out test scores or comparable accuracy
percentages. Only the organiser has the test answers. We do not claim a combined
hidden-test score; the organiser weights all four component scores equally.

Development data were reused during exploration. Rail's fold-fitted preprocessing
reduces leakage, but repeated candidate selection can still cause optimism. Door's
perfect result is not a guarantee on new doors. ACV's six cases are few and informed
development. SHM's grouped result is teammate-reported and was not independently
rerun during integration. Software parity and format checks do not validate the
unknown test labels. Independent asset-level evaluation remains necessary.

## Technology and cloud integration

HTML/CSS/JavaScript provide the interface. Python, Flask and Gunicorn serve saved
pipelines using NumPy, pandas, SciPy, scikit-learn, imbalanced-learn, joblib,
openpyxl and rainflow. Google Cloud Run hosts the shared container. Private Cloud
Storage holds all 86 official test inputs; private Firestore stores compact
results scoped to an opaque browser cookie. Raw uploads are temporary and removed
after inference. The public app requires no judge login; storage and credentials
are not public.

Saved results are accessible in the same browser for seven days; this is application
expiry, not automatic database deletion. Review notes remain in page memory. Size
limits, narrow runtime permissions and bounded instances support a small demo,
not production-scale abuse protection. The temporary cloud-project lifetime must
cover judging.

## Reproducibility and future work

All 86 official inputs were run through the deployed app's prediction endpoint,
using the same saved-model adapter as the upload form. No model training or
selection occurred during this run. The separate validation manifest records input
filenames/hashes, output schemas, row counts and checksums. The prediction archive
contains only the four required CSVs at its root. The app bundle includes runtime
code and trusted trained models, without raw datasets or credentials.

Next steps are independent validation, unfamiliar-input monitoring, durable
authenticated review records and stronger cost controls. The AI improvement tab
describes a future capability: verified findings could support AI-assisted code
or feature suggestions, followed by tests and human approval. Gemini and Vertex
AI are not currently used for inference or automatic retraining.

## Reference

[Official PS3 specifications and info kits](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/tree/966c976005db2e3e40a691cff268fdb8f396a5df/PS3).
This write-up covers Door, ACV, Rail Corrugation and SHM.

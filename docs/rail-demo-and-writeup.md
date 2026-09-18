# Rail demo script and short write-up

## 2–3 minute demo script

**0:00–0:25 — Problem.** Rail corrugation changes the vibration measured around train axle boxes. Our Rail prototype turns one-second sensor recordings into a clear classification: Normal, Side I, or Side II, with a downloadable prediction file.

**0:25–1:15 — Live flow.** Open the Rail app. Upload one or two organizer test recordings. Explain that each file has 10,000 readings across speed and 128 sensor channels. Show the predicted condition, then the measured vibration RMS comparison between the two rail sides. Explain that the model uses 30 measurements; the bar chart is supporting evidence rather than the classification rule. Download rail_predictions.csv and show its two columns.

**1:15–1:55 — Evidence.** Open Model performance. We trained on 272 labelled recordings. Only 14 are Side I, so accuracy alone is insufficient. Five-fold validation achieved macro F1 0.8234 and Side I recall 78.6%. Across five different fold arrangements, mean macro F1 was 0.8229. Every held-out prediction came from a model trained without that recording, with feature selection and synthetic oversampling fitted inside each fold. These are development validation scores, not hidden-test scores.

**1:55–2:25 — Model choice and limits.** Our pipeline selects 30 sensor measurements and uses a 500-tree Random Forest with moderate oversampling. We tested alternatives, including 19 final refinements; none justified replacing the current model. Rare Side I faults remain the main limitation, and model scores are not guarantees of correctness.

**2:25–2:45 — Close.** The Rail prototype provides a tested upload-to-download flow and a verified file containing predictions for all 68 test recordings. It demonstrates how measured sensor evidence can support maintenance triage.

Show a hosted URL only after deployment is verified. Do not claim other subsystems are integrated unless teammates have completed and demonstrated them. Record the actual app; this file is the script, not the video deliverable.

## Short write-up

NebulaX Rail Corrugation Monitor classifies one-second axle-box recordings as Normal, Side I, or Side II. It validates the supplied 129-column, 10,000-row CSV format, extracts vibration and shock summaries plus frequency-band energy and side comparisons, and generates the official two-column prediction CSV.

The solution uses Python, pandas, NumPy, SciPy, scikit-learn, imbalanced-learn, and Streamlit. Its fitted pipeline imputes missing feature values, removes constant measurements, selects 30 features, applies moderate SMOTE oversampling, and trains a 500-tree Random Forest. A fixed Side I score adjustment addresses the rare fault class. Feature selection and oversampling occur inside each validation fold.

On 272 labelled recordings, the fixed five-fold development validation achieved macro F1 0.8234, accuracy 94.1%, and Side I recall 78.6%. Mean macro F1 across five shuffled validation arrangements was 0.8229. A final comparison of 19 nearby configurations found no improvement, so the simpler active model was retained. The 68 test predictions were reproduced exactly and checked for complete filename coverage and valid output labels.

The app presents predictions, measured side-to-side vibration evidence, validation performance, and CSV download. It prevents incomplete or duplicate-file exports. Its distinguishing design choices are recording-level validation, explicit treatment of rare faults, and evidence-based rejection of added model complexity. Validation has informed model selection and does not guarantee hidden-test performance. Further work should focus on additional labelled fault examples and confirmation of the rotating-speed unit before physical order analysis.

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from rail_cdm.dashboard import (
    confusion_matrix_frame,
    load_metrics,
    per_class_metrics,
    validation_errors,
)
from rail_cdm.features import extract_features
from rail_cdm.io import ALLOWED_LABELS, read_sensor_csv
from rail_cdm.predict import validate_prediction_output

APP_ROOT = Path(__file__).resolve().parent
MODEL_PATH = APP_ROOT / "artifacts/rail_model.joblib"
METRICS_PATH = APP_ROOT / "artifacts/metrics.json"
CV_PREDICTIONS_PATH = APP_ROOT / "artifacts/cross_validation_predictions.csv"
MODEL_COMPARISON_PATH = APP_ROOT / "outputs/model_comparison.csv"
TUNING_DIR = APP_ROOT / "outputs/tuning"
SHIFT_AUDIT_PATH = APP_ROOT / "outputs/generalization/distribution_shift.json"

st.set_page_config(page_title="Rail Corrugation Monitor", page_icon="🚆", layout="wide")
st.title("Rail Corrugation Monitor")
st.write("Predict rail conditions and check how reliably the model performs before submission.")

prediction_tab, performance_tab = st.tabs(["Predict files", "Model performance"])

with prediction_tab:
    st.subheader("Predict new rail recordings")
    st.write(
        "Upload one or more one-second axle-box sensor CSV files. The saved model will "
        "classify each file as Normal, Side I, or Side II."
    )
    st.caption(
        "Each CSV must contain 10,000 readings and 129 columns: speed, then 128 sensor channels."
    )

    if not MODEL_PATH.exists():
        st.warning("Train the model first. The app expects artifacts/rail_model.joblib.")
    else:
        bundle = joblib.load(MODEL_PATH)
        model = bundle["model"]
        feature_columns = bundle["feature_columns"]

        uploads = st.file_uploader("Rail sensor CSV files", type="csv", accept_multiple_files=True)

        if uploads:
            rows: list[dict[str, object]] = []
            details: list[dict[str, object]] = []
            evidence: dict[str, dict[str, float]] = {}

            with st.spinner("Extracting signal features and making predictions..."):
                for upload in uploads:
                    try:
                        frame = read_sensor_csv(upload)
                        features = extract_features(frame)
                        feature_frame = pd.DataFrame([features]).reindex(columns=feature_columns)
                        prediction = str(model.predict(feature_frame)[0])
                        probabilities = model.predict_proba(feature_frame)[0]
                        confidence_by_class = dict(zip(model.classes_, probabilities, strict=True))
                        if prediction not in ALLOWED_LABELS:
                            raise ValueError(f"Unexpected model output: {prediction}")

                        rows.append({"file_id": upload.name, "prediction": prediction})
                        evidence[upload.name] = {
                            "Side I": features["side1_vibration_rms_mean"],
                            "Side II": features["side2_vibration_rms_mean"],
                        }
                        details.append(
                            {
                                "file": upload.name,
                                "prediction": prediction,
                                **{
                                    f"P({name})": value
                                    for name, value in confidence_by_class.items()
                                },
                            }
                        )
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"{upload.name}: {exc}")

            if rows:
                predictions = pd.DataFrame(rows, columns=["file_id", "prediction"])
                st.subheader("Predictions")
                st.dataframe(pd.DataFrame(details).style.format(precision=3), width="stretch")
                st.caption(
                    "Class scores include the fixed Side I adjustment. They are model scores, "
                    "not a measured probability that a prediction is correct."
                )
                selected_file = st.selectbox("Signal comparison for", list(evidence))
                st.bar_chart(
                    pd.DataFrame.from_dict(
                        evidence[selected_file], orient="index", columns=["Mean vibration RMS"]
                    )
                )
                st.caption(
                    "RMS summarizes measured vibration strength across each side. "
                    "This is supporting signal evidence; the classifier uses 30 measurements."
                )

                try:
                    validate_prediction_output(predictions, [upload.name for upload in uploads])
                except ValueError as exc:
                    st.warning(str(exc))
                else:
                    st.success(f"All {len(predictions)} recordings are ready to download.")
                    csv_bytes = predictions.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download rail_predictions.csv",
                        data=BytesIO(csv_bytes),
                        file_name="rail_predictions.csv",
                        mime="text/csv",
                    )

with performance_tab:
    st.subheader("Cross-validation results")
    st.caption(
        "These results come only from the labelled training files. Each file was predicted "
        "by a fold that did not train on that file."
    )

    if not METRICS_PATH.exists():
        st.warning("Run rail-train first to create artifacts/metrics.json.")
    else:
        metrics = load_metrics(METRICS_PATH)
        report = metrics["classification_report"]
        class_scores = per_class_metrics(metrics)
        side_i = class_scores.loc[class_scores["Class"] == "Side I"].iloc[0]

        score_col, accuracy_col, side_i_col, folds_col = st.columns(4)
        score_col.metric("Competition score (macro F1)", f"{metrics['macro_f1']:.1%}")
        accuracy_col.metric("Overall accuracy", f"{report['accuracy']:.1%}")
        side_i_col.metric("Side I recall", f"{side_i['Recall']:.1%}")
        folds_col.metric("Validation folds", metrics["cross_validation_folds"])

        st.info(
            "Accuracy counts every correct file equally. Macro F1 gives Normal, Side I, and "
            "Side II equal importance, so it exposes the weaker Side I detection. Use macro "
            "F1 as the main score when comparing improvements."
        )
        if adjustment := metrics.get("decision_adjustment"):
            descriptions = ", ".join(
                f"{class_name} evidence × {multiplier:g}"
                for class_name, multiplier in adjustment.items()
            )
            st.caption(
                f"Decision calibration: {descriptions}. This fixed adjustment was selected "
                "using repeated cross-validation to reduce missed rare faults."
            )

        chart_col, distribution_col = st.columns(2)
        with chart_col:
            st.markdown("#### Score by rail condition")
            score_chart = class_scores.set_index("Class")[["Precision", "Recall", "F1"]]
            st.bar_chart(score_chart, y_label="Score", stack=False)
        with distribution_col:
            st.markdown("#### Labelled files by rail condition")
            st.bar_chart(class_scores.set_index("Class")[["Files"]], y_label="Files")
            st.caption(
                "A bar chart is clearer than a pie chart here: only 14 Side I files are "
                "available, compared with 234 Normal files."
            )

        st.markdown("#### Exact class results")
        st.dataframe(
            class_scores.style.format({"Precision": "{:.1%}", "Recall": "{:.1%}", "F1": "{:.1%}"}),
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### Confusion matrix")
        st.caption("Rows are the real answers; columns are the model's predictions.")
        st.dataframe(
            confusion_matrix_frame(metrics).style.background_gradient(cmap="Blues", axis=None),
            width="stretch",
        )

        if CV_PREDICTIONS_PATH.exists():
            validation_predictions = pd.read_csv(CV_PREDICTIONS_PATH)
            mistakes = validation_errors(validation_predictions)
            with st.expander(f"Review the {len(mistakes)} incorrect validation files"):
                st.caption(
                    "Confidence is the winning probability. Margin is the gap between the "
                    "first and second choices; a small margin means the model was uncertain."
                )
                selected_class = st.selectbox(
                    "Show actual class",
                    ["All", *metrics["confusion_matrix_labels"]],
                )
                shown_mistakes = mistakes
                if selected_class != "All":
                    shown_mistakes = mistakes.loc[mistakes["Actual"] == selected_class]
                probability_columns = [
                    column
                    for column in [
                        "P(Normal)",
                        "P(Side I)",
                        "P(Side II)",
                        "Confidence",
                        "Margin",
                    ]
                    if column in shown_mistakes.columns
                ]
                st.dataframe(
                    shown_mistakes.style.format(
                        {column: "{:.1%}" for column in probability_columns}
                    ),
                    width="stretch",
                    hide_index=True,
                )

                error_routes = (
                    mistakes.groupby(["Actual", "Predicted"], as_index=False)
                    .size()
                    .rename(columns={"size": "Files"})
                    .sort_values("Files", ascending=False)
                )
                st.markdown("##### Error routes")
                st.dataframe(error_routes, width="stretch", hide_index=True)

        if SHIFT_AUDIT_PATH.exists():
            shift_audit = json.loads(SHIFT_AUDIT_PATH.read_text(encoding="utf-8"))
            st.markdown("#### Generalization check")
            st.caption(
                "This check does not use hidden test answers. It asks whether the selected "
                "measurements in the test files look unlike those in training."
            )
            auc_column, ks_column, features_column = st.columns(3)
            auc_column.metric(
                "Train/test distinguishability",
                f"{shift_audit['domain_classifier_auc']:.3f} AUC",
            )
            ks_column.metric(
                "Median feature shift",
                f"{shift_audit['median_ks_statistic']:.3f} KS",
            )
            features_column.metric("Measurements checked", shift_audit["selected_features"])
            st.info(
                "An AUC near 0.5 means the audit model cannot reliably tell training and test "
                "files apart. That is reassuring, although it cannot reveal the hidden labels."
            )

        tuning_files = sorted(TUNING_DIR.glob("*_summary.csv"))
        if tuning_files:
            st.markdown("#### Hyperparameter experiments")
            st.caption(
                "Each result is the average of five shuffled five-fold validations. The active "
                "model is not replaced automatically."
            )
            tuning_by_name = {
                path.stem.removesuffix("_summary").replace("-", " ").title(): path
                for path in tuning_files
            }
            selected_stage = st.selectbox("Tuning stage", list(tuning_by_name))
            tuning = pd.read_csv(tuning_by_name[selected_stage])
            st.bar_chart(
                tuning.set_index("candidate")[["macro_f1_mean"]],
                y_label="Average macro F1",
            )
            shown_columns = [
                "candidate",
                "macro_f1_mean",
                "macro_f1_std",
                "side_i_precision_mean",
                "side_i_recall_mean",
                "side_i_f1_mean",
                "side_ii_f1_mean",
            ]
            st.dataframe(
                tuning[shown_columns].style.format(
                    {column: "{:.1%}" for column in shown_columns if column != "candidate"}
                ),
                width="stretch",
                hide_index=True,
            )

        if MODEL_COMPARISON_PATH.exists():
            comparison = pd.read_csv(MODEL_COMPARISON_PATH).sort_values("macro_f1", ascending=False)
            st.markdown("#### Model comparison")
            st.caption(
                "All models were checked with the same cross-validation splits. Higher macro "
                "F1 is better."
            )
            st.bar_chart(comparison.set_index("model")[["macro_f1"]], y_label="Macro F1")
            st.dataframe(
                comparison.style.format(
                    {column: "{:.1%}" for column in comparison.columns if column != "model"}
                ),
                width="stretch",
                hide_index=True,
            )

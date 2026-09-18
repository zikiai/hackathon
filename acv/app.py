"""Standalone ACV screen: streamlit run acv/app.py."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import warnings

import numpy as np
import pandas as pd
import streamlit as st

from src.baseline import RICH, STANDARD, create_predictions, rank_file


def analyse_uploads(uploads):
    """Use the existing pipeline without persisting uploaded data."""
    cases = {}
    filenames = [u.name for u in uploads]
    if len(filenames) != len(set(filenames)):
        raise ValueError("Duplicate filenames. Upload each case only once.")
    with TemporaryDirectory(prefix="acv-upload-") as directory:
        for upload in uploads:
            name = upload.name
            if (Path(name).name != name or "\\" in name or name.startswith("~$")
                    or Path(name).suffix.lower() != ".xlsx"):
                raise ValueError("Upload original .xlsx cases, not Excel lock files.")
            (Path(directory) / name).write_bytes(upload.getvalue())
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            predictions = create_predictions(directory)
        notices = list(dict.fromkeys(str(w.message) for w in captured))
        for name in sorted(filenames):
            path = Path(directory) / name
            ranking = rank_file(path)
            fields = {"Time"}
            for row in ranking.itertuples():
                names = STANDARD if row.layout == "standard" else RICH
                fields.update(f"Car {row.car} - {field}" for field in names[:2])
            data = pd.read_excel(path, usecols=lambda column: column in fields)
            data["Time"] = pd.to_datetime(data["Time"], errors="raise")
            cases[name] = (ranking, data)
    return predictions, notices, cases


def render_acv():
    st.title("ACV · Cooling inspection")
    st.write("Find which train cars to inspect first using recorded cooling performance.")
    st.caption("Suggested inspection order, not a confirmed leak diagnosis.")
    st.caption("Upload → Summary → Car comparison → Evidence → Download")
    st.subheader("Upload recordings")
    st.write("Choose one or more original Excel case files. Keep their filenames and column headers unchanged.")
    uploads = st.file_uploader("Original Excel case files", type=["xlsx"],
                               accept_multiple_files=True, key="acv_uploads")
    signature = tuple((u.name, sha256(u.getvalue()).hexdigest()) for u in uploads)
    if st.session_state.get("acv_signature") != signature:
        st.session_state.pop("acv_results", None)
        st.session_state.pop("acv_case", None)
        st.session_state.pop("acv_car", None)
        st.session_state.pop("acv_evidence_case", None)
        st.session_state["acv_signature"] = signature
    if uploads:
        st.caption(f"{len(uploads)} file(s) selected. Workbook contents will be checked when you analyse.")
    if st.button("Analyse cars", type="primary", disabled=not uploads):
        st.session_state.pop("acv_results", None)
        try:
            with st.spinner("Comparing cars. Large workbooks may take a few minutes…"):
                st.session_state["acv_results"] = analyse_uploads(uploads)
        except Exception as exc:
            st.error(f"Analysis could not finish: {exc}")
            st.info("Check the workbook format and try again. No partial download was created.")
    if "acv_results" not in st.session_state:
        st.info("Upload recordings, then select Analyse cars.")
        return
    predictions, notices, cases = st.session_state["acv_results"]
    st.divider()
    st.caption(f"Analysis complete · {len(cases)} recording(s)")
    selected = st.selectbox("Recording", list(cases), key="acv_case")
    ranking, data = cases[selected]
    st.subheader("Inspection summary")
    scored = ranking.loc[ranking["evidence"].eq("scored")]
    unavailable = ranking.loc[ranking["evidence"].eq("unavailable"), "car"].tolist()
    best = scored.iloc[0]
    tied = scored.loc[scored["average_positive_gap"].eq(best["average_positive_gap"]), "car"].tolist()
    first, coverage = st.columns(2)
    with first:
        with st.container(border=True):
            st.caption("SUGGESTED FIRST INSPECTION")
            st.subheader(f"Car {best['car']}")
            if len(tied) > 1:
                st.write("Equal top scores: " + ", ".join(f"Car {c}" for c in tied) + ". Car ID determines their order.")
            else:
                st.write("Largest average positive gap above the cooling target.")
            st.caption("An inspection priority, not proof of a refrigerant leak.")
    with coverage:
        with st.container(border=True):
            st.caption("DATA COVERAGE")
            st.subheader(f"{len(scored)} of {len(ranking)} cars scored")
            st.write("Some cars have insufficient data." if unavailable else "Each car has eligible readings.")
            st.caption("Having eligible readings does not guarantee a complete recording.")
    if unavailable:
        st.warning("Insufficient data: " + ", ".join(f"Car {c}" for c in unavailable)
                   + ". These cars still need assessment; they are not confirmed healthy.")
    if ranking["layout"].eq("rich (provisional)").any():
        st.warning("Provisional interpretation: this recording uses an alternative temperature layout with no confirmed information-valid flag.")
    st.caption(f"Recorded period: {data['Time'].min():%d %b %Y, %H:%M:%S} to {data['Time'].max():%d %b %Y, %H:%M:%S}. Time zone is not confirmed.")
    st.subheader("Car comparison")
    st.write("A larger average gap means the car stayed further above its cooling target during eligible readings. Readings at or below target contribute zero.")
    display = pd.DataFrame({
        "Inspection order": ranking["rank"].where(ranking["evidence"].eq("scored")).map(
            lambda value: "Not assessed" if pd.isna(value) else str(int(value))),
        "Car": "Car " + ranking["car"],
        "Average positive gap": ranking["average_positive_gap"].map(
            lambda value: "Unavailable" if pd.isna(value) else f"{value:.4f}"),
        "Usable readings": ranking["usable_rows"],
        "Evidence": ranking["evidence"].map({"scored": "Available", "unavailable": "Insufficient data"}),
    })
    st.dataframe(display, hide_index=True, use_container_width=True)
    st.caption("Scores are recorded temperature gaps, not leak probabilities. Exact ties use car ID. Cars with insufficient data appear last by ID for export completeness; this does not mean they are healthy.")
    st.subheader("Evidence")
    st.write("Choose a car to compare its recorded indoor temperature with its cooling target.")
    if st.session_state.get("acv_evidence_case") != selected:
        st.session_state["acv_car"] = best["car"]
        st.session_state["acv_evidence_case"] = selected
    car = st.selectbox("Car to explore", ranking["car"].tolist(),
                       format_func=lambda value: f"Car {value}", key="acv_car")
    row = ranking.loc[ranking["car"].eq(car)].iloc[0]
    st.caption(f"Car {car} · {int(row['usable_rows']):,} eligible readings used in the score")
    if row["evidence"] == "unavailable":
        st.info("This car cannot be scored from the available readings. Any raw chart below is for context only.")
    names = STANDARD if row["layout"] == "standard" else RICH
    chart = pd.DataFrame({
        "Indoor temperature": pd.to_numeric(data[f"Car {car} - {names[0]}"], errors="raise"),
        "Target (provisional)" if names == RICH else "Cooling control temperature":
            pd.to_numeric(data[f"Car {car} - {names[1]}"], errors="raise"),
    }).replace([np.inf, -np.inf], np.nan)
    chart.index = pd.DatetimeIndex(data["Time"], name="Recorded time")
    if chart.notna().any().any():
        st.line_chart(chart)
        st.caption("Raw temperatures, all operating modes, zeros retained; units unconfirmed. The ranking uses only eligible readings. Lines between recorded points do not establish continuous observations.")
    else:
        st.info("No temperature readings are available for this car.")
    with st.expander("How the ranking works"):
        st.write("Standard layout: valid information, automatic cooling, and finite indoor and control temperatures. Rich layout: full or half cooling with finite cabin and target temperatures; the mapping is provisional with no confirmed validity flag.")
        st.write("The score averages readings, not elapsed time. Pressure, valve states and peer comparisons are not included.")
    if notices:
        with st.expander("Processing notes for all uploaded recordings"):
            for notice in notices:
                st.write(notice)
    st.divider()
    st.subheader("Download results")
    st.write("Export the inspection order for every successfully analysed recording in this batch.")
    st.download_button("Download acv_predictions.csv",
                       data=predictions.to_csv(index=False).encode("utf-8"),
                       file_name="acv_predictions.csv", mime="text/csv")
    st.caption(f"Includes all {len(predictions)} uploaded case(s): file_id and ranked_cars.")


if __name__ == "__main__":
    st.set_page_config(page_title="ACV Cooling Inspection", page_icon="🚆", layout="wide")
    render_acv()

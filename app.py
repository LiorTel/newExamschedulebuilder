from __future__ import annotations

import pandas as pd
import streamlit as st

from classifier import classify_blocks
from extractor import extract_text_from_upload
from merger import build_tables
from normalizer import normalize_blocks
from segmenter import segment_text_to_blocks
from validator import validate_records


st.set_page_config(page_title="Academic Exam Scheduling System – Phase A", layout="wide")

st.title("Academic Exam Scheduling System – Phase A")
st.caption(
    "Upload an academic calendar file. The system will extract the text, split it into structured records, classify academic events and exam constraints, and display the results for review."
)

st.subheader("1. Upload Section")
st.write(
    "Upload the academic calendar file. The system will read the file, extract text, split it into structured blocks, detect dates and time constraints, classify events, and prepare normalized output tables for review."
)

uploaded_file = st.file_uploader("Upload calendar file", type=["txt", "pdf", "docx"])

col1, col2 = st.columns(2)
run_clicked = col1.button("Run Processing", type="primary")
reset_clicked = col2.button("Reset")

if reset_clicked:
    for key in [
        "extraction",
        "blocks_df",
        "classified_df",
        "core_df",
        "constraints_df",
        "validation_df",
    ]:
        st.session_state.pop(key, None)
    st.success("State reset completed.")

if run_clicked:
    if not uploaded_file:
        st.error("Please upload a file first.")
    else:
        extraction = extract_text_from_upload(uploaded_file.name, uploaded_file.getvalue())
        blocks = segment_text_to_blocks(extraction.text)
        parsed_blocks = normalize_blocks(blocks)
        records = classify_blocks(parsed_blocks)
        core_events, constraints = build_tables(records)
        issues = validate_records(records)

        st.session_state["extraction"] = extraction
        st.session_state["blocks_df"] = pd.DataFrame([b.__dict__ for b in parsed_blocks])
        st.session_state["classified_df"] = pd.DataFrame([r.__dict__ for r in records])
        st.session_state["core_df"] = pd.DataFrame(core_events)
        st.session_state["constraints_df"] = pd.DataFrame(constraints)
        st.session_state["validation_df"] = pd.DataFrame([i.__dict__ for i in issues])


st.subheader("3. Raw Text Output")
if "extraction" in st.session_state:
    extraction = st.session_state["extraction"]
    st.text_input("Extraction status", value=extraction.status, disabled=True)
    st.text_area("Extracted text", value=extraction.text, height=240)
else:
    st.info("No extraction result yet.")

st.subheader("4. Parsed Blocks Table")
if "blocks_df" in st.session_state:
    expected_cols = [
        "block_id",
        "section_context",
        "source_text",
        "detected_date_start",
        "detected_date_end",
        "detected_time_start",
        "detected_time_end",
    ]
    st.dataframe(st.session_state["blocks_df"][expected_cols], use_container_width=True)
else:
    st.info("No parsed blocks yet.")

st.subheader("5. Classified Records Table")
if "classified_df" in st.session_state:
    expected_cols = [
        "event_name",
        "event_type",
        "start_date",
        "end_date",
        "exam_policy",
        "allowed_start_time",
        "allowed_end_time",
        "requires_manual_review",
        "classification_reason",
        "source_text",
    ]
    st.dataframe(st.session_state["classified_df"][expected_cols], use_container_width=True)
else:
    st.info("No classified records yet.")

st.subheader("6. Validation / Manual Review Table")
if "validation_df" in st.session_state and not st.session_state["validation_df"].empty:
    st.dataframe(st.session_state["validation_df"], use_container_width=True)
else:
    st.info("No validation issues found or processing not yet run.")

st.divider()
st.subheader("Derived Output Tables")

left, right = st.columns(2)
with left:
    st.markdown("**core_calendar_events**")
    if "core_df" in st.session_state:
        st.dataframe(st.session_state["core_df"], use_container_width=True)

with right:
    st.markdown("**exam_constraints_calendar**")
    if "constraints_df" in st.session_state:
        st.dataframe(st.session_state["constraints_df"], use_container_width=True)

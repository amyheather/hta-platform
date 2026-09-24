# =============================================================================
# NICE HTA PLATFORM
# TA Web Scraper
# =============================================================================

import urllib.parse
from io import BytesIO

import pandas as pd
import streamlit as st

import ta_scraper
from excel_formatter import format_standard_table
from excel_manager import (
    excel_available,
    get_excel_information,
    replace_excel,
    save_excel,
)

# =============================================================================
# Web Scraper UI
# =============================================================================


def show_web_scraper():

    # -------------------------------------------------------------------------
    # Session State
    # -------------------------------------------------------------------------

    if "scraper_result" not in st.session_state:
        st.session_state.scraper_result = None

    if "replace_excel" not in st.session_state:
        st.session_state.replace_excel = False

    # -------------------------------------------------------------------------
    # Header
    # -------------------------------------------------------------------------

    st.header("TA Web Scraper")

    # -------------------------------------------------------------------------
    # Reference Excel
    # -------------------------------------------------------------------------

    st.subheader("Reference Excel")

    if not excel_available():
        uploaded_file = st.file_uploader("Upload Reference Excel", type=["xlsx", "xls"])

        if uploaded_file is not None:
            with st.spinner("Uploading reference Excel..."):
                save_excel(uploaded_file)

            st.rerun()

        return

    # -------------------------------------------------------------------------
    # Existing Excel Information
    # -------------------------------------------------------------------------

    info = get_excel_information()

    filename = info.get("original_filename", "master_reference.xlsx")

    st.info(f"Currently using reference Excel: **{filename}**")

    # if st.button("Replace Reference Excel"):

    # st.session_state.replace_excel = True

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Replace Reference Excel", width="stretch"):
            st.session_state.replace_excel = True

    # with col2:
    # st.link_button(
    # "Open NICE Reference Excel",
    # "https://a.storyblok.com/f/243782/x/04c839059a/ta-recommendations.xlsx",
    # width="stretch"
    # )

    with col2:
        nice_excel_url = (
            "https://a.storyblok.com/f/243782/x/04c839059a/ta-recommendations.xlsx"
        )

        office_viewer_url = (
            "https://view.officeapps.live.com/op/view.aspx?src="
            + urllib.parse.quote(nice_excel_url, safe="")
        )

        st.markdown(
            f"""
            <a href="{office_viewer_url}" target="_blank">
                <button style="
                    width: 100%;
                    padding: 0.5rem;
                    border-radius: 0.5rem;
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    background-color: white;
                    cursor: pointer;
                    font-size: 1rem;
                ">
                    Open NICE Reference Excel
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.replace_excel:
        uploaded_file = st.file_uploader(
            "Select New Excel", type=["xlsx", "xls"], key="replace_reference_excel"
        )

        if uploaded_file is not None:
            with st.spinner("Replacing reference Excel..."):
                replace_excel(uploaded_file)

            st.session_state.replace_excel = False

            st.rerun()

    # -------------------------------------------------------------------------
    # TA Input
    # -------------------------------------------------------------------------

    st.subheader("Enter TA Number / NICE URL")

    ta_value = st.text_input(
        "",
        placeholder="Example: TA970 or https://www.nice.org.uk/guidance/ta970",
        label_visibility="collapsed",
    )

    retrieve = st.button("Retrieve TA Information", type="primary")

    if retrieve:
        if not ta_value.strip():
            st.warning("Please enter a TA Number or NICE URL.")

            return

        with st.spinner("Retrieving information from NICE..."):
            try:
                result, multiple_rows = ta_scraper.scrape_ta_page(ta_value.strip())

                st.session_state.scraper_result = result

            except Exception as error:
                st.error(str(error))

                return

    # -------------------------------------------------------------------------
    # Results
    # -------------------------------------------------------------------------

    if st.session_state.scraper_result is None:
        return

    result = st.session_state.scraper_result

    # -------------------------------------------------------------------------
    # Results Preview
    # -------------------------------------------------------------------------

    st.subheader("Results")

    st.dataframe(result, hide_index=True, width="stretch")

    # -------------------------------------------------------------------------
    # Download Options
    # -------------------------------------------------------------------------

    download_col1, download_col2 = st.columns(2)

    # -------------------------------------------------------------------------
    # CSV Download
    # -------------------------------------------------------------------------

    with download_col1:
        csv = result.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="TA_Web_Scraper_Output.csv",
            mime="text/csv",
            width="stretch",
        )

    # -------------------------------------------------------------------------
    # Excel Download
    # -------------------------------------------------------------------------

    with download_col2:
        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            result.to_excel(writer, index=False, sheet_name="TA Output")

            worksheet = writer.sheets["TA Output"]

            format_standard_table(worksheet)

        output.seek(0)

        # ---------------------------------------------------------
        # Excel File Name
        # ---------------------------------------------------------

        ta_number = result.loc[result["Field"] == "TA Number", "Result"].iloc[0]

        ta_number = str(ta_number).strip().upper()

        # Convert TA214 → TA_214
        excel_filename = ta_number.replace("TA", "TA_") + ".xlsx"

        st.download_button(
            label="Download Excel",
            data=output.getvalue(),
            file_name=excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )

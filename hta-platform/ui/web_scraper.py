# =============================================================================
# NICE HTA PLATFORM
# TA Web Scraper
# =============================================================================

from io import BytesIO

import pandas as pd
import streamlit as st

import ta_scraper

from excel_manager import (
    excel_available,
    save_excel,
    replace_excel,
    get_excel_information
)


from excel_formatter import format_standard_table


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

        uploaded_file = st.file_uploader(
            "Upload Reference Excel",
            type=["xlsx", "xls"]
        )

        if uploaded_file is not None:

            with st.spinner("Uploading reference Excel..."):

                save_excel(uploaded_file)

            st.rerun()

        return

    # -------------------------------------------------------------------------
    # Existing Excel Information
    # -------------------------------------------------------------------------

    info = get_excel_information()

    filename = info.get(
        "original_filename",
        "master_reference.xlsx"
    )

    st.info(
        f"Currently using reference Excel: **{filename}**"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Replace Reference Excel",
            use_container_width=True
        ):
            st.session_state.replace_excel = True

    

    with col2:

        nice_excel_url = (
            "https://a.storyblok.com/f/243782/x/04c839059a/"
            "ta-recommendations.xlsx"
        )

        st.link_button(
            "Download NICE Reference Excel",
            nice_excel_url,
            use_container_width=True
        )


    if st.session_state.replace_excel:

        uploaded_file = st.file_uploader(
            "Select New Excel",
            type=["xlsx", "xls"],
            key="replace_reference_excel"
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
        label_visibility="collapsed"
    )

    retrieve = st.button(
        "Retrieve TA Information",
        type="primary"
    )

    if retrieve:

        if not ta_value.strip():

            st.warning(
                "Please enter a TA Number or NICE URL."
            )

            return

        with st.spinner("Retrieving information from NICE..."):

            try:

                result, multiple_rows = (
                    ta_scraper.scrape_ta_page(
                        ta_value.strip()
                    )
                )

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

    st.dataframe(
        result,
        hide_index=True,
        use_container_width=True
    )

    # -------------------------------------------------------------------------
    # Download Options
    # -------------------------------------------------------------------------

    download_col1, download_col2 = st.columns(2)

    # -------------------------------------------------------------------------
    # CSV Download
    # -------------------------------------------------------------------------

    with download_col1:

        csv = result.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="TA_Web_Scraper_Output.csv",
            mime="text/csv",
            use_container_width=True
        )

    # -------------------------------------------------------------------------
    # Excel Download
    # -------------------------------------------------------------------------

    with download_col2:

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            result.to_excel(
                writer,
                index=False,
                sheet_name="TA Output"
            )

            worksheet = writer.sheets["TA Output"]

            format_standard_table(worksheet)

        output.seek(0)


# ---------------------------------------------------------
# Excel File Name
# ---------------------------------------------------------

        ta_number = result.loc[
            result["Field"] == "TA Number",
            "Result"
        ].iloc[0]

        ta_number = str(ta_number).strip().upper()

        # Convert TA214 → TA_214
        excel_filename = ta_number.replace("TA", "TA_") + ".xlsx"

        st.download_button(
            label="Download Excel",
            data=output.getvalue(),
            file_name=excel_filename,
            mime=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
            use_container_width=True
        )

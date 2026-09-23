# =============================================================================
# Document Repository & Table Extraction
# =============================================================================

import streamlit as st
import pandas as pd
import ta_scraper
from io import BytesIO

import table_repository
from pathlib import Path
import base64
from excel_formatter import (
    format_single_table_excel,
    format_repository_excel,
)

# =============================================================================
# Main UI
# =============================================================================


def show_table_extraction():
    """
    Document Repository & Table Extraction
    """

    st.header("📊 Document Repository & Table Extraction")

    st.markdown("""
Discover NICE documents, download PDF files,
extract tables and browse the extracted table repository.
""")

    st.divider()

    # -------------------------------------------------------------------------
    # Session State
    # -------------------------------------------------------------------------

    if "nice_url" not in st.session_state:

        st.session_state.nice_url = "TA970"

    if "available_documents" not in st.session_state:

        st.session_state.available_documents = None

    if "repository" not in st.session_state:

        st.session_state.repository = None

    if "selected_document" not in st.session_state:

        st.session_state.selected_document = None

    if "downloaded_document" not in st.session_state:

        st.session_state.downloaded_document = None

    if "tables" not in st.session_state:

        st.session_state.tables = None

    # =========================================================================
    # STEP 1
    # Document Discovery
    # =========================================================================

    st.subheader("Discover NICE Documents")

    nice_url = st.text_input(
        "NICE Technology Appraisal",
        value=st.session_state.nice_url,
        placeholder="TA970 or https://www.nice.org.uk/guidance/TA970",
        key="table_extraction_ta",
    )

    if st.button(
        "Discover Documents", type="primary", use_container_width=True
    ):

        if not nice_url.strip():

            st.warning(
                "Please enter a NICE Technology Appraisal Number or URL."
            )

            return

        with st.spinner("Discovering NICE documents..."):

            try:

                documents = table_repository.discover_documents(
                    ta_scraper.normalize_ta_input(nice_url)
                )

            except Exception as error:

                st.error(error)

                return

        if documents.empty:

            st.warning("No downloadable documents were found.")

            return

        st.session_state.nice_url = nice_url

        st.session_state.available_documents = documents

        st.success(f"{len(documents)} document(s) discovered successfully.")

    # =========================================================================
    # STEP 2
    # Select Documents
    # =========================================================================

    if st.session_state.available_documents is None:

        return

    st.divider()

    st.subheader("Select Documents")

    documents = st.session_state.available_documents.copy()

    documents.insert(0, "Select", False)

    edited_documents = st.data_editor(
        documents,
        column_order=[
            "Select",
            "TA Number",
            "Document ID",
            "Document Name",
            "File Type",
            "Download Status",
        ],
        hide_index=True,
        use_container_width=True,
        disabled=[
            column for column in documents.columns if column != "Select"
        ],
    )

    if st.button(
        "Download Selected Documents", type="primary", use_container_width=True
    ):

        selected_documents = edited_documents.loc[
            edited_documents["Select"]
        ].drop(columns="Select")

        if selected_documents.empty:

            st.warning("Please select at least one document.")

            return

        with st.spinner("Downloading selected documents..."):

            try:

                downloaded = table_repository.download_selected_documents(
                    selected_documents
                )

                repository_df = table_repository.update_repository(downloaded)

                # ---------------------------------------------------
                # Refresh Available Documents
                # ---------------------------------------------------

                st.session_state.available_documents = (
                    table_repository.update_download_status(
                        st.session_state.available_documents
                    )
                )

            except Exception as error:

                st.error(error)

                return

        # -----------------------------------------------------------------
        # Already Downloaded Message
        # -----------------------------------------------------------------

        st.session_state.repository = repository_df

        new_downloads = downloaded.attrs.get("new_downloads", 0)

        already_downloaded = downloaded.attrs.get("already_downloaded", 0)

        if new_downloads:

            st.success(
                f"✅ {new_downloads} document(s) downloaded successfully."
            )

        if already_downloaded:

            st.info(
                f"ℹ {already_downloaded} document(s) were already "
                "available in your repository."
            )

        if len(downloaded):

            st.session_state.downloaded_document = downloaded.iloc[0]

    # ---------------------------------------------------------------------
    # Selected Document
    # ---------------------------------------------------------------------

    if st.session_state.downloaded_document is not None:

        st.divider()

        st.subheader("Selected Document")

        document = st.session_state.downloaded_document

        pdf_path = Path(document["Local File"])

        st.success(f"✔ {document['Document Name']} is now available.")

        col1, col2 = st.columns(2)

        # -------------------------------------------------------------
        # Document PREVIEW and DOWNLOAD
        # -------------------------------------------------------------
        with col1:

            if st.button("👁 Preview PDF", use_container_width=True):

                st.session_state.preview_pdf = str(pdf_path)
        # -------------------------------------------------------------
        # Download
        # -------------------------------------------------------------

        with col2:

            with open(pdf_path, "rb") as pdf_file:

                st.download_button(
                    "⬇ Download PDF",
                    data=pdf_file,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    use_container_width=True,
                )

        # -------------------------------------------------------------
        # PDF Preview
        # -------------------------------------------------------------

        if (
            st.session_state.get("preview_pdf") == str(pdf_path)
            and pdf_path.exists()
        ):

            pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)

            if pdf_size_mb <= 10:

                with open(pdf_path, "rb") as pdf_file:

                    base64_pdf = base64.b64encode(pdf_file.read()).decode(
                        "utf-8"
                    )

                pdf_display = f"""
                <iframe
                    src="data:application/pdf;base64,{base64_pdf}"
                    width="100%"
                    height="800"
                    type="application/pdf">
                </iframe>
                """

                st.markdown(pdf_display, unsafe_allow_html=True)

            else:

                st.warning(
                    "This document is larger than 10 MB and cannot "
                    "be previewed. Please download the PDF."
                )

    # =========================================================================
    # STEP 5
    # Table Extraction
    # =========================================================================

    st.divider()

    st.subheader("Table Extraction")

    if st.session_state.downloaded_document is None:

        st.info("Please download a document before extracting tables.")

        return

    st.markdown("### Page Range")

    col1, col2 = st.columns(2)

    with col1:

        page_from = st.number_input(
            "From", min_value=1, value=1, step=1, key="table_page_from"
        )

    with col2:

        page_to = st.number_input(
            "To", min_value=1, value=20, step=1, key="table_page_to"
        )

    st.write("")

    if st.button(
        "Extract Tables",
        type="primary",
        use_container_width=True,
    ):

        with st.spinner("Extracting tables from the selected PDF..."):

            try:

                tables = table_repository.extract_tables(
                    st.session_state.downloaded_document,
                    page_from=page_from,
                    page_to=page_to,
                    export=True,
                )

            except Exception as error:

                st.error(error)

                return

        if not tables:

            st.warning("No tables were detected in the selected document.")

            return

        st.session_state.tables = tables

        st.success(f"{len(tables)} table(s) extracted successfully.")

    # ========================================================================
    # STEP 6
    # Table Repository
    # =========================================================================

    if st.session_state.tables is None:

        return

    tables = st.session_state.tables

    st.divider()

    st.subheader("Table Repository")

    # -------------------------------------------------------------------------
    # Repository Summary
    # -------------------------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric("Extracted Tables", len(tables))

    with col2:

        merged_pages = sum(len(table["Merged Pages"]) for table in tables)

        st.metric("Merged Pages", merged_pages)

    with col3:

        total_rows = sum(table["Rows"] for table in tables)

        st.metric("Total Rows", total_rows)

    # -------------------------------------------------------------------------
    # Table Selection
    # -------------------------------------------------------------------------

    table_labels = []

    for i, table in enumerate(tables):

        if table["Table Number"]:

            label = f"{table['Table Number']} " f"(Page {table['Start Page']})"

        else:

            label = f"Table {i+1} " f"(Page {table['Start Page']})"

        table_labels.append(label)

    selected = st.selectbox(
        "Select Table",
        range(len(tables)),
        format_func=lambda x: table_labels[x],
        key="table_selector",
    )

    table = tables[selected]

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------

    st.divider()

    st.subheader("Table Metadata")

    metadata = {
        "Table Number": (
            table["Table Number"] if table["Table Number"] else "Not Available"
        ),
        "Table Name": (
            table["Table Name"] if table["Table Name"] else "Not Available"
        ),
        "Start Page": table["Start Page"],
        "End Page": table["End Page"],
        "Merged Pages": ", ".join(map(str, table["Merged Pages"])),
        "Rows": table["Rows"],
        "Columns": table["Columns"],
    }

    metadata_df = pd.DataFrame(metadata.items(), columns=["Field", "Value"])

    st.dataframe(metadata_df, hide_index=True, use_container_width=True)

    # -------------------------------------------------------------------------
    # Table Preview
    # -------------------------------------------------------------------------

    st.divider()

    st.subheader("Table Preview")

    st.dataframe(table["DataFrame"], hide_index=True, use_container_width=True)

    # -------------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------------

    st.divider()
    st.subheader("Download Table")

    col1, col2, col3 = st.columns(3)

    # ----------------------------
    # CSV
    # ----------------------------

    csv = table["DataFrame"].to_csv(index=False).encode("utf-8")

    filename = (
        table["Table Number"]
        if table["Table Number"]
        else f"Table_{selected+1}"
    )

    filename = filename.replace(" ", "_").replace("/", "_").replace(":", "")

    with col1:
        st.download_button(
            "⬇ Download CSV",
            data=csv,
            file_name=f"{filename}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ----------------------------
    # Current Table Excel
    # ----------------------------

    excel_buffer = BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:

        metadata = pd.DataFrame(
            [
                [
                    "PDF File Name",
                    Path(
                        st.session_state.downloaded_document["Local File"]
                    ).name,
                ],
                ["Table Number", table["Table Number"] or "Not Available"],
                ["Table Name", table["Table Name"] or "Not Available"],
                ["Start Page", table["Start Page"]],
                ["End Page", table["End Page"]],
                ["Rows", table["Rows"]],
                ["Columns", table["Columns"]],
            ],
            columns=["Field", "Value"],
        )

        metadata.to_excel(
            writer,
            sheet_name="Extracted Table",
            index=False,
            startrow=0,
        )

        table["DataFrame"].to_excel(
            writer,
            sheet_name="Extracted Table",
            index=False,
            startrow=len(metadata) + 3,
        )

        worksheet = writer.sheets["Extracted Table"]

        format_single_table_excel(
            worksheet,
            len(metadata),
        )

    excel_buffer.seek(0)

    with col2:
        st.download_button(
            "⬇ Download Excel",
            data=excel_buffer.getvalue(),
            file_name=f"{filename}.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

    # ----------------------------
    # ALL TABLES Excel
    # ----------------------------

    all_tables_buffer = BytesIO()

    with pd.ExcelWriter(all_tables_buffer, engine="openpyxl") as writer:

        summary = []

        for i, tbl in enumerate(tables, start=1):

            summary.append(
                {
                    "Table No.": tbl["Table Number"] or f"Table {i}",
                    "Table Name": tbl["Table Name"] or "Not Available",
                    "Page": tbl["Start Page"],
                    "Rows": tbl["Rows"],
                    "Columns": tbl["Columns"],
                }
            )

        pd.DataFrame(summary).to_excel(
            writer,
            sheet_name="Summary",
            index=False,
        )

        summary_ws = writer.sheets["Summary"]

        format_repository_excel(summary_ws)

        for i, tbl in enumerate(tables, start=1):

            sheet_name = (
                f"{tbl['Table Number']} {tbl['Table Name']}"
                if tbl["Table Number"]
                else f"Table {i}"
            )

            for ch in ["\\", "/", ":", "*", "?", "[", "]"]:
                sheet_name = sheet_name.replace(ch, "-")

            sheet_name = sheet_name[:31]

            tbl["DataFrame"].to_excel(
                writer, sheet_name=sheet_name, index=False, startrow=0
            )

            worksheet = writer.sheets[sheet_name]

            try:

                format_repository_excel(worksheet)

            except Exception as e:

                st.error(f"Formatting failed for sheet '{sheet_name}': {e}")

    all_tables_buffer.seek(0)

    with col3:
        st.download_button(
            "⬇ Download All",
            data=all_tables_buffer.getvalue(),
            file_name=f"{table['Document ID']}_Extracted_Tables.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

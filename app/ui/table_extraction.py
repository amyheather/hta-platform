# =============================================================================
# Table Extraction
# =============================================================================

import base64
from io import BytesIO
from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

import table_repository
from excel_formatter import (
    format_repository_excel,
    format_single_table_excel,
)

# =============================================================================
# Main UI
# =============================================================================


def show_table_extraction():
    """
    Document Repository & Table Extraction
    """
    st.header("📊 Table Extractor")

    st.markdown(
        """
        Upload a PDF file, choose the page range, and extract tables.
        """
    )

    # =========================================================================
    # Upload PDF
    # =========================================================================

    uploaded_pdf = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        accept_multiple_files=False,
        key="table_extractor_pdf_upload",
    )

    if uploaded_pdf is None:
        st.info("Upload a PDF file to begin extracting tables.")
        return

    # Clear previously extracted tables if the user uploads another PDF.
    if st.session_state.get("table_extractor_source_name") != uploaded_pdf.name:
        st.session_state.tables = None
        st.session_state.table_extractor_source_name = uploaded_pdf.name

    st.success(f"✔ Uploaded: {uploaded_pdf.name}")

    st.divider()

    # =========================================================================
    # Preview PDF
    # =========================================================================

    if st.button("👁 Preview PDF", width="stretch"):
        base64_pdf = base64.b64encode(uploaded_pdf.read()).decode("utf-8")
        pdf_display = f"""
        <iframe
            src="data:application/pdf;base64,{base64_pdf}"
            width="100%"
            height="800"
            type="application/pdf">
        </iframe>
        """
        st.markdown(pdf_display, unsafe_allow_html=True)

    st.divider()

    # =========================================================================
    # Page range
    # =========================================================================

    st.subheader("Page Range")

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

    # =========================================================================
    # Table extraction
    # =========================================================================

    if st.button(
        "Extract Tables",
        type="primary",
        width="stretch",
    ):
        with st.spinner("Extracting tables from the selected PDF..."):
            try:
                # extract_tables previously received a repository document with a
                # Local File path. Preserve that existing interface by creating a
                # temporary PDF and a minimal equivalent document record.
                with tempfile.TemporaryDirectory() as temporary_directory:
                    pdf_path = Path(temporary_directory) / uploaded_pdf.name
                    pdf_path.write_bytes(uploaded_pdf.getvalue())

                    document = {
                        "Local File": str(pdf_path),
                        "Document ID": pdf_path.stem,
                        "Document Name": uploaded_pdf.name,
                    }

                    tables = table_repository.extract_tables(
                        document,
                        page_from=page_from,
                        page_to=page_to,
                        export=False,
                    )

            except Exception as error:
                st.error(error)
                return

        if not tables:
            st.warning("No tables were detected in the selected document.")
            return

        st.session_state.tables = tables

        st.success(f"{len(tables)} table(s) extracted successfully.")

    # =========================================================================
    # Table repository
    # =========================================================================

    tables = st.session_state.get("tables")

    if not tables:
        return

    st.divider()
    st.subheader("Table Repository")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Extracted Tables", len(tables))

    with col2:
        merged_pages = sum(len(table["Merged Pages"]) for table in tables)

        st.metric("Merged Pages", merged_pages)

    with col3:
        total_rows = sum(table["Rows"] for table in tables)

        st.metric("Total Rows", total_rows)

    # =========================================================================
    # Table Selection
    # =========================================================================

    table_labels = []

    for i, table in enumerate(tables):
        if table["Table Number"]:
            label = f"{table['Table Number']} (Page {table['Start Page']})"

        else:
            label = f"Table {i + 1} (Page {table['Start Page']})"

        table_labels.append(label)

    selected = st.selectbox(
        "Select Table",
        range(len(tables)),
        format_func=lambda x: table_labels[x],
        key="table_selector",
    )

    table = tables[selected]

    # =========================================================================
    # Metadata
    # =========================================================================

    st.divider()

    st.subheader("Table Metadata")

    metadata = {
        "Table Number": (
            table["Table Number"] if table["Table Number"] else "Not Available"
        ),
        "Table Name": (table["Table Name"] if table["Table Name"] else "Not Available"),
        "Start Page": table["Start Page"],
        "End Page": table["End Page"],
        "Merged Pages": ", ".join(map(str, table["Merged Pages"])),
        "Rows": table["Rows"],
        "Columns": table["Columns"],
    }

    metadata_df = pd.DataFrame(metadata.items(), columns=["Field", "Value"])

    st.dataframe(metadata_df, hide_index=True, width="stretch")

    # =========================================================================
    # Table preview
    # =========================================================================

    st.divider()

    st.subheader("Table Preview")

    st.dataframe(table["DataFrame"], hide_index=True, width="stretch")

    # =========================================================================
    # Downloads
    # =========================================================================

    st.divider()
    st.subheader("Download Table")

    col1, col2, col3 = st.columns(3)

    # ----------------------------
    # CSV
    # ----------------------------

    csv = table["DataFrame"].to_csv(index=False).encode("utf-8")

    filename = (
        table["Table Number"] if table["Table Number"] else f"Table_{selected + 1}"
    )

    filename = filename.replace(" ", "_").replace("/", "_").replace(":", "")

    with col1:
        st.download_button(
            "⬇ Download CSV",
            data=csv,
            file_name=f"{filename}.csv",
            mime="text/csv",
            width="stretch"
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
                    Path(st.session_state.downloaded_document["Local File"]).name,
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
            mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            width="stretch"
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
            "⬇ Download All to Excel",
            data=all_tables_buffer.getvalue(),
            file_name=f"{table['Document ID']}_Extracted_Tables.xlsx",
            mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            width="stretch"
        )

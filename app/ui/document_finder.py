# =============================================================================
# Document Finder
# =============================================================================


import streamlit as st

import ta_scraper
import table_repository


def show_document_finder():
    """
    Discover NICE documents and allow the user to download selected PDFs.
    """

    st.header("📄 Document Finder")

    st.markdown(
        """
        Discover downloadable NICE documents, select one or more files,
        and download them to a location of your choice.
        """
    )

    # =========================================================================
    # Session State
    # =========================================================================

    if "nice_url" not in st.session_state:
        st.session_state.nice_url = "TA970"

    if "available_documents" not in st.session_state:
        st.session_state.available_documents = None

    if "download_data" not in st.session_state:
        st.session_state.download_data = None

    if "download_filename" not in st.session_state:
        st.session_state.download_filename = None

    if "download_mime" not in st.session_state:
        st.session_state.download_mime = None

    if "download_label" not in st.session_state:
        st.session_state.download_label = None

    if "download_success_message" not in st.session_state:
        st.session_state.download_success_message = None

    # =========================================================================
    # Document discovery
    # =========================================================================

    nice_url = st.text_input(
        "NICE Technology Appraisal",
        value=st.session_state.nice_url,
        placeholder="TA970 or https://www.nice.org.uk/guidance/TA970",
        key="table_extraction_ta",
    )

    if st.button("Discover Documents", type="primary", width="stretch"):
        if not nice_url.strip():
            st.warning("Please enter a NICE Technology Appraisal Number or URL.")

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
        st.session_state.download_data = None
        st.session_state.download_filename = None
        st.session_state.download_mime = None
        st.session_state.download_label = None
        st.session_state.download_success_message = None

        st.success(f"{len(documents)} document(s) discovered successfully.")

    if st.session_state.available_documents is None:
        return

    # =========================================================================
    # Select documents
    # =========================================================================

    st.divider()

    st.subheader("Select Documents")

    st.markdown("""
A single selected document downloads directly. If multiple documents are
selected, they are downloaded as a ZIP file so they can be delivered together.
""")

    select_all = st.checkbox(
        "Select all documents",
        key="document_finder_select_all",
    )
    documents = st.session_state.available_documents.copy()

    documents.insert(0, "Select", select_all)

    edited_documents = st.data_editor(
        documents,
        column_order=[
            "Select",
            "TA Number",
            "Document ID",
            "Document Name",
            "File Type",
        ],
        hide_index=True,
        width="stretch",
        disabled=[column for column in documents.columns if column != "Select"],
        key=f"document_finder_editor_{select_all}"
    )

    if st.button(
        "Prepare selected documents for download",
        type="primary",
        width="stretch",
    ):
        selected_documents = edited_documents.loc[edited_documents["Select"]].drop(
            columns="Select"
        )

        if selected_documents.empty:
            st.warning("Please select at least one document.")
            return

        with st.spinner("Preparing download..."):
            try:
                if len(selected_documents) == 1:
                    document = selected_documents.iloc[0]

                    file_bytes, filename, mime_type = (
                        table_repository.get_download_file(document)
                    )

                    st.session_state.download_data = file_bytes
                    st.session_state.download_filename = filename
                    st.session_state.download_mime = mime_type
                    st.session_state.download_label = "Download document"
                    st.session_state.download_success_message = (
                        "1 document ready to download."
                    )

                else:
                    zip_bytes = table_repository.create_download_zip(
                        selected_documents
                    )

                    ta_number = selected_documents.iloc[0]["TA Number"]

                    st.session_state.download_data = zip_bytes
                    st.session_state.download_filename = f"{ta_number}_documents.zip"
                    st.session_state.download_mime = "application/zip"
                    st.session_state.download_label = "Download documents"
                    st.session_state.download_success_message = (
                        f"{len(selected_documents)} documents ready to download "
                        "as a ZIP file."
                    )

            except Exception as error:
                st.error(f"Could not prepare download: {error}")
                return

    if st.session_state.download_success_message:
        st.success(st.session_state.download_success_message)

    if st.session_state.download_data is not None:
        st.download_button(
            label=st.session_state.download_label,
            data=st.session_state.download_data,
            file_name=st.session_state.download_filename,
            mime=st.session_state.download_mime,
            type="primary",
            width="stretch",
        )

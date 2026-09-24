# =============================================================================
# Document Finder
# =============================================================================

from pathlib import Path

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

        st.success(f"{len(documents)} document(s) discovered successfully.")

    if st.session_state.available_documents is None:
        return

    # =========================================================================
    # Select documents
    # =========================================================================

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
        width="stretch",
        disabled=[column for column in documents.columns if column != "Select"],
    )

    if st.button(
        "Download Selected Documents", type="primary", width="stretch"
    ):
        selected_documents = edited_documents.loc[edited_documents["Select"]].drop(
            columns="Select"
        )

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
            st.success(f"✅ {new_downloads} document(s) downloaded successfully.")

        if already_downloaded:
            st.info(
                f"ℹ {already_downloaded} document(s) were already "
                "available in your repository."
            )

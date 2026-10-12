# =============================================================================
# NICE HTA INFORMATION EXTRACTION PLATFORM
# Main Streamlit Application
# =============================================================================

import streamlit as st

from ui.document_finder import show_document_finder
from ui.rag import show_rag
from ui.table_extraction import show_table_extraction
from ui.web_scraper import show_web_scraper

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="NICE HTA Information Extraction Platform",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# Session State
# =============================================================================

DEFAULT_SESSION_STATE = {
    "repository": None,
    "available_documents": None,
    "selected_document": None,
    "tables": None,
    "nice_url": "TA970",
}

for key, value in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =============================================================================
# Page
# =============================================================================

st.title("NICE HTA Information Extraction Platform")


st.markdown("""
This application supports the structured extraction of information from
**NICE Health Technology Assessment (HTA)** guidance and associated
documents.

It was developed by **Shantanu Fulaware** in their dissertation project for
their MSc Health Data Science degree at the University of Exeter. It was
developed with support from **Dawn Lee** and **Saul Stevens** in the Peninsula
Technology Assessment Group (PenTAG) and **Thomas Monks** in the Peninsula
Collaboration for Health Operational Research and Development group (PenCHORD).

Some amendments have been made by **Amy Heather** to support deployment on
Streamlit Community Cloud, so the PenTAG team are able to run the app from
the browser.

**App features:**

- **🌐 Web Scraper:** Retrieve and explore content from NICE technology
  appraisal webpages.
- **📄 Document Finder:** Download, organise, and review relevant appraisal
  documents.
- **📊 Table Extractor:** Extract tables from PDF documents for further
  analysis.
- **🤖 AI Prompt Template:** Get a prompt to use with an AI tool of your
  choice.""")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🌐 Web Scraper",
        "📄 Document Finder",
        "📊 Table Extractor",
        "🤖 AI Prompt Template"
    ]
)
with tab1:
    show_web_scraper()
with tab2:
    show_document_finder()
with tab3:
    show_table_extraction()
with tab4:
    show_rag()

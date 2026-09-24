# =============================================================================
# NICE HTA INFORMATION EXTRACTION PLATFORM
# Main Streamlit Application
# =============================================================================

import streamlit as st
from ui.table_extraction import show_table_extraction
from ui.web_scraper import show_web_scraper

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="NICE HTA INFORMATION EXTRACTION PLATFORM",
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

st.divider()

tab1, tab2 = st.tabs(
    [
        "🌐 Web Scraper",
        "📊 Document Repository & Table Extraction",
    ]
)
with tab1:
    show_web_scraper()
with tab2:
    show_table_extraction()

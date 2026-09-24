# =============================================================================
# NICE HTA INFORMATION EXTRACTION PLATFORM
# Main Streamlit Application
# =============================================================================

import streamlit as st
from ui.rag_panel import show_rag_panel
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
    "rag_ready": False,
    "rag_result": None,
    "rag_document": None,
    "nice_url": "TA970",
}

for key, value in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =============================================================================
# Title
# =============================================================================

st.title("NICE HTA INFORMATION EXTRACTION PLATFORM")

st.divider()


# =============================================================================
# Tabs
# =============================================================================

tab1, tab2, tab3 = st.tabs(
    [
        "🌐 Web Scraper",
        "📊 Document Repository & Table Extraction",
        "🤖 RAG Question Answering",
    ]
)


# =============================================================================
# Tab 1
# =============================================================================

with tab1:
    show_web_scraper()


# =============================================================================
# Tab 2
# =============================================================================

with tab2:
    show_table_extraction()


# =============================================================================
# Tab 3
# =============================================================================

with tab3:
    show_rag_panel()

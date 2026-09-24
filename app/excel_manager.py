# =============================================================================
# NICE HTA PLATFORM
# Excel Manager
# =============================================================================

import json
import shutil
import pandas as pd
from pathlib import Path

from paths import EXCEL_CONFIG_FILE, MASTER_EXCEL_FILE

# =============================================================================
# Save Excel
# =============================================================================


def save_excel(uploaded_file):
    """
    Save the reference Excel.

    Supports:
    - Streamlit UploadedFile
    - pathlib.Path
    """

    # ------------------------------------------------------------
    # Local File (Jupyter)
    # ------------------------------------------------------------

    if isinstance(uploaded_file, Path):

        shutil.copy2(uploaded_file, MASTER_EXCEL_FILE)

        original_filename = uploaded_file.name

    # ------------------------------------------------------------
    # Streamlit Upload
    # ------------------------------------------------------------

    else:

        with open(MASTER_EXCEL_FILE, "wb") as file:

            shutil.copyfileobj(uploaded_file, file)

        original_filename = uploaded_file.name

    # ------------------------------------------------------------
    # Save Configuration
    # ------------------------------------------------------------

    config = {
        "configured": True,
        "original_filename": original_filename,
        "excel_path": str(MASTER_EXCEL_FILE),
    }

    with open(EXCEL_CONFIG_FILE, "w") as file:

        json.dump(config, file, indent=4)

    return MASTER_EXCEL_FILE


# =============================================================================
# Replace Excel
# =============================================================================


def replace_excel(uploaded_file):
    """
    Replace the existing master Excel.
    """

    return save_excel(uploaded_file)


# =============================================================================
# Excel Exists?
# =============================================================================


def excel_available():
    """
    Return True if a master Excel exists.
    """

    return MASTER_EXCEL_FILE.exists()


# =============================================================================
# Load Excel Path
# =============================================================================


def load_excel_path():
    """
    Return master Excel path.
    """

    if MASTER_EXCEL_FILE.exists():

        return MASTER_EXCEL_FILE

    return None


# =============================================================================
# Load Excel
# =============================================================================


def load_reference_excel():
    """
    Load master Excel as DataFrame.
    """

    excel_path = load_excel_path()

    if excel_path is None:

        raise FileNotFoundError("Reference Excel has not been uploaded.")

    return pd.read_excel(excel_path)


# =============================================================================
# Excel Information
# =============================================================================


def get_excel_information():
    """
    Return Excel metadata.
    """

    if not EXCEL_CONFIG_FILE.exists():

        return {}

    with open(EXCEL_CONFIG_FILE) as file:

        return json.load(file)


# =============================================================================
# Remove Excel
# =============================================================================


def clear_excel():
    """
    Remove master Excel.
    """

    if MASTER_EXCEL_FILE.exists():

        MASTER_EXCEL_FILE.unlink()

    with open(EXCEL_CONFIG_FILE, "w") as file:

        json.dump({}, file)

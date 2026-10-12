# =============================================================================
# NICE HTA PLATFORM
# Excel Manager
# =============================================================================

from pathlib import Path

import pandas as pd

REFERENCE_EXCEL = (
    Path(__file__).resolve().parent
    / "ta_recommendations.xlsx"
)


def load_reference_excel():
    """Load the reference Excel provided with the app."""

    if not REFERENCE_EXCEL.is_file():
        raise FileNotFoundError(
            "The bundled reference Excel was not found: "
            f"{REFERENCE_EXCEL}"
        )

    return pd.read_excel(REFERENCE_EXCEL)

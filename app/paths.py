# =============================================================================
# NICE HTA PLATFORM
# Project Paths
# =============================================================================

from pathlib import Path

# =============================================================================
# Detect Project Root
# =============================================================================

try:
    PROJECT_ROOT = Path(__file__).resolve().parent

except NameError:
    PROJECT_ROOT = Path.cwd()

    if PROJECT_ROOT.name == "modules":
        PROJECT_ROOT = PROJECT_ROOT.parent

# =============================================================================
# Project Folders
# =============================================================================

CONFIG_FOLDER = PROJECT_ROOT / "config"

DOCUMENT_FOLDER = PROJECT_ROOT / "documents"

TABLE_FOLDER = PROJECT_ROOT / "tables"

VECTORSTORE_FOLDER = PROJECT_ROOT / "vectorstore"

OUTPUT_FOLDER = PROJECT_ROOT / "outputs"

TEMP_FOLDER = PROJECT_ROOT / "temp"

ASSETS_FOLDER = PROJECT_ROOT / "assets"

# =============================================================================
# Files
# =============================================================================

INDEX_FILE = PROJECT_ROOT / "repository_index.csv"

EXCEL_CONFIG_FILE = CONFIG_FOLDER / "excel_config.json"

MASTER_EXCEL_FILE = CONFIG_FOLDER / "master_reference.xlsx"

# =============================================================================
# Create Folders
# =============================================================================

for folder in [
    CONFIG_FOLDER,
    DOCUMENT_FOLDER,
    TABLE_FOLDER,
    VECTORSTORE_FOLDER,
    OUTPUT_FOLDER,
    TEMP_FOLDER,
    ASSETS_FOLDER,
]:
    folder.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Create Excel Config
# =============================================================================

if not EXCEL_CONFIG_FILE.exists():
    EXCEL_CONFIG_FILE.write_text("{}")

# =============================================================================
# NICE HTA PLATFORM
# Repository Manager
# =============================================================================

import logging
import shutil

import pandas as pd

from paths import PROJECT_ROOT, DOCUMENT_FOLDER, INDEX_FILE

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(level=logging.INFO, format="%(levelname)s : %(message)s")

logger = logging.getLogger(__name__)

# =============================================================================
# Load Repository Index
# =============================================================================


def load_repository_index():
    """
    Load the master repository index.

    Creates a new repository index automatically
    if one does not already exist.
    """

    required_columns = [
        "Document ID",
        "TA Number",
        "Document Name",
        "File Type",
        "Document URL",
        "Local File",
        "Download Status",
        "Download Date",
    ]

    # ------------------------------------------------------------
    # Repository does not exist
    # ------------------------------------------------------------

    if not INDEX_FILE.exists():

        logger.info("Repository index not found. Creating new repository.")

        repository = pd.DataFrame(columns=required_columns)

        repository.to_csv(INDEX_FILE, index=False)

        return repository

    # ------------------------------------------------------------
    # Load Repository
    # ------------------------------------------------------------

    repository = pd.read_csv(INDEX_FILE)

    # ------------------------------------------------------------
    # Add Missing Columns
    # ------------------------------------------------------------

    for column in required_columns:

        if column not in repository.columns:

            repository[column] = ""

    repository = repository[required_columns]

    repository.fillna("", inplace=True)

    logger.info(f"{len(repository)} document(s) loaded from repository.")

    return repository


# =============================================================================
# Save Repository Index
# =============================================================================


def save_repository_index(repository):
    """
    Save repository index.
    """

    repository = repository.copy()

    repository.to_csv(INDEX_FILE, index=False)

    logger.info(f"{len(repository)} document(s) saved.")


# =============================================================================
# Update Repository Index
# =============================================================================


def update_repository_index(new_documents):
    """
    Update repository with newly downloaded documents.
    """

    repository = load_repository_index()

    if repository.empty:

        repository = new_documents.copy()

    else:

        repository = pd.concat([repository, new_documents], ignore_index=True)

        repository.drop_duplicates(
            subset="Document URL", keep="last", inplace=True
        )

    repository.reset_index(drop=True, inplace=True)

    save_repository_index(repository)

    return repository


# =============================================================================
# Delete TA Documents
# =============================================================================


def delete_ta_documents(ta_number):
    """
    Delete all downloaded documents for a TA.
    """

    repository = load_repository_index()

    folder = DOCUMENT_FOLDER / ta_number

    if folder.exists():

        shutil.rmtree(folder)

        logger.info(f"Deleted folder : {folder}")

    repository = repository.loc[repository["TA Number"] != ta_number]

    repository.reset_index(drop=True, inplace=True)

    save_repository_index(repository)

    return repository


# =============================================================================
# Downloaded PDFs
# =============================================================================


def get_downloaded_pdfs(repository):
    """
    Return downloaded PDF documents only.
    """

    if repository.empty:

        return repository.copy()

    pdfs = repository.copy()

    pdfs = pdfs.loc[pdfs["File Type"].fillna("").str.upper() == "PDF"]

    pdfs = pdfs.loc[
        pdfs["Download Status"]
        .fillna("")
        .isin(["Downloaded", "Already Downloaded"])
    ]

    pdfs.reset_index(drop=True, inplace=True)

    return pdfs


# =============================================================================
# Available TA Numbers
# =============================================================================


def get_available_tas(repository):
    """
    Return available TA numbers.
    """

    pdfs = get_downloaded_pdfs(repository)

    return sorted(pdfs["TA Number"].dropna().unique())


# =============================================================================
# Documents by TA
# =============================================================================


def get_documents_by_ta(repository, ta_number):
    """
    Return documents for one TA.
    """

    docs = get_downloaded_pdfs(repository)

    docs = docs.loc[docs["TA Number"] == ta_number]

    docs = docs.sort_values("Document Name")

    docs.reset_index(drop=True, inplace=True)

    return docs


# =============================================================================
# PDF Path
# =============================================================================


def get_pdf_path(document):
    """
    Return absolute path of the downloaded PDF.
    """

    pdf_path = PROJECT_ROOT / document["Local File"]

    if not pdf_path.exists():

        raise FileNotFoundError(f"PDF not found : {pdf_path}")

    return pdf_path


# =============================================================================
# Repository Summary
# =============================================================================


def repository_summary(repository):
    """
    Return repository statistics.
    """

    pdfs = get_downloaded_pdfs(repository)

    return {
        "Total Documents": len(repository),
        "Downloaded PDFs": len(pdfs),
        "Available TAs": pdfs["TA Number"].nunique(),
    }

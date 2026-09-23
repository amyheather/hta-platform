# =============================================================================
# NICE HTA PLATFORM
# Table Repository
# =============================================================================

import re
import logging
import warnings
import requests
import camelot
import pdfplumber
import json
from bs4 import BeautifulSoup
import pandas as pd

from pathlib import Path
from difflib import SequenceMatcher

from paths import (
    PROJECT_ROOT,
    DOCUMENT_FOLDER,
    TABLE_FOLDER,
    INDEX_FILE,
)

from repository import get_downloaded_pdfs, get_pdf_path

warnings.filterwarnings("ignore", message="Cannot set gray non-stroke color.*")
warnings.filterwarnings("ignore", message=".*does not lie in column range.*")

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = "https://www.nice.org.uk"

REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(level=logging.INFO, format="%(levelname)s : %(message)s")

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", message="Cannot set gray non-stroke color.*")

# =============================================================================
# Helper Functions
# =============================================================================


def validate_url(url):
    """
    Validate NICE Technology Appraisal URL.
    """

    if not isinstance(url, str):

        return False

    pattern = r"^https://www\.nice\.org\.uk/guidance/[A-Za-z0-9]+"

    return re.match(pattern, url) is not None


def build_absolute_url(link):
    """
    Convert relative NICE URL to absolute URL.
    """

    if link.startswith("http"):

        return link

    return BASE_URL + link


def extract_ta_number(url):
    """
    Extract TA number from NICE URL.
    """

    match = re.search(r"/guidance/(ta\d+)", url.lower())

    if match:

        return match.group(1).upper()

    return "UNKNOWN"


def create_empty_dataframe():
    """
    Standard document dataframe.
    """

    return pd.DataFrame(
        columns=[
            "Document ID",
            "TA Number",
            "Document Name",
            "File Type",
            "Document URL",
            "Download Status",
            "Local File",
        ]
    )


# =============================================================================
# Download NICE Page
# =============================================================================


def fetch_page(url):
    """Download and parse a NICE guidance page."""

    if not validate_url(url):

        return None

    try:

        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

        response.raise_for_status()

        return BeautifulSoup(response.text, "html.parser")

    except Exception as error:

        logger.error(error)

        return None


# =============================================================================
# Build NICE URLs
# =============================================================================


def build_document_urls(url):
    """
    Guidance / Resources / History URLs.
    """

    base = url.rstrip("/")

    return {
        "guidance": base,
        "resources": base + "/resources",
        "history": base + "/history",
    }


# =============================================================================
# Module 2
# Discover NICE Documents
# =============================================================================


def fetch_guidance_document(guidance_url):
    """
    Extract the official NICE Guidance PDF.
    """

    soup = fetch_page(guidance_url)

    if soup is None:

        return create_empty_dataframe()

    documents = []

    for link in soup.find_all("a", href=True):

        text = link.get_text(" ", strip=True)

        if "download guidance" not in text.lower():

            continue

        documents.append(
            {
                "Document ID": f"{extract_ta_number(guidance_url)}_DOC001",
                "TA Number": extract_ta_number(guidance_url),
                "Document Name": "Guidance PDF",
                "File Type": "PDF",
                "Document URL": build_absolute_url(link["href"]),
                "Download Status": "Pending",
                "Local File": None,
            }
        )

        break

    return pd.DataFrame(documents)


# =============================================================================
# Repository Status
# =============================================================================


def update_download_status(documents):
    """
    Check repository and update download status.
    """

    repository = load_repository()

    if repository.empty:
        return documents

    downloaded_urls = set(repository["Document URL"])

    downloaded_files = dict(
        zip(repository["Document URL"], repository["Local File"])
    )

    for index in documents.index:

        url = documents.loc[index, "Document URL"]

        if url in downloaded_urls:

            documents.loc[index, "Download Status"] = "Downloaded"

            documents.loc[index, "Local File"] = downloaded_files[url]

        else:

            documents.loc[index, "Download Status"] = "Not Downloaded"

    return documents


# =============================================================================
# History Documents
# =============================================================================


def fetch_history_documents(history_url):
    """
    Extract all downloadable History documents.
    """

    soup = fetch_page(history_url)

    if soup is None:

        return create_empty_dataframe()

    ta = extract_ta_number(history_url)

    documents = []

    counter = 2

    seen = set()

    for link in soup.find_all("a", href=True):

        href = link.get("href", "").strip()

        text = link.get_text(" ", strip=True)

        if "/documents/" not in href:

            continue

        if "(" not in text:

            continue

        document_url = build_absolute_url(href)

        if document_url in seen:

            continue

        seen.add(document_url)

        if "(PDF" in text.upper():

            filetype = "PDF"

        elif "(WORD" in text.upper():

            filetype = "WORD"

        elif "(EXCEL" in text.upper():

            filetype = "EXCEL"

        else:

            filetype = "OTHER"

        document_name = text.split("(")[0].strip()

        lower = document_name.lower()

        if "register of interests" in lower:

            continue

        if lower.startswith("note"):

            continue

        documents.append(
            {
                "Document ID": f"{ta}_DOC{counter:03d}",
                "TA Number": ta,
                "Document Name": document_name,
                "File Type": filetype,
                "Document URL": document_url,
                "Download Status": "Pending",
                "Local File": None,
            }
        )

        counter += 1

    return pd.DataFrame(documents)


# =============================================================================
# Document Discovery
# =============================================================================


def discover_documents(url):
    """
    Return every downloadable NICE document.
    """

    urls = build_document_urls(url)

    guidance = fetch_guidance_document(urls["guidance"])

    history = fetch_history_documents(urls["history"])

    documents = pd.concat([guidance, history], ignore_index=True)

    if documents.empty:

        return documents

    ta = documents.iloc[0]["TA Number"]

    documents["Document ID"] = [
        f"{ta}_DOC{i:03d}" for i in range(1, len(documents) + 1)
    ]

    documents.reset_index(drop=True, inplace=True)

    documents = update_download_status(documents)

    return documents


# =============================================================================
# Module 3
# Document Downloader
# =============================================================================


def safe_filename(document_id, document_name, file_type):
    """
    Create a safe filename for downloaded NICE documents.
    """

    safe_name = re.sub(r'[\\/*?:"<>|]', "", document_name)

    safe_name = safe_name.replace(" ", "_")

    safe_name = re.sub(r"_+", "_", safe_name)

    safe_name = safe_name[:100]

    extension = file_type.lower()

    return f"{document_id}_{safe_name}.{extension}"


# =============================================================================
# Download Single Document
# =============================================================================


def download_document(document):
    """Download a single document from its Document URL."""

    try:

        response = requests.get(
            document["Document URL"],
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            stream=True,
        )

        response.raise_for_status()

    except Exception as error:

        logger.error(error)

        document["Download Status"] = "Failed"

        return document

    ta_folder = DOCUMENT_FOLDER / document["TA Number"]

    ta_folder.mkdir(parents=True, exist_ok=True)

    filename = safe_filename(
        document["Document ID"],
        document["Document Name"],
        document["File Type"],
    )

    filepath = ta_folder / filename

    with open(filepath, "wb") as file:

        for chunk in response.iter_content(chunk_size=8192):

            if chunk:

                file.write(chunk)

    document["Download Status"] = "Downloaded"

    document["Local File"] = str(filepath.relative_to(PROJECT_ROOT))

    logger.info(f"Downloaded : {filename}")

    return document


# =============================================================================
# Download Selected Documents
# =============================================================================


def download_selected_documents(documents):
    """
    Download selected NICE documents.

    Parameters
    ----------
    documents : DataFrame

    Returns
    -------
    DataFrame
    """

    downloaded = []

    new_downloads = 0

    already_downloaded = 0

    for _, row in documents.iterrows():

        # ------------------------------------------------------------
        # Already Downloaded
        # ------------------------------------------------------------

        if row["Download Status"] == "Downloaded":

            already_downloaded += 1

            logger.info(f"{row['Document Name']} already exists.")

            downloaded.append(row.copy())

            continue

        # ------------------------------------------------------------
        # Download New Document
        # ------------------------------------------------------------

        downloaded_document = download_document(row.copy())

        downloaded.append(downloaded_document)

        new_downloads += 1

    repository = pd.DataFrame(downloaded)

    if not repository.empty:

        repository["Download Date"] = pd.Timestamp.now()

    repository.attrs["new_downloads"] = new_downloads
    repository.attrs["already_downloaded"] = already_downloaded

    return repository


# =============================================================================
# Save Repository
# =============================================================================


def save_repository(repository):
    """
    Save repository index.
    """

    repository.to_csv(INDEX_FILE, index=False)

    logger.info(f"Repository saved : {INDEX_FILE}")


# =============================================================================
# Load Repository
# =============================================================================


def load_repository():
    """
    Load repository if available.
    """

    if INDEX_FILE.exists():

        return pd.read_csv(INDEX_FILE)

    return create_empty_dataframe()


# =============================================================================
# Update Repository
# =============================================================================


def update_repository(new_documents):
    """
    Merge new documents into repository.
    """

    repository = load_repository()

    if repository.empty:

        repository = new_documents

    else:

        repository = pd.concat([repository, new_documents], ignore_index=True)

        repository = repository.drop_duplicates(
            subset="Document URL", keep="last"
        )

    save_repository(repository)

    return repository


# =============================================================================
# Module 4.1
# Candidate Table Extraction
# =============================================================================


def extract_candidate_tables(pdf_path, page_from=None, page_to=None):
    """
    Extract candidate tables using Camelot.

    Strategy
    --------
    1. Run Camelot Lattice across the complete PDF.
    2. If no tables are detected, automatically
       fall back to Camelot Stream.

    Returns
    -------
    camelot.core.TableList
    """

    logger.info(f"Scanning PDF : {pdf_path.name}")

    # ------------------------------------------------------------
    # Pages to Process
    # ------------------------------------------------------------

    if page_from is not None and page_to is not None:

        pages = f"{page_from}-{page_to}"

    else:

        pages = "all"

    logger.info(f"Processing Pages : {pages}")

    # ------------------------------------------------------------
    # Try Lattice
    # ------------------------------------------------------------

    try:

        tables = camelot.read_pdf(
            str(pdf_path), flavor="lattice", pages=pages, suppress_stdout=True
        )

        logger.info(f"Lattice tables found: {len(tables)}")

        for i, table in enumerate(tables):

            logger.info("=" * 60)

            logger.info(f"Lattice Table {i+1}")

            logger.info(table.parsing_report)

            logger.info(table.df.head())

            logger.info("=" * 60)

        if len(tables) > 0:

            logger.info(f"Lattice detected {len(tables)} table(s).")

            return tables

    except Exception:

        logger.exception("Lattice extraction failed.")

        raise

    # ------------------------------------------------------------
    # Fallback to Stream
    # ------------------------------------------------------------

    logger.info("No lattice tables detected.")

    logger.info("Switching to Stream extraction...")

    tables = camelot.read_pdf(
        str(pdf_path), flavor="stream", pages=pages, suppress_stdout=True
    )

    # logger.info(

    # f"Stream tables found: {len(tables)}"

    # )

    logger.info(f"Stream tables found: {len(tables)}")

    for i, table in enumerate(tables):

        logger.info("=" * 60)

        logger.info(f"Stream Table {i+1}")

        logger.info(table.parsing_report)

        logger.info(table.df.head())

        logger.info("=" * 60)

    logger.info(f"Stream detected {len(tables)} table(s).")

    return tables


# =============================================================================
# Module 4.2
# Table Caption Extraction
# =============================================================================


def get_text_above_table(pdf, table, margin=60):
    """
    Extract the nearest table caption above a Camelot table.

    Parameters
    ----------
    pdf : pdfplumber.PDF

    table : camelot Table

    margin : int

    Returns
    -------
    str
    """

    page_number = int(table.page)

    x0, y0, x1, y1 = table._bbox

    page = pdf.pages[page_number - 1]

    page_height = page.height

    top = page_height - y1

    crop = page.crop((0, max(0, top - margin), page.width, top))

    text = crop.extract_text()

    if text is None:

        return ""

    lines = []

    for line in text.split("\n"):

        line = line.strip()

        if not line:

            continue

        if re.search(r"Page\s+\d+\s+of\s+\d+", line):

            continue

        if "All rights reserved" in line:

            continue

        if "Company evidence submission" in line:

            continue

        lines.append(line)

    if not lines:

        return ""

    # ------------------------------------------------------------
    # Search from bottom upwards
    # ------------------------------------------------------------

    for i in range(len(lines) - 1, -1, -1):

        if re.match(r"^Table\s+\d+", lines[i], re.IGNORECASE):

            caption = lines[i]

            j = i + 1

            while j < len(lines):

                if re.match(
                    r"^(Table|Figure|Appendix|Section|Chapter)",
                    lines[j],
                    re.IGNORECASE,
                ):

                    break

                caption += " " + lines[j]

                j += 1

            return caption

    return lines[-1]


# =============================================================================
# Module 4.3
# Table Metadata
# =============================================================================


def extract_table_metadata(pdf, table):
    """
    Extract metadata for one Camelot table.

    Parameters
    ----------
    pdf : pdfplumber.PDF

    table : camelot.core.Table

    Returns
    -------
    dict
    """

    caption = get_text_above_table(pdf, table).strip()

    page = int(table.page)

    rows, cols = table.df.shape

    match = re.search(r"(Table\s+\d+[A-Za-z0-9.\-:]*)", caption, re.IGNORECASE)

    if match:

        table_number = match.group(1).strip(" :.-")

        table_name = caption.replace(table_number, "").strip(" :.-")

    else:

        table_number = None

        table_name = caption

    return {
        "PDF Page": page,
        "Table Number": table_number,
        "Table Name": table_name,
        "Rows": rows,
        "Columns": cols,
        "Bounding Box": table._bbox,
    }


# =============================================================================
# Module 4.4
# Repository Table Objects
# =============================================================================


def build_repository_tables(candidate_tables, pdf_path, document_id):
    """
    Convert Camelot tables into repository objects.

    Optimisation
    ------------
    Open the PDF only once and reuse the same
    pdfplumber object for all metadata extraction.
    """

    repository_tables = []

    total = len(candidate_tables)

    logger.info(f"Building repository for {total} table(s).")

    # ------------------------------------------------------------
    # Open PDF only once
    # ------------------------------------------------------------

    with pdfplumber.open(pdf_path) as pdf:

        for i, table in enumerate(candidate_tables):

            logger.info(f"Processing table {i+1}/{total}")

            metadata = extract_table_metadata(pdf, table)

            repository_tables.append(
                {
                    "Document ID": document_id,
                    "PDF Page": metadata["PDF Page"],
                    "Table Number": metadata["Table Number"],
                    "Table Name": metadata["Table Name"],
                    "Rows": metadata["Rows"],
                    "Columns": metadata["Columns"],
                    "Bounding Box": metadata["Bounding Box"],
                    "DataFrame": table.df.copy(),
                    "Start Page": metadata["PDF Page"],
                    "End Page": metadata["PDF Page"],
                    "Merged Pages": [metadata["PDF Page"]],
                }
            )

    logger.info(f"{len(repository_tables)} repository table(s) created.")

    return repository_tables


# =============================================================================
# Module 5.1
# Title Normalisation
# =============================================================================


def normalize_title(text):
    """
    Normalise table titles before comparison.
    """

    if pd.isna(text):

        return ""

    text = str(text).lower()

    text = re.sub(r"\.{2,}", " ", text)

    text = re.sub(r"[:;,\-\(\)\[\]]", " ", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_table_number(text):
    """
    Normalise table numbers before comparison.

    Used only to compare official vs extracted table numbers.
    The original, unnormalised value is still what gets
    displayed in the validation report.
    """

    if pd.isna(text):

        return ""

    text = str(text).lower().strip(" :.-")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =============================================================================
# Module 5.2
# Merge Decision Engine
# =============================================================================


def should_merge(current_table, next_table):
    """
    Decide whether two consecutive tables
    should be merged.
    """

    # ------------------------------------------------------------
    # Rule 1
    # Consecutive pages
    # ------------------------------------------------------------

    if next_table["PDF Page"] != current_table["End Page"] + 1:

        return {
            "merge": False,
            "reason": "Pages are not consecutive",
            "drop_header": False,
        }

    # ------------------------------------------------------------
    # Rule 2
    # New Table Number
    # ------------------------------------------------------------

    if next_table["Table Number"] is not None:

        return {
            "merge": False,
            "reason": "New table number",
            "drop_header": False,
        }

    # ------------------------------------------------------------
    # Rule 3
    # Same number of columns
    # ------------------------------------------------------------

    if current_table["DataFrame"].shape[1] != next_table["DataFrame"].shape[1]:

        return {
            "merge": False,
            "reason": "Column mismatch",
            "drop_header": False,
        }

    # ------------------------------------------------------------
    # Rule 4
    # Compare titles only if both exist
    # ------------------------------------------------------------

    if current_table["Table Name"] and next_table["Table Name"]:

        if normalize_title(current_table["Table Name"]) != normalize_title(
            next_table["Table Name"]
        ):

            return {
                "merge": False,
                "reason": "Title mismatch",
                "drop_header": False,
            }

    # ------------------------------------------------------------
    # Rule 5
    # Duplicate Header
    # ------------------------------------------------------------

    current_header = list(current_table["DataFrame"].iloc[0])

    next_header = list(next_table["DataFrame"].iloc[0])

    return {
        "merge": True,
        "reason": "Continuation",
        "drop_header": current_header == next_header,
    }


# =============================================================================
# Clean Extracted Table
# =============================================================================


def clean_extracted_table(df):
    """
    Clean extracted table before export.

    Only performs lightweight cleaning without
    modifying table structure.
    """

    dataframe = df.copy()

    # ------------------------------------------------------------
    # Trim whitespace
    # ------------------------------------------------------------

    dataframe = dataframe.applymap(
        lambda value: value.strip() if isinstance(value, str) else value
    )

    # ------------------------------------------------------------
    # Remove completely empty rows
    # ------------------------------------------------------------

    dataframe.replace("", pd.NA, inplace=True)

    dataframe.dropna(how="all", inplace=True)

    # ------------------------------------------------------------
    # Remove completely empty columns
    # ------------------------------------------------------------

    dataframe.dropna(axis=1, how="all", inplace=True)

    dataframe.fillna("", inplace=True)

    dataframe.reset_index(drop=True, inplace=True)

    return dataframe


# =============================================================================
# Module 5.3
# Merge Repository Tables
# =============================================================================


def merge_repository_tables(repository_tables):
    """Merge tables that continue across consecutive pages."""

    if not repository_tables:
        return []

    merged = []

    current = repository_tables[0].copy()

    for next_table in repository_tables[1:]:

        print("\n" + "=" * 80)

        print(
            "CURRENT :",
            current["Start Page"],
            "|",
            current["Table Number"],
            "|",
            current["Table Name"],
            "|",
            current["DataFrame"].shape,
        )

        print(
            "NEXT    :",
            next_table["Start Page"],
            "|",
            next_table["Table Number"],
            "|",
            next_table["Table Name"],
            "|",
            next_table["DataFrame"].shape,
        )

        decision = should_merge(current, next_table)

        print("DECISION:", decision)

        # --------------------------------------------------------
        # Merge
        # --------------------------------------------------------

        if decision["merge"]:

            next_df = next_table["DataFrame"].copy()

            if decision["drop_header"]:
                next_df = next_df.iloc[1:].reset_index(drop=True)

            current["DataFrame"] = pd.concat(
                [current["DataFrame"], next_df], ignore_index=True
            )

            current["End Page"] = next_table["PDF Page"]

            current["Merged Pages"].append(next_table["PDF Page"])

        else:

            merged.append(current)

            current = next_table.copy()

    merged.append(current)

    return merged


# =============================================================================
# Module 5.3a
# Extract Table Index
# =============================================================================


def extract_table_index(pdf_path):
    """
    Extract the table index from the document contents.

    Returns
    -------
    pandas.DataFrame
    """

    table_index = []

    pattern = re.compile(
        r"(Table\s+\d+)\s*[:\-]?\s*(.*?)\s+(\d+)$", re.IGNORECASE
    )

    with pdfplumber.open(pdf_path) as pdf:

        # -------------------------------------------------------------
        # Only inspect first 15 pages
        # -------------------------------------------------------------

        for page_number in range(min(15, len(pdf.pages))):

            page = pdf.pages[page_number]

            text = page.extract_text()

            if not text:

                continue

            for line in text.split("\n"):

                match = pattern.search(line.strip())

                if match:

                    table_index.append(
                        {
                            "Table Number": match.group(1),
                            "Table Title": match.group(2),
                            "Expected Page": int(match.group(3)),
                        }
                    )

    return pd.DataFrame(table_index)


# =============================================================================
# Module 12B
# Repository Validation
# =============================================================================


def validate_repository(official_index, merged_tables):
    """Validate extracted tables against the official table index."""

    # -------------------------------------------------------------
    # Convert repository to DataFrame
    # -------------------------------------------------------------

    repository = []

    for table in merged_tables:

        if not table["Table Number"]:
            continue

        repository.append(
            {
                "Table Number": table["Table Number"],
                "Repository Title": table["Table Name"],
                "Repository Page": table["Start Page"],
            }
        )

    repository = pd.DataFrame(repository)

    # -------------------------------------------------------------
    # Normalised Matching Key
    # -------------------------------------------------------------
    # Table numbers are compared using a normalised key so that
    # harmless formatting differences (case, stray punctuation,
    # extra whitespace) don't cause a real match to be missed.
    # The original "Table Number" values below are still what
    # gets displayed in the validation report.

    official_index = official_index.copy()

    official_index["_Number Key"] = official_index["Table Number"].apply(
        normalize_table_number
    )

    if "Table Number" in repository.columns:

        repository["_Number Key"] = repository["Table Number"].apply(
            normalize_table_number
        )

    else:

        repository["_Number Key"] = pd.Series(dtype=str)

    # -------------------------------------------------------------
    # Calculate PDF page offset
    # -------------------------------------------------------------

    common = pd.merge(
        official_index, repository, on="_Number Key", how="inner"
    )

    if len(common):

        page_offset = int(
            (common["Repository Page"] - common["Expected Page"]).mode()[0]
        )

    else:

        page_offset = 0

    logger.info(f"Detected PDF page offset : {page_offset}")

    # -------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------

    results = []

    for _, official in official_index.iterrows():

        result = {
            "Table Number": official["Table Number"],
            "Official Title": official["Table Title"],
            "Expected Page": official["Expected Page"],
        }

        found = repository.loc[
            repository["_Number Key"]
            == normalize_table_number(official["Table Number"])
        ]

        # ---------------------------------------------------------
        # Missing
        # ---------------------------------------------------------

        if found.empty:

            result["Repository Title"] = ""

            result["Repository Page"] = None

            result["Number Match"] = "✗"

            result["Title Match"] = "-"

            result["Page Match"] = "-"

            result["Page Difference"] = None

            result["Confidence"] = 0

            result["Status"] = "MISSING"

            result["Reason"] = "Table not extracted"

            results.append(result)

            continue

        repo = found.iloc[0]

        result["Repository Title"] = repo["Repository Title"]

        result["Repository Page"] = repo["Repository Page"]

        # ---------------------------------------------------------
        # Validation Flags
        # ---------------------------------------------------------

        similarity = SequenceMatcher(
            None,
            normalize_title(official["Table Title"]),
            normalize_title(repo["Repository Title"]),
        ).ratio()

        title_match = similarity >= 0.85

        expected_pdf_page = official["Expected Page"] + page_offset

        page_difference = abs(expected_pdf_page - repo["Repository Page"])

        page_match = page_difference <= 2

        # ---------------------------------------------------------
        # Store validation flags
        # ---------------------------------------------------------

        result["Number Match"] = "✓"

        result["Title Match"] = "✓" if title_match else "✗"

        result["Page Match"] = "✓" if page_match else "✗"

        result["Page Difference"] = page_difference

        # ---------------------------------------------------------
        # Confidence Score
        # ---------------------------------------------------------

        confidence = 40

        if title_match:
            confidence += 40

        if page_match:
            confidence += 20

        result["Confidence"] = confidence

        # ---------------------------------------------------------
        # Validation Status
        # ---------------------------------------------------------

        if title_match and page_match:

            result["Status"] = "PASS"

            result["Reason"] = "Matched"

        elif (not title_match) and page_match:

            result["Status"] = "MISMATCH"

            result["Reason"] = "Title mismatch"

        elif title_match and (not page_match):

            result["Status"] = "MISMATCH"

            result["Reason"] = "Page mismatch"

        else:

            result["Status"] = "MISMATCH"

            result["Reason"] = "Page & title mismatch"

        results.append(result)

    validation = pd.DataFrame(results)

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------

    print()

    print("=" * 60)

    print("Repository Validation Summary")

    print("=" * 60)

    print(f"Official Tables   : {len(official_index)}")

    print(f"Repository Tables : {len(repository)}")

    print()

    print(validation["Status"].value_counts())

    print()

    print(validation["Reason"].value_counts())

    print()

    accuracy = ((validation["Status"] == "PASS").sum() / len(validation)) * 100

    print(f"Repository Accuracy : {accuracy:.1f}%")

    print("=" * 60)

    return validation


# 6.1 Extract Tables From PDF


def extract_tables_from_pdf(
    pdf_path, document_id, page_from=None, page_to=None
):
    """
    Complete extraction pipeline
    for one PDF.
    """

    candidate_tables = extract_candidate_tables(
        pdf_path, page_from=page_from, page_to=page_to
    )

    repository_tables = build_repository_tables(
        candidate_tables, pdf_path, document_id
    )

    repository_tables = merge_repository_tables(repository_tables)

    return repository_tables


# 6.2 Process Repository Row


def process_document(document_row, page_from=None, page_to=None):
    """
    Process one repository document.
    """

    pdf_path = get_pdf_path(document_row)

    tables = extract_tables_from_pdf(
        pdf_path,
        document_row["Document ID"],
        page_from=page_from,
        page_to=page_to,
    )

    logger.info(f"{len(tables)} table(s) extracted.")

    return tables


# 6.3 Process Complete Repository


def process_repository(repository_df):
    """
    Process every downloaded PDF.
    """

    all_tables = []

    pdfs = get_downloaded_pdfs(repository_df)

    for _, row in pdfs.iterrows():

        all_tables.extend(process_document(row))

    return all_tables


# 6.4 Export Tables

# =============================================================================
# Export Tables
# =============================================================================


def export_tables(repository_tables):
    """
    Export extracted tables and metadata.

    Folder Structure
    ----------------
    tables/

        TA970/

            TA970_DOC001/

                Table_01.csv

                Table_01.json

                Table_02.csv

                Table_02.json
    """

    for index, table in enumerate(repository_tables, start=1):

        # ------------------------------------------------------------
        # Create Folder
        # ------------------------------------------------------------

        ta_number = table["Document ID"].split("_")[0]

        document_id = table["Document ID"]

        output_folder = TABLE_FOLDER / ta_number / document_id

        output_folder.mkdir(parents=True, exist_ok=True)

        # ------------------------------------------------------------
        # File Name
        # ------------------------------------------------------------

        if table["Table Number"]:

            filename = (
                table["Table Number"]
                .replace(" ", "_")
                .replace("/", "_")
                .replace(":", "")
                + ".csv"
            )

        else:

            filename = f"Table_{index:02d}.csv"

        csv_file = output_folder / filename

        json_file = output_folder / filename.replace(".csv", ".json")

        # ------------------------------------------------------------
        # Save Table
        # ------------------------------------------------------------

        table["DataFrame"].to_csv(csv_file, index=False)

        # ------------------------------------------------------------
        # Metadata
        # ------------------------------------------------------------

        metadata = {
            "Document ID": table["Document ID"],
            "TA Number": ta_number,
            "Table Number": table["Table Number"],
            "Table Name": table["Table Name"],
            "PDF Page": table["PDF Page"],
            "Start Page": table["Start Page"],
            "End Page": table["End Page"],
            "Merged Pages": table["Merged Pages"],
            "Rows": table["Rows"],
            "Columns": table["Columns"],
        }

        with open(json_file, "w", encoding="utf-8") as file:

            json.dump(metadata, file, indent=4, ensure_ascii=False)

    logger.info(f"{len(repository_tables)} table(s) exported successfully.")


# 6.5 Streamlit API


def extract_tables(document_row, page_from=None, page_to=None, export=False):
    """
    Public API.

    Parameters
    ----------
    document_row

    export : bool

    Returns
    -------
    list
    """

    tables = process_document(
        document_row, page_from=page_from, page_to=page_to
    )

    if export:

        export_tables(tables)

    return tables


# =============================================================================
# Get Downloaded Document Path
# =============================================================================


def get_document_path(document):
    """
    Returns the local path of a downloaded document.
    """

    if document is None:
        return None

    if "Local Path" in document.index:
        return Path(document["Local Path"])

    if "Local File" in document.index:
        return Path(document["Local File"])

    if "File Path" in document.index:
        return Path(document["File Path"])

    return None


# =============================================================================
# Read Downloaded Document
# =============================================================================


def get_document_bytes(document):
    """
    Returns document bytes for preview/download.
    """

    file_path = get_document_path(document)

    if file_path is None:
        return None

    if not file_path.exists():
        return None

    with open(file_path, "rb") as file:

        return file.read()


# =============================================================================
# Check Download Status
# =============================================================================


def document_exists(document):
    """Return True if the document has already been downloaded."""

    file_path = get_document_path(document)

    if file_path is None:
        return False

    return file_path.exists()


# =============================================================================
# Is PDF
# =============================================================================


def is_pdf(document):
    """Return True if the downloaded document is a PDF file."""

    file_path = get_document_path(document)

    if file_path is None:
        return False

    return file_path.suffix.lower() == ".pdf"

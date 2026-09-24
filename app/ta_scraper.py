# =============================================================================
# NICE HTA PLATFORM
# TA Web Scraper
# =============================================================================

import re

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

from excel_manager import load_reference_excel

# =============================================================================
# TA Input Normalization
# =============================================================================


def normalize_ta_input(value: str) -> str:
    """
    Accepts:
        TA970
        970
        NICE URL

    Returns:
        NICE Guidance URL
    """

    value = value.strip()

    if value.lower().startswith("http"):
        return value

    ta = value.upper()

    if not ta.startswith("TA"):
        ta = f"TA{ta}"

    return f"https://www.nice.org.uk/guidance/{ta.lower()}"


# =============================================================================
# TA Number Formatter
# =============================================================================


def normalize_ta_number(value) -> str:
    """
    Standardise TA numbers.

    Examples
    --------
    1      -> TA001
    12     -> TA012
    78     -> TA078
    TA12   -> TA012
    TA078  -> TA078
    TA970  -> TA970
    """

    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    digits = "".join(ch for ch in value if ch.isdigit())

    if not digits:
        return value

    return f"TA{int(digits):03d}"


# =============================================================================
# NICE Configuration
# =============================================================================


BASE_URL = "https://www.nice.org.uk/guidance/{ta}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

TITLE_SPLIT_TOKENS = [
    " for treating ",
    " for the treatment of ",
    " for ",
    " with ",
    " and ",
]

# =============================================================================
# URL Builder - NICE Configuration
# =============================================================================


def build_url(value):

    if isinstance(value, pd.Series):
        value = value["TA ID"]

    value = str(value).strip()

    if value.lower().startswith("http"):
        return value

    return BASE_URL.format(ta=normalize_ta_number(value).lower())


# =============================================================================
# Download NICE Page
# =============================================================================


def fetch_page(url):

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)

        response.raise_for_status()

        return BeautifulSoup(response.text, "lxml")

    except Exception:
        return None


# =============================================================================
# Title
# =============================================================================


def extract_title(soup):

    h1 = soup.find("h1")

    if h1:
        return h1.get_text(strip=True)

    return None


# =============================================================================
# Breadcrumbs
# =============================================================================


def extract_breadcrumbs(soup):

    nav = soup.find(
        "nav", attrs={"aria-label": re.compile("breadcrumb", re.IGNORECASE)}
    )

    if nav is None:
        return []

    return [item.get_text(strip=True) for item in nav.find_all("li")]


# =============================================================================
# Disease Area
# =============================================================================


def extract_disease_area(breadcrumbs):

    try:
        idx = next(
            i
            for i, b in enumerate(breadcrumbs)
            if "conditions and diseases" in b.lower()
        )

        return breadcrumbs[idx + 1]

    except (StopIteration, IndexError):
        return None


# =============================================================================
# Disease Sub Area
# =============================================================================


def extract_disease_sub_area(breadcrumbs):

    try:
        idx = next(
            i
            for i, b in enumerate(breadcrumbs)
            if "conditions and diseases" in b.lower()
        )

        return breadcrumbs[idx + 2]

    except (StopIteration, IndexError):
        return None


# =============================================================================
# Technology Name
# =============================================================================


def extract_technology_name(title):

    if title is None:
        return None

    title_lower = title.lower()

    for token in TITLE_SPLIT_TOKENS:
        if token in title_lower:
            return title[: title_lower.index(token)].strip()

    return title


# =============================================================================
# Publication Date
# =============================================================================


def extract_publication_date(soup):

    text = soup.get_text(" ", strip=True)

    match = re.search(r"Published[:\s]+(\d{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)

    if match:
        return match.group(1)

    return None


# =============================================================================
# Last Updated Date
# =============================================================================


def extract_last_updated_date(soup):

    text = soup.get_text(" ", strip=True)

    match = re.search(r"Last updated[:\s]+(\d{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)

    if match:
        return match.group(1)

    return None


# =============================================================================
# NICE Recommendations
# =============================================================================


def extract_recommendations(soup):
    """
    Extract the complete NICE Recommendations section.

    Supports both:
        • New NICE layout
        • Older NICE layout
    """

    recommendation = extract_recommendations_new(soup)

    if recommendation:
        return recommendation

    recommendation = extract_recommendations_old(soup)

    if recommendation:
        return recommendation

    return None


# =============================================================================
# New NICE Layout
# =============================================================================


def extract_recommendations_new(soup):
    """
    Extract everything inside the '1 Recommendations'
    section until the next major section.
    """

    chapter = soup.find("div", class_="chapter")

    if chapter is None:
        return None

    output = []

    started = False

    for child in chapter.children:
        if not isinstance(child, Tag):
            continue

        # ---------------------------------------------------------
        # Start at Recommendations heading
        # ---------------------------------------------------------

        if child.name == "h2":
            heading = child.get_text(" ", strip=True).lower()

            if "recommendation" in heading:
                started = True
                continue

            elif started:
                break

        if not started:
            continue

        # ---------------------------------------------------------
        # Introductory paragraphs
        # ---------------------------------------------------------

        if child.name == "p":
            text = child.get_text(" ", strip=True)

            if text:
                output.append(text)

        # ---------------------------------------------------------
        # Recommendation articles
        # ---------------------------------------------------------

        elif child.name == "article":
            number = child.find("h3")

            body = child.find("div")

            if body is None:
                continue

            if number:
                output.append(number.get_text(strip=True))

            for p in body.find_all("p", recursive=False):
                text = p.get_text(" ", strip=True)

                if text:
                    output.append(text)

            for li in body.select("li"):
                bullet = li.get_text(" ", strip=True)

                if bullet:
                    output.append(f"• {bullet}")

    if output:
        return "\n\n".join(output)

    return None


# =============================================================================
# Older NICE Layout
# =============================================================================


def extract_recommendations_old(soup):
    """
    Extract complete Recommendations section
    from older NICE pages.
    """

    chapter = soup.find("div", class_="chapter")

    if chapter is None:
        return None

    output = []

    started = False

    for child in chapter.children:
        if not isinstance(child, Tag):
            continue

        # ---------------------------------------------------------
        # Start at Recommendations heading
        # ---------------------------------------------------------

        if child.name == "h2":
            heading = child.get_text(" ", strip=True).lower()

            if "recommendation" in heading:
                started = True
                continue

            elif started:
                break

        if not started:
            continue

        # ---------------------------------------------------------
        # Introductory paragraphs
        # ---------------------------------------------------------

        if child.name == "p":
            text = child.get_text(" ", strip=True)

            if text:
                output.append(text)

        # ---------------------------------------------------------
        # Numbered recommendations
        # ---------------------------------------------------------

        paragraph = child.find("p", class_="numbered-paragraph")

        if paragraph is None:
            continue

        number = ""

        span = paragraph.find("span", class_="paragraph-number")

        if span:
            number = span.get_text(strip=True)

            span.extract()

        text = paragraph.get_text(" ", strip=True)

        if number:
            output.append(number)

        output.append(text)

        for li in child.select("ul li"):
            bullet = li.get_text(" ", strip=True)

            if bullet:
                output.append(f"• {bullet}")

    if output:
        return "\n\n".join(output)

    return None


# =============================================================================
# Scrape Single TA
# =============================================================================


def scrape_ta(value):
    """
    Scrape NICE webpage and enrich it with
    information from the uploaded reference Excel.
    """

    url = build_url(value)

    soup = fetch_page(url)

    if soup is None:
        return None

    # Recommendations page
    recommendation_url = url.rstrip("/") + "/chapter/1-Recommendations"

    recommendation_soup = fetch_page(recommendation_url)

    title = extract_title(soup)

    breadcrumbs = extract_breadcrumbs(soup)

    if recommendation_soup is not None:
        nice_recommendation = extract_recommendations(recommendation_soup)
    else:
        nice_recommendation = None

    ta_number = normalize_ta_number(url.rstrip("/").split("/")[-1])

    record = {
        "TA Number": ta_number,
        "Title": title,
        "Disease Area": extract_disease_area(breadcrumbs),
        "Disease Sub-Area": extract_disease_sub_area(breadcrumbs),
        "Technology Name": extract_technology_name(title),
        "Publication Date": extract_publication_date(soup),
        "Last Updated": extract_last_updated_date(soup),
        "NICE Recommendation": nice_recommendation,
    }

    # ------------------------------------------------------------
    # Merge Reference Excel
    # ------------------------------------------------------------

    try:
        reference = load_reference_excel()

        reference["TA ID"] = (
            reference["TA ID"].map(normalize_ta_number)
            # .astype(str)
            # .str.upper()
            # .str.strip()
        )

        match = reference.loc[reference["TA ID"] == record["TA Number"]]

        # --------------------------------------------------------
        # Store ALL matching Excel rows
        # --------------------------------------------------------

        reference_rows = []

        for _, row in match.iterrows():
            reference_row = {
                "Rec no.": row.get("Rec no.", ""),
                "Appraisal Process": row.get("STA/MTA process", ""),
                "Recommendation": row.get(
                    "Categorisation (for specific recommendation)", ""
                ),
                "Technology Type": row.get("Technology type", ""),
                "Indication": row.get("Indication", ""),
                "Comments": row.get("Comment", ""),
            }

            reference_rows.append(reference_row)

        record["_reference_rows"] = reference_rows

    except Exception:
        record["_reference_rows"] = []

    return record


# =============================================================================
# Public Function for Streamlit
# =============================================================================


def scrape_ta_page(value):
    """
    Return combined NICE + Excel information
    as a vertical dataframe for Streamlit preview.

    Each matching Excel row produces exactly five fields:

        Appraisal Process
        Recommendation
        Technology Type
        Indication
        Comments

    If multiple Excel rows match the TA,
    the five-field block is repeated for every row.
    """

    record = scrape_ta(value)

    if record is None:
        raise ValueError("Unable to retrieve NICE webpage.")

    # ------------------------------------------------------------
    # Get ALL matching reference Excel rows
    # ------------------------------------------------------------

    reference_rows = record.pop("_reference_rows", [])

    # ------------------------------------------------------------
    # Build output
    # ------------------------------------------------------------

    fields = []
    results = []

    # ------------------------------------------------------------
    # Add NICE webpage information
    # ------------------------------------------------------------

    for field, value in record.items():
        fields.append(field)
        results.append(value)

    # ------------------------------------------------------------
    # Add reference Excel information
    #
    # Every Excel row ALWAYS produces all five fields.
    # Blank Excel values remain blank.
    # ------------------------------------------------------------

    excel_fields = [
        "Rec no.",
        "Appraisal Process",
        "Recommendation",
        "Technology Type",
        "Indication",
        "Comments",
    ]

    for row in reference_rows:
        for field in excel_fields:
            fields.append(field)

            value = row.get(field, "")

            # Convert Excel NaN to blank
            if pd.isna(value):
                value = ""

            results.append(value)

    # ------------------------------------------------------------
    # Create final dataframe
    # ------------------------------------------------------------

    preview = pd.DataFrame({"Field": fields, "Result": results})

    return preview, len(reference_rows) > 1


# =============================================================================
# Test Block
# =============================================================================

if __name__ == "__main__":
    print(scrape_ta("TA970"))

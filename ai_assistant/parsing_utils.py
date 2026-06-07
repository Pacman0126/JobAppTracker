import re


BAD_LOCATION_WORDS = {
    "vollzeit",
    "teilzeit",
    "festanstellung",
    "homeoffice",
    "gehalt",
    "benefits",
    "bewerbungen",
    "mitarbeiter",
    "stars",
    "tage",
    "job",
    "jobs",
    "stellenbeschreibung",
    "finden",
    "software",
    "entwickler",
    "informatik",
    "elektrotechnik",
    "feinmechanik",
    "optik",
    "logo",
    "passt",
    "weniger",
    "hervorragend",
    "erschienen",
    "woche",
    "jahr",
    "geschätzt",
}


LEGAL_COMPANY_SUFFIXES = (
    "GmbH & Co KG",
    "GmbH & Co. KG",
    "GmbH",
    "AG",
    "KG",
    "SE",
    "UG",
    "OHG",
    "e.V.",
)


def normalize_whitespace(text):
    return re.sub(r"\s+", " ", text or "").strip()


def get_clean_lines(text):
    return [
        line.strip()
        for line in (text or "").splitlines()
        if line.strip()
    ]


def extract_header_block(text, max_lines=25):
    lines = get_clean_lines(text)
    return lines[:max_lines]


def clean_company_name(company_name):
    company_name = normalize_whitespace(company_name)
    company_name = re.sub(r"\s+logo$", "", company_name, flags=re.IGNORECASE)

    stop_patterns = [
        r"\s+ist\s+ein\b",
        r"\s+ist\s+eine\b",
        r"\s+als\s+tochterunternehmen\b",
        r"\s+entwickelt\b",
        r"\s+sucht\b",
        r"\s+wir\s+suchen\b",
        r"\s+feste\s+anstellung\b",
        r"\s+vollzeit\b",
        r"\s+teilzeit\b",
        r"\s+homeoffice\b",
        r"\s+erschienen\b",
    ]

    for pattern in stop_patterns:
        company_name = re.split(
            pattern,
            company_name,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

    suffix_match = re.search(
        r"^(.{2,120}?\b(?:GmbH\s*&\s*Co\.?\s*KG|GmbH|AG|KG|SE|UG|OHG|e\.V\.))\b",
        company_name,
        flags=re.IGNORECASE,
    )

    if suffix_match:
        company_name = suffix_match.group(1).strip()

    return company_name[:255].strip()


def clean_job_title(title):
    title = normalize_whitespace(title)
    title = re.sub(r"-\s*job post", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\bm/w/d\b", "(m/w/d)", title)
    return title[:255].strip()


def looks_like_job_title(line):
    lowered = line.lower()

    job_words = (
        "m/w/d",
        "entwickler",
        "software",
        "developer",
        "ingenieur",
        "engineer",
        "manager",
        "consultant",
        "administrator",
        "spezialist",
        "techniker",
        "projektleiter",
    )

    return len(line) <= 180 and any(word in lowered for word in job_words)


def looks_like_company(line):
    line = normalize_whitespace(line)

    if not line or len(line) > 180:
        return False

    if looks_like_job_title(line):
        return False

    lowered = line.lower()

    bad_words = {
        "vollzeit",
        "teilzeit",
        "festanstellung",
        "homeoffice",
        "erschienen",
        "gehalt",
        "passt gut",
        "passt weniger",
        "passt hervorragend",
        "slide number",
        "softwareentwickler",
        "entwickler",
        "anwendungsentwicklung",
        "ingenieur",
        "engineer",
        "developer",
    }

    if any(word in lowered for word in bad_words):
        return False

    if any(suffix.lower() in lowered for suffix in LEGAL_COMPANY_SUFFIXES):
        return True

    words = line.split()

    if 2 <= len(words) <= 6 and not line.endswith((".", ":", ";")):
        uppercaseish = sum(1 for word in words if word[:1].isupper())
        return uppercaseish >= 2

    return False


def extract_company_candidate(text):
    lines = extract_header_block(text)

    # Prefer company-looking header lines.
    for line in lines[:15]:
        if looks_like_company(line):
            return clean_company_name(line)

    # Fallback: company with legal suffix anywhere in early text.
    early_text = normalize_whitespace(" ".join(lines[:25]))

    company_match = re.search(
        r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9&.,\- ]+"
        r"(?:GmbH\s*&\s*Co\.?\s*KG|GmbH|AG|KG|SE|OHG|UG|e\.V\.)"
        r"[A-Za-zÄÖÜäöüß0-9&.,\- ]*)\b",
        early_text,
    )

    if company_match:
        return clean_company_name(company_match.group(1))

    return ""


def extract_job_title_candidate(text):
    lines = extract_header_block(text)

    for line in lines[:15]:
        if looks_like_job_title(line):
            return clean_job_title(line)

    return ""


def is_bad_location_candidate(candidate):
    lowered = candidate.lower()

    if any(word in lowered for word in BAD_LOCATION_WORDS):
        return True

    if len(candidate) > 80:
        return True

    if candidate.endswith((".", ":", ";")):
        return True

    return False


def extract_postal_location_candidates(text):
    cleaned_text = normalize_whitespace(text)

    matches = re.findall(
        r"\b(\d{5})\s+"
        r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
        r"(?:\s+(?:am|an|im|in|der|den|dem|"
        r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)){0,4})",
        cleaned_text,
    )

    candidates = []

    for postcode, city in matches:
        candidate = f"{postcode} {city}".strip()

        if not is_bad_location_candidate(candidate):
            candidates.append(candidate)

    return candidates


def extract_explicit_location_candidates(text):
    cleaned_text = normalize_whitespace(text)

    patterns = [
        r"(?:Standort|Arbeitsort|Einsatzort)\s+(.{3,180}?)(?:\s+einen|\s+eine|\s+zum|\s+zur|\s+als|\s+in Vollzeit|\s+Vollzeit|\s+Teilzeit|\.|$)",
        r"(?:in|am Standort|für den Standort)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+(?:\s+(?:am|an|im|in|der|den|dem|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)){0,3})",
    ]

    candidates = []

    for pattern in patterns:
        for phrase in re.findall(pattern, cleaned_text, flags=re.IGNORECASE):
            for part in re.split(r",|\s+oder\s+|\s+und\s+", phrase):
                candidate = normalize_whitespace(part).strip(" .,:;()-")

                if candidate and not is_bad_location_candidate(candidate):
                    candidates.append(candidate)

    return candidates


def extract_city_line_candidates(text):
    lines = extract_header_block(text, max_lines=50)
    candidates = []

    employment_markers = {
        "feste anstellung",
        "festanstellung",
        "vollzeit",
        "teilzeit",
        "homeoffice",
        "remote",
        "hybrid",
    }

    for index, line in enumerate(lines):
        candidate = normalize_whitespace(line)

        if not candidate:
            continue

        if re.search(r"\d", candidate):
            continue

        if len(candidate.split()) > 4:
            continue

        if is_bad_location_candidate(candidate):
            continue

        if looks_like_job_title(candidate) or looks_like_company(candidate):
            continue

        lowered_next = lines[index + 1].lower() if index + \
            1 < len(lines) else ""

        # Strong signal: job boards often show city directly before employment type.
        if any(marker in lowered_next for marker in employment_markers):
            candidates.append(candidate)

    return candidates


# def extract_city_like_candidates(text):
#     header_text = normalize_whitespace(
#         " ".join(extract_header_block(text, 30)))

#     candidates = re.findall(
#         r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]{3,}"
#         r"(?:\s+(?:am|an|im|in|der|den|dem|"
#         r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]{3,})){0,2}\b",
#         header_text,
#     )

#     cleaned_candidates = []

#     for candidate in candidates[:80]:
#         candidate = normalize_whitespace(candidate)

#         if is_bad_location_candidate(candidate):
#             continue

#         if looks_like_job_title(candidate) or looks_like_company(candidate):
#             continue

#         cleaned_candidates.append(candidate)

#     return cleaned_candidates
def extract_city_like_candidates(text):
    return []


def extract_location_candidates(text):
    """
    Returns ordered candidates.
    Google validation happens later in location_utils/services.
    """
    candidates = []

    for extractor in (
        extract_postal_location_candidates,
        extract_explicit_location_candidates,
        extract_city_line_candidates,
        extract_city_like_candidates,
    ):
        for candidate in extractor(text):
            if candidate not in candidates:
                candidates.append(candidate)

    return candidates

import re


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


def normalize_whitespace(text):
    return re.sub(r"\s+", " ", text or "").strip()


def get_clean_lines(text):
    return [
        line.strip()
        for line in (text or "").splitlines()
        if line.strip()
    ]


def extract_header_block(text, max_lines=40):
    return get_clean_lines(text)[:max_lines]


def clean_job_title(title):
    title = normalize_whitespace(title)

    title = re.sub(r"-\s*job post", "", title, flags=re.IGNORECASE)

    # Normalize all common m/w/d variants to one clean form.
    title = re.sub(
        r"\(?\b[mwdivx/-]{1,8}\b\)?",
        lambda match: "(m/w/d)" if "m" in match.group(0).lower()
        and "w" in match.group(0).lower()
        and "d" in match.group(0).lower()
        else match.group(0),
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(r"\(\s*\(m/w/d\)\s*\)", "(m/w/d)", title)
    title = re.sub(r"\s+", " ", title)

    return title[:255].strip()


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
        r"^(.{2,140}?\b(?:GmbH\s*&\s*Co\.?\s*KG|GmbH|AG|KG|SE|UG|OHG|e\.V\.))\b",
        company_name,
        flags=re.IGNORECASE,
    )

    if suffix_match:
        company_name = suffix_match.group(1).strip()

    return company_name[:255].strip()


def looks_like_job_title(line):
    lowered = (line or "").lower()

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
        "anwendungsentwicklung",
    )

    return len(line or "") <= 180 and any(word in lowered for word in job_words)


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
        "bewerben",
        "stellenbeschreibung",
    }

    if any(word in lowered for word in bad_words):
        return False

    if any(suffix.lower() in lowered for suffix in LEGAL_COMPANY_SUFFIXES):
        return True

    words = line.split()

    if 2 <= len(words) <= 7 and not line.endswith((".", ":", ";")):
        uppercaseish = sum(1 for word in words if word[:1].isupper())
        return uppercaseish >= 2

    return False


def extract_job_title_candidate(text):
    for line in extract_header_block(text, max_lines=25):
        if looks_like_job_title(line):
            return clean_job_title(line)

    return ""


def extract_company_candidate(text):
    lines = extract_header_block(text, max_lines=40)

    for index, line in enumerate(lines[:20]):
        if not looks_like_company(line):
            continue

        previous_line = lines[index - 1] if index > 0 else ""

        if previous_line and clean_job_title(previous_line) == clean_job_title(line):
            continue

        return clean_company_name(line)

    early_text = normalize_whitespace(" ".join(lines[:30]))

    company_match = re.search(
        r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9&.,\- ]+"
        r"(?:GmbH\s*&\s*Co\.?\s*KG|GmbH|AG|KG|SE|OHG|UG|e\.V\.)"
        r"[A-Za-zÄÖÜäöüß0-9&.,\- ]*)\b",
        early_text,
    )

    if company_match:
        return clean_company_name(company_match.group(1))

    return ""


def is_bad_location_candidate(candidate):
    candidate = normalize_whitespace(candidate)
    lowered = candidate.lower()

    if not candidate:
        return True

    if len(candidate) > 80:
        return True

    if candidate.endswith((".", ":", ";")):
        return True

    if any(word in lowered for word in BAD_LOCATION_WORDS):
        return True

    if looks_like_job_title(candidate):
        return True

    if looks_like_company(candidate):
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
        candidate = normalize_whitespace(f"{postcode} {city}")

        if not is_bad_location_candidate(candidate):
            candidates.append(candidate)

    return candidates


def extract_explicit_location_candidates(text):
    cleaned_text = normalize_whitespace(text)

    patterns = [
        r"(?:Standort|Arbeitsort|Einsatzort|Ort)\s+(.{3,180}?)(?:\s+einen|\s+eine|\s+zum|\s+zur|\s+als|\s+in Vollzeit|\s+Vollzeit|\s+Teilzeit|\.|$)",
        r"(?:für den Standort|am Standort|in)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+(?:\s+(?:am|an|im|in|der|den|dem|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)){0,3})",
    ]

    candidates = []

    for pattern in patterns:
        for phrase in re.findall(pattern, cleaned_text, flags=re.IGNORECASE):
            for part in re.split(r",|\s+oder\s+|\s+und\s+", phrase):
                candidate = normalize_whitespace(part).strip(" .,:;()-")

                if not is_bad_location_candidate(candidate):
                    candidates.append(candidate)

    return candidates


def extract_city_line_candidates(text):
    lines = extract_header_block(text, max_lines=60)
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

        if re.search(r"\d", candidate):
            continue

        if len(candidate.split()) > 4:
            continue

        if is_bad_location_candidate(candidate):
            continue

        previous_line = lines[index - 1].lower() if index > 0 else ""
        next_line = lines[index + 1].lower() if index + 1 < len(lines) else ""

        strong_header_signal = any(
            marker in next_line
            for marker in employment_markers
        )

        after_company_signal = looks_like_company(previous_line)

        if strong_header_signal or after_company_signal:
            candidates.append(candidate)

    return candidates


def extract_location_candidates(text):
    candidates = []

    for extractor in (
        extract_postal_location_candidates,
        extract_explicit_location_candidates,
        extract_city_line_candidates,
    ):
        for candidate in extractor(text):
            if candidate not in candidates:
                candidates.append(candidate)

    return candidates


def extract_contact_data(text):
    cleaned_text = normalize_whitespace(text)
    lines = get_clean_lines(text)

    contact_person = ""
    contact_email = ""
    contact_phone = ""

    email_match = re.search(
        r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
        cleaned_text,
    )

    if email_match:
        contact_email = email_match.group(0)

    phone_match = re.search(
        r"(?:Telefon|Tel\.?|Phone)\s*[:\-]?\s*(\+?\d[\d\s()/.-]{6,})",
        cleaned_text,
        re.IGNORECASE,
    )

    if phone_match:
        contact_phone = phone_match.group(1).strip()

    contact_markers = {
        "kontakt",
        "fragen? ihr ansprechpartner:",
        "ihr ansprechpartner:",
        "ansprechpartner:",
        "ansprechpartnerin:",
    }

    contact_index = None

    for index, line in enumerate(lines):
        if line.lower().strip() in contact_markers:
            contact_index = index
            break

    if contact_index is not None:
        contact_window = lines[contact_index + 1: contact_index + 8]

        for line in contact_window:
            candidate = line.strip()

            if not candidate:
                continue

            if candidate.lower().startswith(("tel", "telefon", "e-mail", "email")):
                continue

            if re.search(r"\d", candidate):
                continue

            if 2 <= len(candidate.split()) <= 4:
                contact_person = candidate
                break

    if not contact_person:
        inline_person_match = re.search(
            r"(?:Ansprechpartner|Ansprechpartnerin)\s*[:\-]?\s*"
            r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
            r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+){1,3})",
            cleaned_text,
            re.IGNORECASE,
        )

        if inline_person_match:
            contact_person = inline_person_match.group(1).strip()

    return {
        "contact_person": contact_person,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
    }


def detect_application_method(text, contact_email=""):
    lower_text = normalize_whitespace(text).lower()

    if contact_email:
        return "email"

    if "online-bewerbung" in lower_text:
        return "employer_website"

    if "karriere" in lower_text or "career" in lower_text:
        return "employer_website"

    return "job_board"

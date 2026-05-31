import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from .location_utils import verify_german_location_with_google


def extract_text_from_url(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

    except requests.RequestException:
        return {
            "success": False,
            "text": "",
            "message": (
                "This job page could not be read automatically. "
                "Please copy and paste the job description text above under 'Fallback'."
            ),
            "json_ld_data": {},
        }

    soup = BeautifulSoup(response.text, "html.parser")
    json_ld_data = extract_json_ld_job_data(soup)

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) < 500:
        return {
            "success": False,
            "text": text,
            "message": (
                "Only limited job text could be read automatically. "
                "Please copy and paste the job description text above under 'Fallback'."
            ),
            "json_ld_data": {},
        }

    return {
        "success": True,
        "text": text[:8000],
        "message": "Job posting text extracted successfully.",
        "json_ld_data": json_ld_data,
    }


def detect_source_website(url):
    domain = urlparse(url).netloc.lower()

    if "stepstone" in domain:
        return "StepStone"

    if "linkedin" in domain:
        return "LinkedIn"

    if "indeed" in domain:
        return "Indeed"

    if "xing" in domain:
        return "XING"

    return domain.replace("www.", "")


def extract_json_ld_job_data(soup):
    job_data = {}

    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        try:
            data = json.loads(script.string or "")
        except (TypeError, json.JSONDecodeError):
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            if item.get("@type") != "JobPosting":
                continue

            hiring_org = item.get("hiringOrganization", {})
            job_location = item.get("jobLocation", {})

            if isinstance(job_location, list) and job_location:
                job_location = job_location[0]

            address = {}
            if isinstance(job_location, dict):
                address = job_location.get("address", {}) or {}

            location_parts = [
                address.get("postalCode", ""),
                address.get("addressLocality", ""),
            ]

            job_data = {
                "company_name": hiring_org.get("name", ""),
                "job_title": item.get("title", ""),
                "location": " ".join(
                    part for part in location_parts if part
                ).strip(),
                "job_description": item.get("description", ""),
            }

            return job_data

    return job_data


def extract_structured_job_data(text, url=""):
    source_website = detect_source_website(url) if url else ""

    cleaned_text = re.sub(r"\s+", " ", text).strip()
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    company_name = ""
    job_title = ""
    location = extract_german_location(cleaned_text)
    locations = extract_multiple_german_locations(cleaned_text)
    contact_person = ""
    contact_email = ""

    company_indicators = (
        "GmbH",
        "AG",
        "KG",
        "SE",
        "UG",
        "OHG",
        "Co.",
        "Automation",
        "Group",
    )

    # Strong pasted job-board pattern:
    # line 1 often = title, line 2 often = company.
    # Location is NOT taken from line position; it is extracted by postal code.
    if len(lines) >= 2:
        likely_title = lines[0]
        likely_company = lines[1]

        if any(indicator in likely_company for indicator in company_indicators):
            job_title = likely_title
            company_name = likely_company

    # StepStone URL extraction pattern
    if not job_title or not company_name or not location:
        title_match = re.search(
            r"^(.*?)\s*-\s*Job bei der Firma\s+(.+?)\s+in\s+(.+?)\s+Jobs finden",
            cleaned_text,
            re.IGNORECASE,
        )

        if title_match:
            job_title = job_title or title_match.group(1).strip()
            company_name = company_name or title_match.group(2).strip()

            if not location:
                location = title_match.group(3).strip()

    # Generic company fallback
    if not company_name:
        company_pattern = re.compile(
            r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9&.,\- ]+"
            r"(GmbH|AG|KG|SE|OHG|UG|e\.V\.|Group|Solutions|Automation)"
            r"[A-Za-zÄÖÜäöüß0-9&.,\- ]*)\b"
        )

        for line in lines:
            match = company_pattern.search(line)
            if match:
                company_name = match.group(1).strip()
                break

    # Generic job title fallback
    if not job_title:
        for line in lines[:25]:
            lowered = line.lower()

            if (
                "(m/w/d)" in lowered
                or "m/w/d" in lowered
                or "entwickler" in lowered
                or "software" in lowered
                or "developer" in lowered
                or "ingenieur" in lowered
                or "engineer" in lowered
            ):
                if len(line) <= 180:
                    job_title = line.strip()
                    break

    # Contact person after "Kontakt"
    contact_index = None
    for index, line in enumerate(lines):
        if line.lower() == "kontakt":
            contact_index = index
            break

    if contact_index is not None:
        contact_window = lines[contact_index: contact_index + 20]

        for line in contact_window:
            if (
                line.startswith("Frau ")
                or line.startswith("Herr ")
                or line.startswith("Ms. ")
                or line.startswith("Mr. ")
            ):
                contact_person = line.strip()
                break

    # Email detection
    contact_email_match = re.search(
        r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
        cleaned_text,
    )

    if contact_email_match:
        contact_email = contact_email_match.group(0)

    application_method = "job_board"
    lower_text = cleaned_text.lower()

    if contact_email:
        application_method = "email"

    if "online-bewerbung" in lower_text:
        application_method = "email" if contact_email else "employer_website"

    if "karriere" in lower_text or "career" in lower_text:
        application_method = "employer_website" if not contact_email else "email"

    job_title = clean_job_title(job_title)
    company_name = clean_company_name(company_name)

    if location:
        verified_location = verify_german_location_with_google(location)
        if verified_location:
            location = verified_location

    return {
        "company_name": company_name,
        "job_title": job_title,
        "location": location,
        "locations": locations,
        "source_website": source_website,
        "application_method": application_method,
        "contact_person": contact_person,
        "contact_email": contact_email,
        "job_url": url,
        "job_description": cleaned_text[:5000],
    }


def clean_job_title(title):
    title = re.sub(r"-\s*job post", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\bm/w/d\b", "(m/w/d)", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def clean_company_name(company_name):
    company_name = re.sub(r"\s+", " ", company_name)
    company_name = re.sub(r"\s+logo$", "", company_name, flags=re.IGNORECASE)
    return company_name.strip()


def extract_german_location(cleaned_text):
    """
    Extract and verify German postal-code + city.

    Examples:
    96052 Bamberg
    33415 Verl
    60311 Frankfurt am Main

    Rejects:
    10000 Mitarbeiter
    5001-10000 Mitarbeiter
    """

    # Find ALL possible German postal-code candidates
    matches = re.findall(
        r"\b(\d{5})\s+"
        r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
        r"(?:\s+(?:am|an|im|in|der|den|dem|"
        r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)){0,4})",
        cleaned_text,
    )

    if not matches:
        return ""

    bad_words = {
        "mitarbeiter",
        "jobs",
        "bewertungen",
        "unternehmen",
        "unternehmensporträt",
        "gehalt",
        "vollzeit",
        "teilzeit",
        "festanstellung",
        "tage",
        "bewerbungen",
        "sterne",
    }

    for postcode, city in matches:

        candidate = f"{postcode} {city}".strip()

        lowered = candidate.lower()

        # Reject obvious junk
        if any(word in lowered for word in bad_words):
            continue

        # Clean trailing junk words
        candidate = re.split(
            r"\b("
            r"Festanstellung|"
            r"Teilzeit|"
            r"Vollzeit|"
            r"Homeoffice|"
            r"Hat|"
            r"Tage|"
            r"Benefits|"
            r"Stellenbeschreibung|"
            r"Jobs|"
            r"Bewertungen"
            r")\b",
            candidate,
        )[0].strip()

        # Verify against Google Maps
        verified_location = verify_german_location_with_google(candidate)

        if verified_location:
            return verified_location

    return ""


# def extract_multiple_german_locations(cleaned_text):
#     verified_locations = []

#     header_stop_markers = [
#         "Stellenbeschreibung",
#         "Tätigkeitsbereich",
#         "Aufgaben",
#         "Anforderungen",
#         "Profil",
#         "Wir bieten",
#         "Kontakt",
#         "Benefits",
#         "Full job description",
#         "Job Description",
#     ]

#     header_text = cleaned_text

#     for marker in header_stop_markers:
#         marker_index = header_text.lower().find(marker.lower())

#         if marker_index != -1:
#             header_text = header_text[:marker_index]
#             break

#     header_text = header_text[:3000]

#     bad_candidate_words = {
#         "vollzeit",
#         "teilzeit",
#         "festanstellung",
#         "homeoffice",
#         "gehalt",
#         "benefits",
#         "bewerbungen",
#         "mitarbeiter",
#         "stars",
#         "tage",
#         "job",
#         "jobs",
#         "stellenbeschreibung",
#         "finden",
#         "software",
#         "entwickler",
#         "finanz",
#         "informatik",
#     }

#     def clean_city_candidate(candidate):
#         candidate = candidate.strip(" .;:-")

#         candidate = re.sub(
#             r"^.*\b(GmbH\s*&\s*Co\.\s*KG|GmbH|AG|KG|SE|UG|OHG)\s+",
#             "",
#             candidate,
#             flags=re.IGNORECASE,
#         )

#         candidate = re.split(
#             r"\b("
#             r"Feste Anstellung|Festanstellung|Vollzeit|Teilzeit|"
#             r"Homeoffice|Erschienen|Gehalt|Benefits|Job|Jobs"
#             r")\b",
#             candidate,
#             flags=re.IGNORECASE,
#         )[0]

#         return candidate.strip(" .;:-")

#     location_phrases = []

#     # Pattern 1:
#     # Standort Hannover, Münster oder Frankfurt am Main
#     targeted_patterns = [
#         r"Standort\s+(.{3,160}?)(?:\s+einen|\s+eine|\s+zum|\s+zur|\.|$)",
#         r"Arbeitsort\s+(.{3,160}?)(?:\s+einen|\s+eine|\s+zum|\s+zur|\.|$)",
#     ]

#     for pattern in targeted_patterns:
#         for match in re.findall(pattern, header_text, flags=re.IGNORECASE):
#             location_phrases.append(match)

#     # Pattern 2:
#     # Company name + Hannover, Münster, Frankfurt am Main + Feste Anstellung
#     company_location_match = re.search(
#         r"(?:GmbH\s*&\s*Co\.\s*KG|GmbH|AG|KG|SE|UG|OHG)\s+"
#         r"(.{3,180}?)\s+"
#         r"(?:Feste Anstellung|Festanstellung|Vollzeit|Teilzeit|Homeoffice)",
#         header_text,
#         flags=re.IGNORECASE,
#     )

#     if company_location_match:
#         location_phrases.append(company_location_match.group(1))

#     # Pattern 3:
#     # Generic comma-separated city group
#     comma_groups = re.findall(
#         r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\- ]+"
#         r"(?:,\s*[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\- ]+)+)",
#         header_text,
#     )

#     location_phrases.extend(comma_groups)

#     city_name_pattern = re.compile(
#         r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
#         r"(?:\s+(?:am|an|im|in|der|den|dem|"
#         r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)){0,3}\b"
#     )

#     for phrase in location_phrases:
#         city_candidates = []

#         for part in re.split(r",|\s+oder\s+", phrase):
#             part = clean_city_candidate(part)

#             match = city_name_pattern.search(part)

#             if match:
#                 city_candidates.append(match.group(0))

#         for city_candidate in city_candidates:
#             lowered = city_candidate.lower()

#     # Pattern 4:
#     # Standort Hannover, Münster oder Frankfurt am Main
#     oder_location_match = re.search(
#         r"Standort\s+(.{3,120}?)\s+(?:einen|eine|zum|zur|als|in Vollzeit|Vollzeit|Teilzeit)",
#         header_text,
#         flags=re.IGNORECASE,
#     )

#     if oder_location_match:
#         phrase = oder_location_match.group(1)

#         city_candidates = re.split(r",|\s+oder\s+", phrase)

#         for city_candidate in city_candidates:
#             city_candidate = clean_city_candidate(city_candidate)

#             if not city_candidate:
#                 continue

#             verified = verify_german_location_with_google(city_candidate)

#             if verified and verified not in verified_locations:
#                 verified_locations.append(verified)

#     print("\n=== LOCATION PHRASES ===")
#     for phrase in location_phrases:
#         print(phrase)

#     print("\n=== VERIFIED LOCATIONS ===")
#     for loc in verified_locations:
#         print(loc)

#     if verified_locations:
#         return verified_locations

#     # Postal-code fallback
#     postal_candidates = re.findall(
#         r"\b(\d{5})\s+"
#         r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
#         r"(?:\s+(?:am|an|im|in|der|den|dem|"
#         r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)){0,4})",
#         header_text,
#     )

#     for postcode, city in postal_candidates:
#         candidate = f"{postcode} {city}".strip()
#         verified = verify_german_location_with_google(candidate)

#         if verified and verified not in verified_locations:
#             verified_locations.append(verified)

#     return verified_locations
def extract_multiple_german_locations(cleaned_text):
    verified_locations = []

    header_stop_markers = [
        "Stellenbeschreibung",
        "Tätigkeitsbereich",
        "Aufgaben",
        "Anforderungen",
        "Profil",
        "Wir bieten",
        "Kontakt",
        "Benefits",
        "Full job description",
        "Job Description",
    ]

    header_text = cleaned_text

    for marker in header_stop_markers:
        marker_index = header_text.lower().find(marker.lower())

        if marker_index != -1:
            header_text = header_text[:marker_index]
            break

    header_text = header_text[:3000]

    bad_candidate_words = {
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
        "finanz",
        "informatik",
    }

    def clean_city_candidate(candidate):
        candidate = candidate.strip(" .;:-")

        candidate = re.sub(
            r"^.*\b(GmbH\s*&\s*Co\.\s*KG|GmbH|AG|KG|SE|UG|OHG)\s+",
            "",
            candidate,
            flags=re.IGNORECASE,
        )

        candidate = re.split(
            r"\b("
            r"Feste Anstellung|Festanstellung|Vollzeit|Teilzeit|"
            r"Homeoffice|Erschienen|Gehalt|Benefits|Job|Jobs|finden"
            r")\b",
            candidate,
            flags=re.IGNORECASE,
        )[0]

        return candidate.strip(" .;:-")

    location_phrases = []

    targeted_patterns = [
        r"Standort\s+(.{3,180}?)(?:\s+einen|\s+eine|\s+zum|\s+zur|\s+als|\s+in Vollzeit|\s+Vollzeit|\s+Teilzeit|\.|$)",
        r"Arbeitsort\s+(.{3,180}?)(?:\s+einen|\s+eine|\s+zum|\s+zur|\s+als|\s+in Vollzeit|\s+Vollzeit|\s+Teilzeit|\.|$)",
    ]

    for pattern in targeted_patterns:
        for match in re.findall(pattern, header_text, flags=re.IGNORECASE):
            location_phrases.append(match)

    company_location_match = re.search(
        r"(?:GmbH\s*&\s*Co\.\s*KG|GmbH|AG|KG|SE|UG|OHG)\s+"
        r"(.{3,180}?)\s+"
        r"(?:Feste Anstellung|Festanstellung|Vollzeit|Teilzeit|Homeoffice)",
        header_text,
        flags=re.IGNORECASE,
    )

    if company_location_match:
        location_phrases.append(company_location_match.group(1))

    comma_groups = re.findall(
        r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\- ]+"
        r"(?:,\s*[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\- ]+)+)",
        header_text,
    )

    location_phrases.extend(comma_groups)

    city_name_pattern = re.compile(
        r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
        r"(?:\s+(?:am|an|im|in|der|den|dem|"
        r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)){0,3}\b"
    )

    for phrase in location_phrases:
        for part in re.split(r",|\s+oder\s+", phrase):
            part = clean_city_candidate(part)

            match = city_name_pattern.search(part)

            if not match:
                continue

            city_candidate = match.group(0)
            lowered = city_candidate.lower()

            if any(word in lowered for word in bad_candidate_words):
                continue

            verified = verify_german_location_with_google(city_candidate)

            if verified and verified not in verified_locations:
                verified_locations.append(verified)

    if verified_locations:
        return verified_locations

    postal_candidates = re.findall(
        r"\b(\d{5})\s+"
        r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
        r"(?:\s+(?:am|an|im|in|der|den|dem|"
        r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)){0,4})",
        header_text,
    )

    for postcode, city in postal_candidates:
        candidate = f"{postcode} {city}".strip()
        verified = verify_german_location_with_google(candidate)

        if verified and verified not in verified_locations:
            verified_locations.append(verified)

    return verified_locations

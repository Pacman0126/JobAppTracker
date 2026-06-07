import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from .location_utils import verify_german_location_with_google

from .parsing_utils import clean_company_name
from .parsing_utils import clean_job_title
from .parsing_utils import extract_company_candidate
from .parsing_utils import extract_job_title_candidate
from .parsing_utils import extract_location_candidates
from .parsing_utils import normalize_whitespace


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

    cleaned_text = normalize_whitespace(text)
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    company_name = extract_company_candidate(text)
    job_title = extract_job_title_candidate(text)

    location_candidates = extract_location_candidates(text)
    locations = []

    for candidate in location_candidates:
        verified = verify_german_location_with_google(candidate)

        if verified and verified not in locations:
            locations.append(verified)

    location = locations[0] if locations else ""

    contact_person = ""
    contact_email = ""
    contact_phone = ""

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

    # Contact person detection
    contact_index = None

    contact_markers = [
        "kontakt",
        "fragen? ihr ansprechpartner:",
        "ihr ansprechpartner:",
        "ansprechpartner:",
        "ansprechpartnerin:",
    ]

    for index, line in enumerate(lines):
        lowered_line = line.lower().strip()

        if lowered_line in contact_markers:
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

            if len(candidate.split()) in [2, 3, 4]:
                contact_person = candidate
                break

    # Fallback: inline German contact phrase
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

    # Email detection
    contact_email_match = re.search(
        r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
        cleaned_text,
    )

    if contact_email_match:
        contact_email = contact_email_match.group(0)

    # Phone detection
    contact_phone_match = re.search(
        r"(?:Telefon|Tel\.?|Phone)\s*[:\-]?\s*(\+?\d[\d\s()/.-]{6,})",
        cleaned_text,
        re.IGNORECASE,
    )

    if contact_phone_match:
        contact_phone = contact_phone_match.group(1).strip()

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

    if not location and locations:
        location = locations[0]

    return {
        "company_name": company_name,
        "job_title": job_title,
        "location": location,
        "locations": locations,
        "source_website": source_website,
        "application_method": application_method,
        "contact_person": contact_person,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "job_url": url,
        "job_description": cleaned_text[:5000],
    }

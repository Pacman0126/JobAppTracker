import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .location_utils import deduplicate_locations
from .location_utils import verify_german_location_with_google
from .parsing_utils import clean_company_name
from .parsing_utils import clean_job_title
from .parsing_utils import detect_application_method
from .parsing_utils import extract_company_candidate
from .parsing_utils import extract_contact_data
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

    text = soup.get_text(separator="\n")
    text = re.sub(r"\n\s*\n+", "\n", text).strip()

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


def verify_location_candidates(candidates):
    verified_locations = []

    for candidate in candidates:
        verified = verify_german_location_with_google(candidate)

        if verified:
            verified_locations.append(verified)

    return deduplicate_locations(verified_locations)


def extract_structured_job_data(text, url=""):
    cleaned_text = normalize_whitespace(text)
    source_website = detect_source_website(url) if url else ""

    company_name = extract_company_candidate(text)
    job_title = extract_job_title_candidate(text)

    location_candidates = extract_location_candidates(text)
    locations = verify_location_candidates(location_candidates)
    location = locations[0] if locations else ""

    # "debug": {
    #     "company_candidate": company_name,
    #     "job_title_candidate": job_title,
    #     "location_candidates": location_candidates,
    #     "verified_locations": locations,
    # },

    contact_data = extract_contact_data(text)

    application_method = detect_application_method(
        text,
        contact_email=contact_data.get("contact_email", ""),
    )

    return {
        "company_name": clean_company_name(company_name),
        "job_title": clean_job_title(job_title),
        "location": location,
        "locations": locations,
        "source_website": source_website,
        "application_method": application_method,
        "contact_person": contact_data.get("contact_person", ""),
        "contact_email": contact_data.get("contact_email", ""),
        "contact_phone": contact_data.get("contact_phone", ""),
        "job_url": url,
        "job_description": cleaned_text[:5000],
        "debug": {
            "company_candidate": company_name,
            "job_title_candidate": job_title,
            "location_candidates": location_candidates,
            "verified_locations": locations,
        },
    }

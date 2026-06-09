import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .parser_pipeline import build_parser_result
from .parsing_utils import normalize_whitespace
from .parser_diagnostics import build_parser_report


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

            return {
                "company_name": hiring_org.get("name", ""),
                "job_title": item.get("title", ""),
                "location": " ".join(
                    part for part in location_parts if part
                ).strip(),
                "job_description": item.get("description", ""),
            }

    return job_data


def merge_json_ld_data(structured_data, json_ld_data):
    """
    JSON-LD is usually cleaner than scraped text when available.
    Use it only to fill blanks so user-visible parser results are not overwritten.
    """
    if not json_ld_data:
        return structured_data

    for key, value in json_ld_data.items():
        if value and not structured_data.get(key):
            structured_data[key] = value

    return structured_data


def extract_structured_job_data(text, url="", json_ld_data=None):
    cleaned_text = normalize_whitespace(text)
    source_website = detect_source_website(url) if url else ""

    parser_result = build_parser_result(text)

    parser_report = build_parser_report(
        parser_result,
        json_ld_available=bool(json_ld_data),
    )

    company = parser_result["company"]
    job = parser_result["job"]
    locations = parser_result["locations"]
    contacts = parser_result["contacts"]

    structured_data = {
        "company_name": company["value"],
        "job_title": job["value"],
        "location": locations["value"],
        "locations": locations["verified"],
        "source_website": source_website,
        "application_method": parser_result["application_method"],
        "contact_person": contacts.get("contact_person", ""),
        "contact_email": contacts.get("contact_email", ""),
        "contact_phone": contacts.get("contact_phone", ""),
        "job_url": url,
        "job_description": cleaned_text[:5000],
        "parser_report": parser_report,
        "debug": {
            "company_candidate": company["candidate"],
            "job_title_candidate": job["candidate"],
            "location_candidates": locations["candidates"],
            "verified_locations": locations["verified"],
        },
    }

    return merge_json_ld_data(structured_data, json_ld_data or {})

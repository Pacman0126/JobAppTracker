"""
parser_pipeline.py

Coordinates candidate extraction and parser stages.

This module should NOT:
- talk to Django
- make HTTP requests
- call Google Maps APIs

Its job is to coordinate parsing utilities and
return normalized parser results.
"""

from .parsing_utils import (
    clean_company_name,
    clean_job_title,
    detect_application_method,
    extract_company_candidate,
    extract_contact_data,
    extract_job_title_candidate,
    extract_location_candidates,
)

from .location_utils import (
    deduplicate_locations,
    verify_german_location_with_google,
)


def parse_company(text):
    candidate = extract_company_candidate(text)

    return {
        "candidate": candidate,
        "value": clean_company_name(candidate),
    }


def parse_job_title(text):
    candidate = extract_job_title_candidate(text)

    return {
        "candidate": candidate,
        "value": clean_job_title(candidate),
    }


def parse_locations(text):
    candidates = extract_location_candidates(text)

    verified = []

    for candidate in candidates:
        location = verify_german_location_with_google(candidate)

        if location:
            verified.append(location)

    verified = deduplicate_locations(verified)

    return {
        "candidates": candidates,
        "verified": verified,
        "value": verified[0] if verified else "",
    }


def parse_contacts(text):
    return extract_contact_data(text)


def parse_application_method(
    text,
    contact_email="",
):
    return detect_application_method(
        text,
        contact_email=contact_email,
    )


def build_parser_result(text):
    company = parse_company(text)
    job = parse_job_title(text)
    locations = parse_locations(text)
    contacts = parse_contacts(text)

    application_method = parse_application_method(
        text,
        contact_email=contacts.get(
            "contact_email",
            "",
        ),
    )

    return {
        "company": company,
        "job": job,
        "locations": locations,
        "contacts": contacts,
        "application_method": application_method,
    }

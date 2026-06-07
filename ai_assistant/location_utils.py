import re
import requests
from decouple import config


BAD_LOCATION_WORDS = {
    "mitarbeiter",
    "jobs",
    "bewertungen",
    "unternehmensporträt",
    "gehalt",
    "vollzeit",
    "teilzeit",
    "festanstellung",
}


def looks_like_bad_location(candidate):
    lowered = candidate.lower()

    return any(word in lowered for word in BAD_LOCATION_WORDS)


def verify_german_location_with_google(candidate):
    if not candidate or looks_like_bad_location(candidate):
        return ""

    original_candidate = candidate
    candidate_lower = candidate.lower()

    api_key = config("GOOGLE_MAPS_SERVER_KEY", default="")

    if not api_key:
        return candidate

    has_postcode_input = bool(re.search(r"\b\d{5}\b", candidate))

    response = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={
            "address": f"{candidate}, Germany",
            "components": "country:DE",
            "language": "de",
            "key": api_key,
        },
        timeout=8,
    )

    data = response.json()

    if data.get("status") != "OK":
        return ""

    for result in data.get("results", []):
        components = result.get("address_components", [])

        postcode = ""
        locality = ""
        country = ""

        for component in components:
            types = component.get("types", [])
            long_name = component.get("long_name", "")

            if "postal_code" in types and re.fullmatch(r"\d{5}", long_name):
                postcode = long_name

            if any(
                location_type in types
                for location_type in (
                    "locality",
                    "postal_town",
                    "administrative_area_level_3",
                    "administrative_area_level_2",
                    "sublocality",
                )
            ):
                if not locality:
                    locality = long_name

            if "country" in types:
                country = long_name

        if not locality or not country:
            continue

        # Critical guard:
        # If the input did not contain a postcode, the returned city must
        # appear in the original candidate. This blocks KNDS -> Kleve.
        if not has_postcode_input:
            locality_lower = locality.lower()

            if locality_lower not in candidate_lower:
                continue

        if postcode and locality and country:
            return f"{postcode} {locality}, {country}"

        return f"{locality}, {country}"

    return ""

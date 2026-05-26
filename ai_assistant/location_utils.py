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
    """
    Verify and normalize German locations using Google Geocoding.

    Examples:
    Verl -> 33415 Verl, Deutschland
    Frankfurt am Main -> 60311 Frankfurt am Main, Deutschland
    """

    if not candidate or looks_like_bad_location(candidate):
        return ""

    api_key = config("GOOGLE_MAPS_SERVER_KEY", default="")

    # Fallback if API key missing
    if not api_key:
        return candidate

    response = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={
            # Add Germany context for city-only lookups
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

            if "postal_code" in types:
                postcode = component.get("long_name", "")

            # locality OR postal_town
            if "locality" in types or "postal_town" in types:
                locality = component.get("long_name", "")

            if "country" in types:
                country = component.get("long_name", "")

        # Require ALL three
        if postcode and locality and country:

            return f"{postcode} {locality}, {country}"

    return ""

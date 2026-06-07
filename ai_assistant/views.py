import re
from multiprocessing import context
from django.contrib.auth.decorators import login_required
from django.http import QueryDict
from django.shortcuts import redirect
from django.shortcuts import render

from .services import extract_structured_job_data
from .services import extract_text_from_url


@login_required
def analyze_job_posting(request):
    context = {}

    if request.method == "POST":
        url = request.POST.get("job_url", "").strip()
        pasted_text = request.POST.get("pasted_job_text", "").strip()

        result = {
            "success": False,
            "text": "",
            "message": "",
        }

        if pasted_text:
            result = {
                "success": True,
                "text": pasted_text[:8000],
                "message": (
                    "Pasted job description used successfully."
                ),
            }

        elif url:
            result = extract_text_from_url(url)

        structured_data = {}

        if result["text"]:
            structured_data = extract_structured_job_data(
                result["text"],
                url=url,
            )

        json_ld_data = result.get("json_ld_data", {})

        for key, value in json_ld_data.items():
            if value and not structured_data.get(key):
                structured_data[key] = value

        missing_fields = []

        if not structured_data.get("company_name"):
            missing_fields.append("Company")

        if not structured_data.get("job_title"):
            missing_fields.append("Job title")

        if not structured_data.get("location"):
            missing_fields.append("Location")

        if not structured_data.get("contact_person"):
            missing_fields.append("Contact person")

        if not structured_data.get("contact_email"):
            missing_fields.append("Contact email")

        context["missing_fields"] = missing_fields

        context["result"] = result
        context["structured_data"] = structured_data
        context["job_url"] = url
        context["pasted_job_text"] = pasted_text

        google_maps_browser_key = ""

        try:
            google_maps_browser_key = __import__(
                "django.conf"
            ).conf.settings.GOOGLE_MAPS_BROWSER_KEY
        except AttributeError:
            google_maps_browser_key = ""

        home_location = ""

        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)

            if profile:
                home_location = (
                    profile.normalized_home_location
                    or profile.formatted_address
                    or ""
                )

        commute_routes = []

        if structured_data and home_location:
            locations = structured_data.get("locations") or []

            if not locations and structured_data.get("location"):
                locations = [structured_data["location"]]

            for location in locations:
                commute_routes.append(
                    {
                        "name": (
                            f"{structured_data.get('company_name', 'Job Location')}"
                            f" — {location}"
                        ),
                        "start": home_location,
                        "end": location,
                    }
                )

        context["commute_routes"] = commute_routes
        context["google_maps_browser_key"] = google_maps_browser_key

    return render(
        request,
        "ai_assistant/analyze_job_posting.html",
        context,
    )


@login_required
def use_extracted_job_data(request):
    def clean_param(value, max_length=None):
        value = re.sub(r"\s+", " ", value or "").strip()

        if max_length and len(value) > max_length:
            value = value[:max_length].rsplit(" ", 1)[0].strip()

        return value

    query_params = QueryDict(mutable=True)

    query_params["company_name"] = clean_param(
        request.POST.get("company_name", ""),
        255,
    )
    query_params["company_website"] = clean_param(
        request.POST.get("company_website", ""),
        500,
    )
    query_params["contact_person"] = clean_param(
        request.POST.get("contact_person", ""),
        255,
    )
    query_params["contact_email"] = clean_param(
        request.POST.get("contact_email", ""),
        255,
    )
    query_params["contact_phone"] = clean_param(
        request.POST.get("contact_phone", ""),
        100,
    )
    query_params["job_title"] = clean_param(
        request.POST.get("job_title", ""),
        255,
    )
    query_params["location"] = clean_param(
        request.POST.get("location", ""),
        255,
    )
    query_params["source_website"] = clean_param(
        request.POST.get("source_website", ""),
        100,
    )
    query_params["application_method"] = clean_param(
        request.POST.get("application_method", ""),
        50,
    )
    query_params["job_url"] = clean_param(
        request.POST.get("job_url", ""),
        1000,
    )
    query_params["job_description"] = request.POST.get(
        "job_description",
        "",
    )[:5000]

    return redirect(
        f"/en/applications/new/?{query_params.urlencode()}"
    )

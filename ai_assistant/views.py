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

    return render(
        request,
        "ai_assistant/analyze_job_posting.html",
        context,
    )


@login_required
def use_extracted_job_data(request):
    query_params = QueryDict(mutable=True)

    query_params["company_name"] = request.POST.get("company_name", "")
    query_params["company_website"] = request.POST.get("company_website", "")
    query_params["contact_person"] = request.POST.get("contact_person", "")
    query_params["contact_email"] = request.POST.get("contact_email", "")
    query_params["job_title"] = request.POST.get("job_title", "")
    query_params["location"] = request.POST.get("location", "")
    query_params["source_website"] = request.POST.get("source_website", "")
    query_params["application_method"] = request.POST.get(
        "application_method",
        "",
    )
    query_params["job_url"] = request.POST.get("job_url", "")
    query_params["job_description"] = request.POST.get(
        "job_description",
        "",
    )

    return redirect(
        f"/en/applications/new/?{query_params.urlencode()}"
    )

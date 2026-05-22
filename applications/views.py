from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render

from .forms import JobApplicationForm
from .models import Company
from .models import JobApplication


@login_required
def application_list(request):
    applications = JobApplication.objects.filter(
        user=request.user,
    ).select_related("company").order_by("-created_at")

    return render(
        request,
        "applications/application_list.html",
        {
            "applications": applications,
        },
    )


@login_required
def application_create(request):
    if request.method == "POST":
        form = JobApplicationForm(request.POST)

        if form.is_valid():
            company_name = form.cleaned_data["company_name"].strip()

            company, created = Company.objects.get_or_create(
                user=request.user,
                name=company_name,
                defaults={
                    "website": form.cleaned_data.get("company_website", ""),
                    "contact_person": form.cleaned_data.get(
                        "contact_person",
                        "",
                    ),
                    "contact_email": form.cleaned_data.get(
                        "contact_email",
                        "",
                    ),
                },
            )

            if not created:
                company.website = (
                    form.cleaned_data.get("company_website")
                    or company.website
                )
                company.contact_person = (
                    form.cleaned_data.get("contact_person")
                    or company.contact_person
                )
                company.contact_email = (
                    form.cleaned_data.get("contact_email")
                    or company.contact_email
                )
                company.save()

            application = form.save(commit=False)
            application.user = request.user
            application.company = company
            application.save()

            messages.success(
                request,
                "Application created successfully.",
            )

            return redirect("applications:application_list")

    else:
        form = JobApplicationForm()

    return render(
        request,
        "applications/application_form.html",
        {
            "form": form,
        },
    )

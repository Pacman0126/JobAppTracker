from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render

from documents.models import ApplicationDocument
from documents.models import UserDocument

from .forms import JobApplicationForm
from .models import Company
from .models import JobApplication
from .models import ApplicationDraft


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
    available_documents = UserDocument.objects.filter(
        user=request.user,
    ).order_by("title")

    if request.method == "POST":
        form = JobApplicationForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            company_name = form.cleaned_data["company_name"].strip()

            company, created = Company.objects.get_or_create(
                user=request.user,
                name=company_name,
                defaults={
                    "website": form.cleaned_data.get("company_website", ""),
                    "contact_person": form.cleaned_data.get("contact_person", ""),
                    "contact_email": form.cleaned_data.get("contact_email", ""),
                    "contact_phone": form.cleaned_data.get("contact_phone", ""),
                },
            )

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
            company.contact_phone = (
                form.cleaned_data.get("contact_phone")
                or company.contact_phone
            )
            company.save()

            application = form.save(commit=False)
            application.user = request.user
            application.company = company
            application.contact_person_snapshot = form.cleaned_data.get(
                "contact_person",
                "",
            )
            application.contact_email_snapshot = form.cleaned_data.get(
                "contact_email",
                "",
            )
            application.contact_phone_snapshot = form.cleaned_data.get(
                "contact_phone",
                "",
            )
            application.save()

            selected_document_ids = request.POST.getlist(
                "submitted_documents",
            )

            selected_documents = UserDocument.objects.filter(
                user=request.user,
                id__in=selected_document_ids,
            )

            for document in selected_documents:
                ApplicationDocument.objects.create(
                    application=application,
                    document=document,
                )

            messages.success(
                request,
                "Application created successfully.",
            )

            return redirect("applications:application_list")

        messages.error(
            request,
            "Application could not be saved. Please check the form errors.",
        )

    else:
        form = JobApplicationForm(
            initial=request.GET.dict(),
            user=request.user,
        )

    return render(
        request,
        "applications/application_form.html",
        {
            "form": form,
            "available_documents": available_documents,
        },
    )


@login_required
def application_detail(request, pk):
    application = JobApplication.objects.select_related(
        "company",
    ).get(
        pk=pk,
        user=request.user,
    )

    draft, _created = ApplicationDraft.objects.get_or_create(
        application=application,
    )

    return render(
        request,
        "applications/application_detail.html",
        {
            "application": application,
            "draft": draft,
        },
    )

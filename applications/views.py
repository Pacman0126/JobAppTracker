from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from ai_assistant.candidate_analysis import analyze_candidate_fit
# from ai_assistant.requirement_utils import compare_keyword_overlap
from documents.models import ApplicationDocument
from documents.models import UserDocument
from documents.text_utils import extract_document_text

from .forms import JobApplicationForm
from .models import ApplicationDraft
from .models import Company
from .models import JobApplication


def _build_match_notes(match_result):
    score = match_result.get("match_score", 0)

    strengths = (
        match_result.get("strengths")
        or match_result.get("matched_keywords", [])
    )

    gaps = (
        match_result.get("gaps")
        or match_result.get("missing_keywords", [])
    )

    recommendations = match_result.get(
        "recommendations",
        [],
    )

    summary = match_result.get(
        "summary",
        "",
    )

    strengths_text = (
        "\n".join(
            f"✓ {item}"
            for item in strengths[:15]
        )
        or "-"
    )

    gaps_text = (
        "\n".join(
            f"△ {item}"
            for item in gaps[:15]
        )
        or "-"
    )

    recommendation_text = (
        "\n".join(
            f"• {item}"
            for item in recommendations[:5]
        )
        or "-"
    )

    return f"""Candidate Match Score: {score}%

{summary}

Key Strengths
{strengths_text}

Potential Gaps
{gaps_text}

AI Recommendations
{recommendation_text}
"""


def _build_anschreiben(application, selected_cv, match_result):
    contact_person = application.contact_person_snapshot.strip()

    if contact_person:
        salutation = f"Sehr geehrte/r {contact_person},"
    else:
        salutation = "Sehr geehrte Damen und Herren,"

    strengths = (
        match_result.get("strengths")
        or match_result.get("matched_keywords", [])
    )

    gaps = (
        match_result.get("gaps")
        or match_result.get("missing_keywords", [])
    )

    score = match_result.get("match_score", 0)

    use_specific_matches = score >= 25 and len(strengths) >= 3
    use_specific_gaps = score >= 25 and len(gaps) >= 3

    strong_matches = (
        ", ".join(strengths[:8])
        if use_specific_matches
        else "meine Erfahrung in Softwareentwicklung, Projektarbeit und technischer Problemlösung"
    )

    development_terms = (
        ", ".join(gaps[:5])
        if use_specific_gaps
        else "die ausgeschriebenen fachlichen Anforderungen"
    )

    return f"""{salutation}

mit großem Interesse habe ich Ihre Ausschreibung für die Position als {application.job_title} bei {application.company.name} gelesen.

Besonders angesprochen hat mich die Verbindung zwischen den fachlichen Anforderungen der Stelle und meinem bisherigen Profil. Auf Grundlage meines ausgewählten Lebenslaufs „{selected_cv.title}“ ergibt sich eine erste Übereinstimmung von ca. {score}% zwischen meinem Profil und der Stellenbeschreibung.

Besonders relevant sind dabei folgende Überschneidungen: {strong_matches}. Diese Erfahrungen möchte ich gezielt in die ausgeschriebene Position einbringen und weiter ausbauen.

Darüber hinaus sehe ich in den genannten Anforderungen wie {development_terms} gute Ansatzpunkte, mich strukturiert einzuarbeiten und meine bisherigen Kenntnisse sinnvoll zu erweitern. Durch meine berufliche Erfahrung, meine Weiterbildung im Bereich Webentwicklung und meine projektorientierte Arbeitsweise bin ich es gewohnt, neue Themen schnell zu erfassen und zuverlässig in die Praxis umzusetzen.

Gerne überzeuge ich Sie in einem persönlichen Gespräch davon, dass ich sowohl fachlich als auch persönlich gut zu dieser Position passe.

Mit freundlichen Grüßen
"""


@login_required
def application_list(request):
    applications = JobApplication.objects.filter(
        user=request.user,
    ).select_related(
        "company",
        "draft",
    ).prefetch_related(
        "application_documents__document",
    ).order_by("-created_at")

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
    application = get_object_or_404(
        JobApplication.objects.select_related(
            "company",
        ).prefetch_related(
            "application_documents__document",
        ),
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


@login_required
def generate_anschreiben(request, pk):
    application = get_object_or_404(
        JobApplication.objects.select_related(
            "company",
        ),
        pk=pk,
        user=request.user,
    )

    if request.method != "POST":
        return redirect("applications:application_detail", pk=pk)

    selected_cv_id = request.POST.get("selected_cv")

    if not selected_cv_id:
        messages.error(
            request,
            "Please select exactly one CV before generating the Anschreiben.",
        )
        return redirect("applications:application_detail", pk=pk)

    selected_cv = UserDocument.objects.filter(
        id=selected_cv_id,
        user=request.user,
        document_type="cv",
    ).first()

    if not selected_cv:
        messages.error(
            request,
            "Selected CV could not be found.",
        )
        return redirect("applications:application_detail", pk=pk)

    cv_text = extract_document_text(selected_cv)
    job_description = application.job_description or ""

    match_result = analyze_candidate_fit(
        candidate_text=cv_text,
        job_text=job_description,
    )

    print("\nCV KEYWORDS")
    print(match_result.get("candidate_keywords"))

    print("\nJOB KEYWORDS")
    print(match_result.get("job_keywords"))

    print("\nMATCHED")
    print(match_result.get("matched_keywords"))

    print("\nMISSING")
    print(match_result.get("missing_keywords"))

    print("\nSCORE")
    print(match_result.get("match_score"))

    draft, _created = ApplicationDraft.objects.get_or_create(
        application=application,
    )

    draft.selected_cv = selected_cv
    draft.match_notes = _build_match_notes(match_result)
    draft.anschreiben_text = _build_anschreiben(
        application=application,
        selected_cv=selected_cv,
        match_result=match_result,
    )
    draft.save()

    messages.success(
        request,
        "Anschreiben draft generated with CV/job-description comparison.",
    )

    return redirect("applications:application_detail", pk=pk)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import JobApplication


@login_required
def application_list(request):
    applications = JobApplication.objects.filter(
        user=request.user
    ).select_related("company").order_by("-created_at")

    return render(
        request,
        "applications/application_list.html",
        {
            "applications": applications,
        },
    )

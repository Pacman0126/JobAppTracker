from django.contrib import admin

from .models import Company
from .models import JobApplication


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "contact_person",
        "contact_email",
        "user",
        "created_at",
    )
    search_fields = (
        "name",
        "contact_person",
        "contact_email",
    )
    list_filter = (
        "created_at",
    )


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "job_title",
        "company",
        "user",
        "status",
        "date_applied",
        "created_at",
    )
    search_fields = (
        "job_title",
        "company__name",
        "job_description",
    )
    list_filter = (
        "status",
        "date_applied",
        "created_at",
    )

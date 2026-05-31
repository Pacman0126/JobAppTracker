from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Company(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="companies",
    )
    name = models.CharField(max_length=255)
    website = models.URLField(blank=True)

    contact_person = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class JobApplication(models.Model):
    APPLICATION_METHOD_CHOICES = [
        ("job_board", "Job board portal"),
        ("employer_website", "Employer website"),
        ("email", "Email application"),
        ("recruiter", "Recruiter contact"),
        ("direct_contact", "Direct company contact"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("interview", "Interview"),
        ("rejected", "Rejected"),
        ("offer", "Offer"),
        ("archived", "Archived"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="applications",
    )

    job_title = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    source_website = models.CharField(max_length=255, blank=True)

    contact_person_snapshot = models.CharField(max_length=255, blank=True)
    contact_email_snapshot = models.EmailField(blank=True)
    contact_phone_snapshot = models.CharField(max_length=50, blank=True)

    application_method = models.CharField(
        max_length=30,
        choices=APPLICATION_METHOD_CHOICES,
        default="job_board",
    )

    job_url = models.URLField(blank=True)
    job_description = models.TextField()
    date_found = models.DateField(null=True, blank=True)
    date_applied = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def days_since_applied(self):
        if not self.date_applied:
            return None

        return (timezone.localdate() - self.date_applied).days

    def __str__(self):
        return f"{self.job_title} - {self.company.name}"

from django.contrib.auth.models import User
from django.db import models


class Company(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="companies",
    )

    name = models.CharField(
        max_length=255,
    )

    website = models.URLField(
        blank=True,
    )

    contact_person = models.CharField(
        max_length=255,
        blank=True,
    )

    contact_email = models.EmailField(
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.name


class JobApplication(models.Model):
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

    job_title = models.CharField(
        max_length=255,
    )

    location = models.CharField(
        max_length=255,
        blank=True,
    )

    source_website = models.CharField(
        max_length=255,
        blank=True,
    )

    job_url = models.URLField(
        blank=True,
    )

    job_description = models.TextField()

    date_found = models.DateField(
        null=True,
        blank=True,
    )

    date_applied = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.job_title} - {self.company.name}"

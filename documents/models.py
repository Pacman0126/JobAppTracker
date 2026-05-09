from django.contrib.auth.models import User
from django.db import models

from applications.models import JobApplication


def user_document_path(instance, filename):
    """
    Store uploaded files per user.

    Example:
    user_5/documents/resume.pdf
    """
    return (
        f"user_{instance.user.id}/documents/{filename}"
    )


class UserDocument(models.Model):
    DOCUMENT_TYPES = [
        ("cv", "CV / Lebenslauf"),
        ("cover_letter", "Cover Letter / Anschreiben"),
        ("certificate", "Certificate / Zertifikat"),
        ("zeugnis", "Zeugnis"),
        ("arbeitszeugnis", "Arbeitszeugnis"),
        ("reference", "Reference"),
        ("scan", "Scanned Document"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    title = models.CharField(
        max_length=255,
    )

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES,
    )

    file = models.FileField(
        upload_to=user_document_path,
    )

    original_filename = models.CharField(
        max_length=255,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.title


class ApplicationDocument(models.Model):
    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="application_documents",
    )

    document = models.ForeignKey(
        UserDocument,
        on_delete=models.CASCADE,
        related_name="application_links",
    )

    purpose = models.CharField(
        max_length=100,
        blank=True,
    )

    attached_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.document.title} -> "
            f"{self.application.job_title}"
        )

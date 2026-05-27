from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    full_name = models.CharField(
        max_length=255,
        blank=True,
    )

    email_contact = models.EmailField(
        blank=True,
    )

    phone_contact = models.CharField(
        max_length=50,
        blank=True,
    )

    street_address = models.CharField(
        max_length=255,
        blank=True,
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        default="Deutschland",
        blank=True,
    )

    home_location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Example: 95448 Bayreuth, Deutschland",
    )

    normalized_home_location = models.CharField(
        max_length=255,
        blank=True,
    )

    applicant_summary = models.TextField(
        blank=True,
        help_text=(
            "Short reusable profile summary for Anschreiben generation."
        ),
    )

    key_skills = models.TextField(
        blank=True,
        help_text=(
            "Reusable skills, technologies, languages, and strengths."
        ),
    )

    preferred_language = models.CharField(
        max_length=10,
        choices=[
            ("de", "Deutsch"),
            ("en", "English"),
        ],
        default="de",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Profile for {self.user.username}"

    @property
    def formatted_address(self):
        parts = [
            self.street_address,
            " ".join(
                part for part in [self.postal_code, self.city] if part
            ),
            self.country,
        ]

        return ", ".join(part for part in parts if part)

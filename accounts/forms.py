from django import forms

from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile

        fields = [
            "full_name",
            "email_contact",
            "phone_contact",
            "street_address",
            "postal_code",
            "city",
            "country",
            "home_location",
            "applicant_summary",
            "key_skills",
            "preferred_language",
        ]

        widgets = {
            "applicant_summary": forms.Textarea(attrs={"rows": 4}),
            "key_skills": forms.Textarea(attrs={"rows": 4}),
        }

from django import forms

from documents.models import UserDocument

from .models import JobApplication


class JobApplicationForm(forms.ModelForm):
    company_name = forms.CharField(max_length=255, label="Company name")
    company_website = forms.URLField(required=False, label="Company website")
    contact_person = forms.CharField(
        max_length=255, required=False, label="Contact person")
    contact_email = forms.EmailField(required=False, label="Contact email")

    submitted_documents = forms.ModelMultipleChoiceField(
        queryset=UserDocument.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Documents submitted with this application",
    )

    class Meta:
        model = JobApplication
        fields = [
            "company_name",
            "company_website",
            "contact_person",
            "contact_email",
            "job_title",
            "location",
            "source_website",
            "application_method",
            "job_url",
            "job_description",
            "date_found",
            "date_applied",
            "status",
            "notes",
            "submitted_documents",
        ]

        widgets = {
            "job_description": forms.Textarea(attrs={"rows": 8}),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "date_found": forms.DateInput(attrs={"type": "date"}),
            "date_applied": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields["submitted_documents"].queryset = (
                UserDocument.objects.filter(user=user).order_by(
                    "document_type", "title")
            )

from django.urls import path

from . import views


app_name = "ai_assistant"

urlpatterns = [
    path(
        "analyze/",
        views.analyze_job_posting,
        name="analyze_job_posting",
    ),
    path(
        "use-extracted-data/",
        views.use_extracted_job_data,
        name="use_extracted_job_data",
    ),
]

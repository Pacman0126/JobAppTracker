from django.urls import path

from . import views


app_name = "applications"

urlpatterns = [
    path("", views.application_list, name="application_list"),
]

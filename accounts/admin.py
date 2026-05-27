from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "email_contact",
        "phone_contact",
        "normalized_home_location",
        "updated_at",
    )

    search_fields = (
        "user__username",
        "full_name",
        "email_contact",
        "city",
    )

from django.contrib import admin

from .models import ApplicationDocument
from .models import UserDocument


@admin.register(UserDocument)
class UserDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "document_type",
        "user",
        "uploaded_at",
    )

    search_fields = (
        "title",
        "original_filename",
    )

    list_filter = (
        "document_type",
        "uploaded_at",
    )


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "document",
        "purpose",
        "attached_at",
    )

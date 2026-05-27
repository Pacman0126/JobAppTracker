"""
URL configuration for BewerbungsManager project.
"""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("core.urls")),
    path("applications/", include("applications.urls")),
    path("vault/", include("documents.urls")),
    path("ai/", include("ai_assistant.urls")),
    path("accounts/", include("accounts.urls")),


)


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.BASE_DIR / "static",
    )

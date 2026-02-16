"""URL configuration for the construction management example project."""
from django.contrib import admin
from django.urls import include, path
from onboarding.views import onboarding_settings
from platform_core.views import subcontractor_dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("stratagem/", include("django_stratagem.drf.urls")),
    path("", subcontractor_dashboard, name="dashboard"),
    path("onboarding/settings/", onboarding_settings, name="onboarding-settings"),
]

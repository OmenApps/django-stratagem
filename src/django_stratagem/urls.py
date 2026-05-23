from django.urls import path

from .inspector import registry_inspector

app_name = "django_stratagem"

urlpatterns = [
    path("inspector/", registry_inspector, name="registry-inspector"),
]

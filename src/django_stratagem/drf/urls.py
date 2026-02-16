from django.urls import path

from .views import RegistryChoicesAPIView, RegistryHierarchyAPIView

urlpatterns = [
    path("api/registry/choices/", RegistryChoicesAPIView.as_view(), name="registry-choices-api"),
    path("api/registry/hierarchy/", RegistryHierarchyAPIView.as_view(), name="registry-hierarchy-api"),
]

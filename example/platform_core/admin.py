# platform_core/admin.py
from django.contrib import admin

from django_stratagem.admin import ContextAwareRegistryAdmin, RegistryFieldListFilter
from platform_core.models import Employee, Firm, Subcontractor, SubcontractorEmployee


@admin.register(Firm)
class FirmAdmin(ContextAwareRegistryAdmin):
    list_display = ["name", "region", "plan", "compliance_strategy"]
    list_filter = [
        "region",
        "plan",
        ("compliance_strategy", RegistryFieldListFilter),
    ]


@admin.register(Subcontractor)
class SubcontractorAdmin(admin.ModelAdmin):
    list_display = ["name", "firm", "trade", "is_active"]
    list_filter = ["firm", "is_active"]


@admin.register(Employee)
class EmployeeAdmin(ContextAwareRegistryAdmin):
    list_display = ["user", "firm", "role", "onboarding_preference"]
    list_filter = [
        "firm",
        "role",
        ("onboarding_preference", RegistryFieldListFilter),
    ]


@admin.register(SubcontractorEmployee)
class SubcontractorEmployeeAdmin(admin.ModelAdmin):
    list_display = ["user", "subcontractor", "role"]
    list_filter = ["subcontractor", "role"]

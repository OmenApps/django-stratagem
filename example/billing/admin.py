# billing/admin.py
from django.contrib import admin

from billing.models import BillingConfig
from django_stratagem.admin import HierarchicalRegistryAdmin


@admin.register(BillingConfig)
class BillingConfigAdmin(HierarchicalRegistryAdmin):
    list_display = ["firm", "billing_model", "invoicing_strategy"]

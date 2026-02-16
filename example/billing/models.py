# billing/models.py
from django.db import models
from platform_core.models import Firm

from billing.registry import BillingModelRegistry, InvoicingStrategyRegistry
from django_stratagem import HierarchicalRegistryField


class BillingConfig(models.Model):
    firm = models.OneToOneField(Firm, on_delete=models.CASCADE, related_name="billing_config")
    billing_model = BillingModelRegistry.choices_field(blank=True, default="")
    invoicing_strategy = HierarchicalRegistryField(
        registry=InvoicingStrategyRegistry,
        parent_field="billing_model",
        blank=True,
        default="",
    )

    def __str__(self):
        return f"Billing config for {self.firm.name}"

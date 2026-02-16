# billing/forms.py
from django import forms

from billing.registry import BillingModelRegistry, InvoicingStrategyRegistry
from django_stratagem import (
    HierarchicalFormMixin,
    HierarchicalRegistryFormField,
    RegistryFormField,
)


class BillingConfigForm(HierarchicalFormMixin, forms.Form):
    billing_model = RegistryFormField(registry=BillingModelRegistry)
    invoicing_strategy = HierarchicalRegistryFormField(
        registry=InvoicingStrategyRegistry,
        parent_field="billing_model",
    )

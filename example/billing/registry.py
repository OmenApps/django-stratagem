# billing/registry.py
from django_stratagem import HierarchicalInterface, HierarchicalRegistry, Interface, Registry


class BillingModelRegistry(Registry):
    implementations_module = "billing_models"


class BillingModelInterface(Interface):
    registry = BillingModelRegistry

    def calculate_total(self, line_items):
        raise NotImplementedError


class InvoicingStrategyRegistry(HierarchicalRegistry):
    implementations_module = "invoicing_strategies"
    parent_registry = BillingModelRegistry


class InvoicingStrategyInterface(HierarchicalInterface):
    registry = InvoicingStrategyRegistry

    def generate_invoice(self, firm, period):
        raise NotImplementedError

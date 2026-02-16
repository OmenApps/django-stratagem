# billing/invoicing_strategies.py
from billing.registry import InvoicingStrategyInterface


class HourlyInvoicing(InvoicingStrategyInterface):
    slug = "hourly"
    description = "Invoice per hour worked"
    parent_slug = "time_and_materials"

    def generate_invoice(self, firm, period):
        return {"type": "hourly", "firm": firm.name, "period": str(period)}


class WeeklyInvoicing(InvoicingStrategyInterface):
    slug = "weekly"
    description = "Weekly consolidated invoice"
    parent_slug = "time_and_materials"

    def generate_invoice(self, firm, period):
        return {"type": "weekly", "firm": firm.name, "period": str(period)}


class MilestoneInvoicing(InvoicingStrategyInterface):
    slug = "milestone"
    description = "Invoice on milestone completion"
    parent_slug = "fixed_price"

    def generate_invoice(self, firm, period):
        return {"type": "milestone", "firm": firm.name, "period": str(period)}


class CompletionInvoicing(InvoicingStrategyInterface):
    slug = "completion"
    description = "Invoice on project completion"
    parent_slug = "fixed_price"

    def generate_invoice(self, firm, period):
        return {"type": "completion", "firm": firm.name, "period": str(period)}


class OpenBookInvoicing(InvoicingStrategyInterface):
    slug = "open_book"
    description = "Transparent cost breakdown with markup"
    parent_slug = "cost_plus"

    def generate_invoice(self, firm, period):
        return {"type": "open_book", "firm": firm.name, "period": str(period)}


class MonthlyReconciliation(InvoicingStrategyInterface):
    slug = "monthly_reconciliation"
    description = "Monthly cost reconciliation and settlement"
    parent_slug = "cost_plus"

    def generate_invoice(self, firm, period):
        return {"type": "monthly_reconciliation", "firm": firm.name, "period": str(period)}

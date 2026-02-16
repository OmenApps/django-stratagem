# billing/billing_models.py
from billing.registry import BillingModelInterface


class TimeAndMaterials(BillingModelInterface):
    slug = "time_and_materials"
    description = "Bill for actual hours and materials used"
    priority = 10

    def calculate_total(self, line_items):
        return sum(item["hours"] * item["rate"] + item.get("materials", 0) for item in line_items)


class FixedPrice(BillingModelInterface):
    slug = "fixed_price"
    description = "Bill a pre-agreed fixed amount per milestone"
    priority = 20

    def calculate_total(self, line_items):
        return sum(item["amount"] for item in line_items)


class CostPlus(BillingModelInterface):
    slug = "cost_plus"
    description = "Bill actual costs plus a percentage markup"
    priority = 30

    def calculate_total(self, line_items):
        base = sum(item["cost"] for item in line_items)
        markup = sum(item["cost"] * item.get("markup_pct", 0.15) for item in line_items)
        return base + markup

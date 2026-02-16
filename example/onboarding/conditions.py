# onboarding/conditions.py
from django_stratagem import Condition


class PlanCondition(Condition):
    """Check that the firm's plan is in the allowed list."""

    def __init__(self, allowed_plans):
        self.allowed_plans = allowed_plans

    def is_met(self, context):
        firm = context.get("firm")
        if not firm:
            return False
        return firm.plan in self.allowed_plans

    def explain(self):
        return f"Firm plan must be one of: {', '.join(self.allowed_plans)}"

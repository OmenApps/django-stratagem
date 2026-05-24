"""Concrete payment gateways for the payments example."""

from .registry import PaymentGateway


class StripeGateway(PaymentGateway):
    slug = "stripe"
    description = "Charge via Stripe"
    priority = 10

    def charge(self, amount_cents: int) -> str:
        return f"stripe:{amount_cents}"


class PaypalGateway(PaymentGateway):
    slug = "paypal"
    description = "Charge via PayPal"
    priority = 20

    def charge(self, amount_cents: int) -> str:
        return f"paypal:{amount_cents}"

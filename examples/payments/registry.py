"""A registry of payment gateways, one chosen per merchant."""

from django_stratagem.interfaces import Interface
from django_stratagem.registry import Registry


class PaymentGatewayRegistry(Registry):
    """Registry of payment gateways a merchant can select."""

    implementations_module = "gateways"


class PaymentGateway(Interface):
    """Base interface for a payment gateway."""

    registry = PaymentGatewayRegistry

    def charge(self, amount_cents: int) -> str:
        """Charge ``amount_cents`` and return a short receipt string."""
        raise NotImplementedError

# billing/signals.py
from django.dispatch import receiver

from django_stratagem.signals import implementation_registered, implementation_unregistered


@receiver(implementation_registered)
@receiver(implementation_unregistered)
def invalidate_billing_cache(sender, **kwargs):
    """Clear billing caches when any billing registry changes."""
    from billing.registry import BillingModelRegistry, InvoicingStrategyRegistry

    if sender in (BillingModelRegistry, InvoicingStrategyRegistry):
        from django.core.cache import cache

        cache.delete("billing:choices")
        cache.delete("billing:hierarchy_map")

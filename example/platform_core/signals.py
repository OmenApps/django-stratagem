# platform_core/signals.py
import logging

from django.dispatch import receiver

from django_stratagem.signals import implementation_registered, registry_reloaded

logger = logging.getLogger("platform_core")


@receiver(implementation_registered)
def notify_firms_of_new_option(sender, registry, implementation, **kwargs):
    """Log when a new compliance option becomes available."""
    from compliance.registry import ComplianceRegistry

    if registry is ComplianceRegistry:
        logger.info(
            "New compliance option available: %s - %s",
            implementation.slug,
            implementation.description,
        )


@receiver(registry_reloaded)
def warm_caches(sender, registry, **kwargs):
    """Pre-populate caches after a registry reload."""
    registry.get_choices()
    registry.get_items()

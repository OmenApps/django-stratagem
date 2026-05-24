"""A registry of notification channels.

This example shows a registry where some channels are conditionally
available (the webhook channel requires a setting to be enabled).
"""

from django_stratagem.interfaces import ConditionalInterface
from django_stratagem.registry import Registry


class NotificationRegistry(Registry):
    """Registry of notification channels a project can send through."""

    implementations_module = "channels"


class NotificationChannel(ConditionalInterface):
    """Base interface for a notification channel."""

    registry = NotificationRegistry

    def send(self, message: str) -> str:
        """Send ``message`` and return a short status string."""
        raise NotImplementedError

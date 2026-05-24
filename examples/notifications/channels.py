"""Concrete notification channels for the notifications example."""

from django_stratagem.conditions import SettingCondition

from .registry import NotificationChannel


class EmailChannel(NotificationChannel):
    slug = "email"
    description = "Send notifications by email"
    priority = 10

    def send(self, message: str) -> str:
        return f"email:{message}"


class SmsChannel(NotificationChannel):
    slug = "sms"
    description = "Send notifications by SMS"
    priority = 20

    def send(self, message: str) -> str:
        return f"sms:{message}"


class WebhookChannel(NotificationChannel):
    slug = "webhook"
    description = "POST notifications to a webhook (must be enabled in settings)"
    priority = 30
    condition = SettingCondition("NOTIFICATIONS_WEBHOOK_ENABLED", True)

    def send(self, message: str) -> str:
        return f"webhook:{message}"

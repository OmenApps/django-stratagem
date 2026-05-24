import pytest
from django.test import override_settings


@pytest.fixture
def notification_registry():
    from examples.notifications.registry import NotificationRegistry

    original = dict(NotificationRegistry.implementations)
    NotificationRegistry.discover_implementations()
    yield NotificationRegistry
    NotificationRegistry.implementations.clear()
    NotificationRegistry.implementations.update(original)
    NotificationRegistry.clear_cache()


def test_notification_channels_registered(notification_registry):
    slugs = set(notification_registry.implementations)
    assert {"email", "sms", "webhook"} <= slugs


def test_notification_channel_sends(notification_registry):
    channel = notification_registry.get(slug="email")
    assert channel.send("hi") == "email:hi"


def test_webhook_hidden_when_setting_disabled(notification_registry):
    with override_settings(NOTIFICATIONS_WEBHOOK_ENABLED=False):
        available = notification_registry.get_available_implementations({})
    assert "webhook" not in available
    assert "email" in available


def test_webhook_visible_when_setting_enabled(notification_registry):
    with override_settings(NOTIFICATIONS_WEBHOOK_ENABLED=True):
        available = notification_registry.get_available_implementations({})
    assert "webhook" in available

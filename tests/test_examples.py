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


@pytest.fixture
def payment_registry():
    from examples.payments.registry import PaymentGatewayRegistry

    original = dict(PaymentGatewayRegistry.implementations)
    PaymentGatewayRegistry.discover_implementations()
    yield PaymentGatewayRegistry
    PaymentGatewayRegistry.implementations.clear()
    PaymentGatewayRegistry.implementations.update(original)
    PaymentGatewayRegistry.clear_cache()


def test_payment_gateways_registered(payment_registry):
    assert {"stripe", "paypal"} <= set(payment_registry.implementations)


@pytest.mark.django_db
def test_merchant_persists_selected_gateway(payment_registry):
    from examples.payments.gateways import StripeGateway
    from examples.payments.models import Merchant

    merchant = Merchant.objects.create(name="Acme", gateway="stripe")
    merchant.refresh_from_db()
    assert merchant.gateway is StripeGateway
    assert merchant.gateway().charge(500) == "stripe:500"

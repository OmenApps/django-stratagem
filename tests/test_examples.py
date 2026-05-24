import pytest
from django.test import override_settings


@pytest.fixture
def notification_registry():
    from examples.notifications.registry import NotificationRegistry

    from django_stratagem.testing import isolate_registries

    with isolate_registries():
        NotificationRegistry.discover_implementations()
        yield NotificationRegistry


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

    from django_stratagem.testing import isolate_registries

    with isolate_registries():
        PaymentGatewayRegistry.discover_implementations()
        yield PaymentGatewayRegistry


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


@pytest.fixture
def export_registry():
    from examples.exports.registry import ExportFormatRegistry

    from django_stratagem.testing import isolate_registries

    with isolate_registries():
        ExportFormatRegistry.discover_implementations()
        yield ExportFormatRegistry


def test_export_formats_registered(export_registry):
    assert {"csv", "json"} <= set(export_registry.implementations)


def test_export_format_renders(export_registry):
    json_format = export_registry.get(slug="json")
    assert json_format.render([{"a": 1}]) == b'[{"a": 1}]'


def test_export_serializer_accepts_valid_slug(export_registry):
    pytest.importorskip("rest_framework")
    from examples.exports.serializers import ExportRequestSerializer

    serializer = ExportRequestSerializer(data={"format": "csv", "row_count": 3})
    assert serializer.is_valid(), serializer.errors


def test_export_serializer_rejects_unknown_slug(export_registry):
    pytest.importorskip("rest_framework")
    from examples.exports.serializers import ExportRequestSerializer

    serializer = ExportRequestSerializer(data={"format": "nope"})
    assert not serializer.is_valid()
    assert "format" in serializer.errors

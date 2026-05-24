def test_to_snake_converts_camel_case():
    from django_stratagem.management.commands.startregistry import to_snake

    assert to_snake("NotificationChannel") == "notification_channel"
    assert to_snake("Payment") == "payment"


def test_render_registry_module_contains_classes():
    from django_stratagem.management.commands.startregistry import render_registry_module

    src = render_registry_module("Notification", "notification_implementations")
    assert "class NotificationRegistry(Registry):" in src
    assert "class NotificationInterface(Interface):" in src
    assert 'implementations_module = "notification_implementations"' in src


def test_render_implementations_module_defines_default_impl():
    from django_stratagem.management.commands.startregistry import render_implementations_module

    src = render_implementations_module("Notification")
    assert "from .registry import NotificationInterface" in src
    assert "class DefaultNotification(NotificationInterface):" in src
    assert 'slug = "default"' in src

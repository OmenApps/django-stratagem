import pytest


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


def test_write_registry_files_creates_both_files(tmp_path):
    from django_stratagem.management.commands.startregistry import write_registry_files

    written = write_registry_files(tmp_path, "Notification", "notification_implementations")

    registry_file = tmp_path / "registry.py"
    impl_file = tmp_path / "notification_implementations.py"
    assert registry_file.exists()
    assert impl_file.exists()
    assert set(written) == {registry_file, impl_file}
    assert "NotificationRegistry" in registry_file.read_text()


def test_write_registry_files_refuses_to_clobber(tmp_path):
    from django.core.management.base import CommandError

    from django_stratagem.management.commands.startregistry import write_registry_files

    write_registry_files(tmp_path, "Notification", "notification_implementations")
    with pytest.raises(CommandError):
        write_registry_files(tmp_path, "Notification", "notification_implementations")


def test_write_registry_files_force_overwrites(tmp_path):
    from django_stratagem.management.commands.startregistry import write_registry_files

    write_registry_files(tmp_path, "Notification", "notification_implementations")
    # Should not raise with force=True.
    write_registry_files(tmp_path, "Notification", "notification_implementations", force=True)

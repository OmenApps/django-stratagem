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


def test_command_writes_into_resolved_app_path(tmp_path, mocker):
    from django.core.management import call_command

    fake_config = mocker.Mock()
    fake_config.path = str(tmp_path)
    mocker.patch("django.apps.apps.get_app_config", return_value=fake_config)

    call_command("startregistry", "Notification", "--app", "anyapp")

    assert (tmp_path / "registry.py").exists()
    assert (tmp_path / "notification_implementations.py").exists()


def test_command_custom_module_name(tmp_path, mocker):
    from django.core.management import call_command

    fake_config = mocker.Mock()
    fake_config.path = str(tmp_path)
    mocker.patch("django.apps.apps.get_app_config", return_value=fake_config)

    call_command("startregistry", "Payment", "--app", "anyapp", "--module", "gateways")

    assert (tmp_path / "gateways.py").exists()
    assert "PaymentRegistry" in (tmp_path / "registry.py").read_text()


def test_command_errors_on_unknown_app(mocker):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    mocker.patch("django.apps.apps.get_app_config", side_effect=LookupError("nope"))

    with pytest.raises(CommandError):
        call_command("startregistry", "Notification", "--app", "missing")


def test_to_snake_pins_acronym_behavior():
    # The default --module name derives from to_snake(name), so pin the
    # consecutive-capitals behavior to catch accidental regex changes.
    from django_stratagem.management.commands.startregistry import to_snake

    assert to_snake("APIGateway") == "api_gateway"
    assert to_snake("HTTPSRequest") == "https_request"
    assert to_snake("HTTPServer") == "http_server"


def test_command_rejects_invalid_name(mocker):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    # get_app_config should never be reached; name validation fails first.
    mocker.patch("django.apps.apps.get_app_config", side_effect=AssertionError("should not be called"))

    with pytest.raises(CommandError):
        call_command("startregistry", "Not a valid name", "--app", "anyapp")


def test_command_rejects_path_traversal_module(tmp_path, mocker):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    fake_config = mocker.Mock()
    fake_config.path = str(tmp_path)
    mocker.patch("django.apps.apps.get_app_config", return_value=fake_config)

    with pytest.raises(CommandError):
        call_command("startregistry", "Notification", "--app", "anyapp", "--module", "../../evil")

    # Nothing should have been written outside the target directory.
    assert not (tmp_path.parent.parent / "evil.py").exists()


def test_command_rejects_dunder_module(tmp_path, mocker):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    fake_config = mocker.Mock()
    fake_config.path = str(tmp_path)
    mocker.patch("django.apps.apps.get_app_config", return_value=fake_config)

    # __init__ is a valid identifier but must be rejected: --force would clobber
    # the package's __init__.py.
    with pytest.raises(CommandError):
        call_command("startregistry", "Notification", "--app", "anyapp", "--module", "__init__")
    assert not (tmp_path / "__init__.py").exists()


def test_command_rejects_registry_module_collision(tmp_path, mocker):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    # Validation fires before the app is resolved, so get_app_config must not be reached.
    fake_config = mocker.Mock()
    fake_config.path = str(tmp_path)
    get_app_config = mocker.patch("django.apps.apps.get_app_config", return_value=fake_config)

    with pytest.raises(CommandError):
        call_command("startregistry", "Notification", "--app", "anyapp", "--module", "registry")

    get_app_config.assert_not_called()
    assert not (tmp_path / "registry.py").exists()


def test_command_rejects_non_ascii_name(mocker):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    mocker.patch("django.apps.apps.get_app_config", side_effect=AssertionError("should not be called"))

    # "Café" is a valid Python identifier but not ASCII; reject it.
    with pytest.raises(CommandError):
        call_command("startregistry", "Café", "--app", "anyapp")


def test_command_force_overwrites_via_cli(tmp_path, mocker):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    fake_config = mocker.Mock()
    fake_config.path = str(tmp_path)
    mocker.patch("django.apps.apps.get_app_config", return_value=fake_config)

    call_command("startregistry", "Notification", "--app", "anyapp")
    with pytest.raises(CommandError):
        call_command("startregistry", "Notification", "--app", "anyapp")
    # With --force the second run succeeds.
    call_command("startregistry", "Notification", "--app", "anyapp", "--force")


def test_command_default_module_name(tmp_path, mocker):
    from django.core.management import call_command

    fake_config = mocker.Mock()
    fake_config.path = str(tmp_path)
    mocker.patch("django.apps.apps.get_app_config", return_value=fake_config)

    call_command("startregistry", "Notification", "--app", "anyapp")

    assert (tmp_path / "notification_implementations.py").exists()


def test_generated_code_imports_and_autoregisters(tmp_path, monkeypatch):
    """The generated registry/implementations modules import and auto-register.

    The command tests mock the app path and only check rendered strings, so this
    test guards that the actual generated source is valid Python that wires up
    auto-registration end to end. ``isolate_registries`` rolls back the global
    registry list so the generated ``GreetingRegistry`` does not leak.
    """
    import importlib
    import sys

    from django_stratagem.management.commands.startregistry import write_registry_files
    from django_stratagem.registry import Registry
    from django_stratagem.testing import isolate_registries

    pkg = tmp_path / "generated_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    write_registry_files(pkg, "Greeting", "greeting_implementations")

    monkeypatch.syspath_prepend(str(tmp_path))
    for mod in [m for m in sys.modules if m.startswith("generated_pkg")]:
        del sys.modules[mod]

    try:
        with isolate_registries():
            registry_mod = importlib.import_module("generated_pkg.registry")
            impl_mod = importlib.import_module("generated_pkg.greeting_implementations")

            assert issubclass(registry_mod.GreetingRegistry, Registry)
            assert registry_mod.GreetingRegistry.implementations_module == "greeting_implementations"
            assert registry_mod.GreetingInterface.registry is registry_mod.GreetingRegistry
            assert "default" in registry_mod.GreetingRegistry.implementations
            assert impl_mod.DefaultGreeting().run() == "default"
    finally:
        for mod in [m for m in sys.modules if m.startswith("generated_pkg")]:
            del sys.modules[mod]


def test_write_registry_files_rolls_back_on_write_failure(tmp_path, mocker):
    from pathlib import Path

    from django.core.management.base import CommandError

    from django_stratagem.management.commands.startregistry import write_registry_files

    # A pre-existing registry.py that --force will overwrite; its content must
    # be restored if a later write fails mid-operation.
    registry_file = tmp_path / "registry.py"
    registry_file.write_text("ORIGINAL")

    real_write = Path.write_text
    calls = {"n": 0}

    def flaky_write(self, data, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:  # fail on the implementations-module write
            raise OSError("disk full")
        return real_write(self, data, *args, **kwargs)

    mocker.patch("pathlib.Path.write_text", flaky_write)

    with pytest.raises(CommandError):
        write_registry_files(tmp_path, "Notification", "notification_implementations", force=True)

    # registry.py restored to its original content; the impl module not left behind.
    assert registry_file.read_text() == "ORIGINAL"
    assert not (tmp_path / "notification_implementations.py").exists()

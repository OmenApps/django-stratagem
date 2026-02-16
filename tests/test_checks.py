"""Tests for django_stratagem system checks."""

from __future__ import annotations

from unittest.mock import patch

from django_stratagem.checks import check_registries
from django_stratagem.registry import HierarchicalRegistry, Registry, django_stratagem_registry


class TestCheckRegistries:
    """Tests for check_registries system check."""

    def test_valid_config_no_errors(self):
        """Test that valid configuration produces no errors."""
        errors = check_registries(app_configs=None)
        # The test fixtures have valid registries, so no E001 errors expected for them
        e001_errors = [e for e in errors if e.id == "django_stratagem.E001"]
        assert len(e001_errors) == 0

    def test_e001_invalid_implementations_module(self):
        """Test E001 fires for registry with non-string implementations_module."""

        class BadRegistry(Registry):
            implementations_module = "valid_module"

        # Override to invalid value after registration
        BadRegistry.implementations_module = 123

        errors = check_registries(app_configs=None)
        e001_errors = [e for e in errors if e.id == "django_stratagem.E001"]
        assert any("BadRegistry" in e.msg for e in e001_errors)

    def test_e001_none_implementations_module(self):
        """Test E001 fires for registry with None implementations_module."""

        class NoneModuleRegistry(Registry):
            implementations_module = "placeholder"

        NoneModuleRegistry.implementations_module = None

        errors = check_registries(app_configs=None)
        e001_errors = [e for e in errors if e.id == "django_stratagem.E001"]
        assert any("NoneModuleRegistry" in e.msg for e in e001_errors)

    def test_e001_empty_implementations_module(self):
        """Test E001 fires for registry with empty string implementations_module."""

        class EmptyModuleRegistry(Registry):
            implementations_module = "placeholder"

        EmptyModuleRegistry.implementations_module = ""

        errors = check_registries(app_configs=None)
        e001_errors = [e for e in errors if e.id == "django_stratagem.E001"]
        assert any("EmptyModuleRegistry" in e.msg for e in e001_errors)

    def test_w001_orphaned_parent_registry(self):
        """Test W001 fires for hierarchical registry with parent not in global registry."""

        class OrphanParent(Registry):
            implementations_module = "orphan_parent_impls"

        class OrphanChild(HierarchicalRegistry):
            implementations_module = "orphan_child_impls"
            parent_registry = OrphanParent

        # Remove the parent from global registry to simulate orphan
        django_stratagem_registry.remove(OrphanParent)

        errors = check_registries(app_configs=None)
        w001_errors = [e for e in errors if e.id == "django_stratagem.W001"]
        assert any("OrphanChild" in e.msg for e in w001_errors)

    def test_e002_invalid_field_registry_type(self):
        """Test E002 fires for model field with invalid registry type."""
        from django_stratagem.fields import AbstractRegistryField

        fake_field_instance = object.__new__(AbstractRegistryField)
        fake_field_instance.registry = "not_a_registry_class"
        fake_field_instance.name = "bad_field"

        fake_model = type("FakeModel", (), {"__name__": "FakeModel"})
        fake_model._meta = type("Meta", (), {
            "get_fields": lambda self: [fake_field_instance],
            "app_label": "testapp",
            "model_name": "fakemodel",
        })()

        with patch("django.apps.apps.get_models", return_value=[fake_model]):
            errors = check_registries(app_configs=None)

        e002_errors = [e for e in errors if e.id == "django_stratagem.E002"]
        assert len(e002_errors) >= 1
        assert any("bad_field" in e.msg for e in e002_errors)

    def test_w002_unregistered_field_registry(self):
        """Test W002 fires for model field referencing unregistered registry."""
        from django_stratagem.fields import AbstractRegistryField

        class UnregisteredRegistry(Registry):
            implementations_module = "unreg_impls"

        # Remove from global registry
        django_stratagem_registry.remove(UnregisteredRegistry)

        fake_field_instance = object.__new__(AbstractRegistryField)
        fake_field_instance.registry = UnregisteredRegistry
        fake_field_instance.name = "orphan_field"

        fake_model = type("FakeModel2", (), {"__name__": "FakeModel2"})
        fake_model._meta = type("Meta", (), {
            "get_fields": lambda self: [fake_field_instance],
            "app_label": "testapp",
            "model_name": "fakemodel2",
        })()

        with patch("django.apps.apps.get_models", return_value=[fake_model]):
            errors = check_registries(app_configs=None)

        w002_errors = [e for e in errors if e.id == "django_stratagem.W002"]
        assert any("orphan_field" in e.msg for e in w002_errors)

    def test_multiple_errors(self):
        """Test that check returns multiple errors when multiple issues exist."""

        class Bad1(Registry):
            implementations_module = "placeholder"

        class Bad2(Registry):
            implementations_module = "placeholder2"

        Bad1.implementations_module = None
        Bad2.implementations_module = ""

        errors = check_registries(app_configs=None)
        e001_errors = [e for e in errors if e.id == "django_stratagem.E001"]
        bad_names = [e.msg for e in e001_errors]
        assert any("Bad1" in msg for msg in bad_names)
        assert any("Bad2" in msg for msg in bad_names)

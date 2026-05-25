import pytest
from django.db import models

from django_stratagem.fields import RegistryField
from django_stratagem.interfaces import Interface
from django_stratagem.registry import ImplementationNotFound, Registry
from tests.exporter_plugins.exporters import CsvExporter
from tests.exporters.models import ExportConfig
from tests.exporters.registry import ExporterRegistry


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="test",
        password="test",
    )


@pytest.mark.django_db
def test_get_items(register_test_implementations):
    expected = [("csv", CsvExporter)]
    assert ExporterRegistry.get_items() == expected


@pytest.mark.django_db
def test_get_choices(register_test_implementations):
    # Display name is derived from class name via camel_to_title, so "CsvExporter" -> "Csv Exporter"
    expected = [("csv", "Csv Exporter")]
    assert ExporterRegistry.get_choices() == expected


@pytest.mark.django_db
def test_get(register_test_implementations):
    assert isinstance(ExporterRegistry.get(slug="csv"), CsvExporter)


@pytest.mark.django_db
def test_choices_set_on_field(register_test_implementations):
    # Display name is derived from class name via camel_to_title, so "CsvExporter" -> "Csv Exporter"
    expected = [("csv", "Csv Exporter")]
    field = ExportConfig._meta.get_field("exporter_type")
    assert field.choices == expected


@pytest.mark.django_db
def test_non_registry_raises_value_error(register_test_implementations):
    with pytest.raises(ValueError):

        class Baz(models.Model):
            bad_field = RegistryField(registry="wrong", max_length=100)


@pytest.mark.django_db
def test_no_implementation_found(register_test_implementations):
    with pytest.raises(ImplementationNotFound):
        ExporterRegistry.get(slug="doesnotexist")


class TestGetOrDefault:
    """Tests for Registry.get_or_default() - untested public API."""

    def test_slug_found(self, test_strategy_registry):
        """get_or_default returns an instance when slug exists."""
        from tests.registries_fixtures import EmailStrategy

        result = test_strategy_registry.get_or_default(slug="email")
        assert result is not None
        assert isinstance(result, EmailStrategy)

    def test_fqn_found(self, test_strategy_registry):
        """get_or_default returns an instance when FQN is valid."""
        from tests.registries_fixtures import EmailStrategy

        result = test_strategy_registry.get_or_default(fully_qualified_name="tests.registries_fixtures.EmailStrategy")
        assert result is not None
        assert isinstance(result, EmailStrategy)

    def test_slug_not_found_falls_back(self, test_strategy_registry):
        """get_or_default falls back to default slug when primary slug is missing."""
        from tests.registries_fixtures import SMSStrategy

        result = test_strategy_registry.get_or_default(slug="nonexistent", default="sms")
        assert result is not None
        assert isinstance(result, SMSStrategy)

    def test_slug_not_found_no_default(self, test_strategy_registry):
        """get_or_default returns None when slug missing and no default."""
        result = test_strategy_registry.get_or_default(slug="nonexistent")
        assert result is None

    def test_neither_provided(self, test_strategy_registry):
        """get_or_default returns None when neither slug nor FQN is provided."""
        result = test_strategy_registry.get_or_default()
        assert result is None


class TestValidateImplementationStringInterface:
    """Tests for Registry.validate_implementation with string interface_class."""

    def test_resolves_string_interface_class(self):
        """Registry with string interface_class resolves it and validates subclasses."""

        class StringInterfaceRegistry(Registry):
            implementations_module = "test_string_interface"
            interface_class = "tests.registries_fixtures.TestStrategy"

        # A subclass of TestStrategy should register successfully
        from tests.registries_fixtures import TestStrategy

        class GoodImpl(TestStrategy):
            slug = "good_impl"
            registry = StringInterfaceRegistry

        assert "good_impl" in StringInterfaceRegistry.implementations

        # A non-subclass should be rejected
        class NotASubclass(Interface):
            slug = "bad_impl"

        with pytest.raises(TypeError, match="must inherit from"):
            StringInterfaceRegistry.register(NotASubclass)


class TestFriendlySlugErrors:
    """Slug-not-found errors include suggestions, available slugs, and a doc link."""

    def test_get_suggests_closest_slug(self, test_strategy_registry):
        with pytest.raises(ImplementationNotFound) as excinfo:
            test_strategy_registry.get(slug="emai")
        message = str(excinfo.value)
        assert "Did you mean 'email'?" in message
        assert "Available slugs: email, push, sms." in message
        assert "https://django-stratagem.readthedocs.io" in message

    def test_get_class_includes_available_slugs(self, test_strategy_registry):
        with pytest.raises(ImplementationNotFound) as excinfo:
            test_strategy_registry.get_class(slug="nope")
        assert "Available slugs: email, push, sms." in str(excinfo.value)

    def test_get_implementation_class_includes_available_slugs(self, test_strategy_registry):
        with pytest.raises(ImplementationNotFound) as excinfo:
            test_strategy_registry.get_implementation_class("nope")
        assert "Available slugs: email, push, sms." in str(excinfo.value)

    def test_get_implementation_meta_includes_available_slugs(self, test_strategy_registry):
        with pytest.raises(ImplementationNotFound) as excinfo:
            test_strategy_registry.get_implementation_meta("nope")
        assert "Available slugs: email, push, sms." in str(excinfo.value)

    def test_unregister_missing_slug_includes_available_slugs(self, test_strategy_registry):
        with pytest.raises(ImplementationNotFound) as excinfo:
            test_strategy_registry.unregister("nope")
        assert "Available slugs: email, push, sms." in str(excinfo.value)

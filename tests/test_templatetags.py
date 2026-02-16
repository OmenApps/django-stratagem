"""Tests for django_stratagem templatetags."""

from __future__ import annotations

from django_stratagem.registry import django_stratagem_registry
from django_stratagem.templatetags.stratagem import (
    display_name,
    get_choices,
    get_implementations,
    get_registries,
    is_available,
    registry_description,
    registry_icon,
)


class TestGetImplementationsTag:
    """Tests for get_implementations template tag."""

    def test_returns_all_implementations(self, test_registry):
        """Test returns dict of slug -> class for all implementations."""
        result = get_implementations(test_registry)
        assert "email" in result
        assert "sms" in result
        assert "push" in result

    def test_with_context_filters(self, conditional_registry, premium_user):
        """Test with context filters implementations by availability."""
        context = {"user": premium_user}
        result = get_implementations(conditional_registry, context=context)
        assert "premium_feature" in result
        assert "basic_feature" in result

    def test_with_context_excludes_unavailable(self, conditional_registry, basic_user):
        """Test with context excludes unavailable implementations."""
        context = {"user": basic_user}
        result = get_implementations(conditional_registry, context=context)
        assert "premium_feature" not in result
        assert "basic_feature" in result

    def test_empty_registry(self):
        """Test returns empty dict for registry with no implementations."""
        from django_stratagem.registry import Registry

        class EmptyRegistry(Registry):
            implementations_module = "empty_test_implementations"

        result = get_implementations(EmptyRegistry)
        assert result == {}


class TestGetChoicesTag:
    """Tests for get_choices template tag."""

    def test_returns_choices_list(self, test_registry):
        """Test returns list of (slug, label) tuples."""
        result = get_choices(test_registry)
        slugs = [slug for slug, _ in result]
        assert "email" in slugs
        assert "sms" in slugs
        assert "push" in slugs

    def test_with_context_filters(self, conditional_registry, basic_user):
        """Test with context filters choices by availability."""
        context = {"user": basic_user}
        result = get_choices(conditional_registry, context=context)
        slugs = [slug for slug, _ in result]
        assert "basic_feature" in slugs
        assert "premium_feature" not in slugs


class TestGetRegistriesTag:
    """Tests for get_registries template tag."""

    def test_returns_all_registries(self):
        """Test returns list containing registered registries."""
        result = get_registries()
        assert len(result) > 0

    def test_returns_list_type(self):
        """Test returns a list (not the global list object itself)."""
        result = get_registries()
        assert isinstance(result, list)
        # Should be a new list, not the global registry itself
        assert result is not django_stratagem_registry


class TestDisplayNameFilter:
    """Tests for display_name template filter."""

    def test_with_explicit_registry(self, test_registry, email_strategy):
        """Test with explicit registry calls get_display_name."""
        result = display_name(email_strategy, registry=test_registry)
        assert result == "Email Strategy"

    def test_auto_discovery_with_class(self, test_registry, email_strategy):
        """Test auto-discovers registry when given a class."""
        result = display_name(email_strategy)
        assert result == "Email Strategy"

    def test_auto_discovery_with_instance(self, test_registry, email_strategy):
        """Test auto-discovers registry when given an instance."""
        instance = email_strategy()
        result = display_name(instance)
        assert result == "Email Strategy"

    def test_fallback_to_class_name(self):
        """Test falls back to __name__ for unregistered class."""

        class UnregisteredClass:
            pass

        result = display_name(UnregisteredClass)
        assert result == "UnregisteredClass"

    def test_fallback_instance_class_name(self):
        """Test falls back to type().__name__ for unregistered instance."""

        class UnregisteredClass:
            pass

        result = display_name(UnregisteredClass())
        assert result == "UnregisteredClass"


class TestRegistryIconFilter:
    """Tests for registry_icon template filter."""

    def test_class_with_icon(self, email_strategy):
        """Test returns icon for a class with icon attribute."""
        result = registry_icon(email_strategy)
        assert result == "fa-solid fa-envelope"

    def test_class_without_icon(self):
        """Test returns empty string for a class without icon."""

        class NoIconClass:
            pass

        result = registry_icon(NoIconClass)
        assert result == ""

    def test_instance_with_icon(self, email_strategy):
        """Test returns icon for an instance whose class has icon."""
        instance = email_strategy()
        result = registry_icon(instance)
        assert result == "fa-solid fa-envelope"


class TestRegistryDescriptionFilter:
    """Tests for registry_description template filter."""

    def test_class_with_description(self, email_strategy):
        """Test returns description for a class with description attribute."""
        result = registry_description(email_strategy)
        assert result == "Send notifications via email"

    def test_class_without_description(self):
        """Test returns empty string for a class without description."""

        class NoDescClass:
            pass

        result = registry_description(NoDescClass)
        assert result == ""

    def test_instance_with_description(self, email_strategy):
        """Test returns description for an instance whose class has description."""
        instance = email_strategy()
        result = registry_description(instance)
        assert result == "Send notifications via email"


class TestIsAvailableFilter:
    """Tests for is_available template filter."""

    def test_with_available_method_true(self):
        """Test returns True when is_available returns True."""

        class AvailableImpl:
            @classmethod
            def is_available(cls, context):
                return True

        assert is_available(AvailableImpl) is True

    def test_with_available_method_false(self):
        """Test returns False when is_available returns False."""

        class UnavailableImpl:
            @classmethod
            def is_available(cls, context):
                return False

        assert is_available(UnavailableImpl) is False

    def test_without_available_method(self):
        """Test returns True when no is_available method exists."""

        class SimpleImpl:
            pass

        assert is_available(SimpleImpl) is True

    def test_with_context(self):
        """Test passes context through to is_available."""
        received_context = {}

        class ContextAwareImpl:
            @classmethod
            def is_available(cls, context):
                received_context.update(context)
                return True

        is_available(ContextAwareImpl, context={"user": "test"})
        assert received_context == {"user": "test"}

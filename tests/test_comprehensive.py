"""Tests for conditions, signals, utils, and edge cases."""

from unittest.mock import patch

import pytest
from django.core.cache import cache

from django_stratagem.conditions import (
    AllConditions,
    AnyCondition,
    CallableCondition,
    NotCondition,
    PermissionCondition,
)
from django_stratagem.exceptions import ImplementationNotFound
from django_stratagem.interfaces import HierarchicalInterface, Interface
from django_stratagem.registry import Registry, discover_registries
from django_stratagem.signals import implementation_registered, implementation_unregistered, registry_reloaded
from django_stratagem.utils import get_class, get_display_string, import_by_name, is_running_migrations


class TestConditions:
    """Test the conditions system for conditional implementations."""

    def test_callable_condition(self):
        """Test CallableCondition with lambda."""
        condition = CallableCondition(lambda ctx: ctx.get("enabled", False))

        assert condition.is_met({"enabled": True}) is True
        assert condition.is_met({"enabled": False}) is False
        assert condition.is_met({}) is False

    def test_all_conditions(self):
        """Test AllConditions combines with AND logic."""
        cond1 = CallableCondition(lambda ctx: ctx.get("a", False))
        cond2 = CallableCondition(lambda ctx: ctx.get("b", False))

        all_cond = AllConditions([cond1, cond2])

        assert all_cond.is_met({"a": True, "b": True}) is True
        assert all_cond.is_met({"a": True, "b": False}) is False
        assert all_cond.is_met({"a": False, "b": True}) is False
        assert all_cond.is_met({"a": False, "b": False}) is False

    def test_any_condition(self):
        """Test AnyCondition combines with OR logic."""
        cond1 = CallableCondition(lambda ctx: ctx.get("a", False))
        cond2 = CallableCondition(lambda ctx: ctx.get("b", False))

        any_cond = AnyCondition([cond1, cond2])

        assert any_cond.is_met({"a": True, "b": True}) is True
        assert any_cond.is_met({"a": True, "b": False}) is True
        assert any_cond.is_met({"a": False, "b": True}) is True
        assert any_cond.is_met({"a": False, "b": False}) is False

    def test_not_condition(self):
        """Test NotCondition negates a condition."""
        cond = CallableCondition(lambda ctx: ctx.get("enabled", False))
        not_cond = NotCondition(cond)

        assert not_cond.is_met({"enabled": True}) is False
        assert not_cond.is_met({"enabled": False}) is True

    def test_condition_and_operator(self):
        """Test condition & operator creates AllConditions."""
        cond1 = CallableCondition(lambda ctx: ctx.get("a", False))
        cond2 = CallableCondition(lambda ctx: ctx.get("b", False))

        combined = cond1 & cond2

        assert isinstance(combined, AllConditions)
        assert combined.is_met({"a": True, "b": True}) is True
        assert combined.is_met({"a": True, "b": False}) is False

    def test_condition_or_operator(self):
        """Test condition | operator creates AnyCondition."""
        cond1 = CallableCondition(lambda ctx: ctx.get("a", False))
        cond2 = CallableCondition(lambda ctx: ctx.get("b", False))

        combined = cond1 | cond2

        assert isinstance(combined, AnyCondition)
        assert combined.is_met({"a": True, "b": False}) is True
        assert combined.is_met({"a": False, "b": False}) is False

    def test_condition_invert_operator(self):
        """Test ~condition creates NotCondition."""
        cond = CallableCondition(lambda ctx: ctx.get("enabled", False))
        inverted = ~cond

        assert isinstance(inverted, NotCondition)
        assert inverted.is_met({"enabled": True}) is False
        assert inverted.is_met({"enabled": False}) is True

    def test_complex_condition_combination(self):
        """Test complex combinations of conditions."""
        cond_a = CallableCondition(lambda ctx: ctx.get("a", False))
        cond_b = CallableCondition(lambda ctx: ctx.get("b", False))
        cond_c = CallableCondition(lambda ctx: ctx.get("c", False))

        # (a AND b) OR c
        complex_cond = (cond_a & cond_b) | cond_c

        assert complex_cond.is_met({"a": True, "b": True, "c": False}) is True
        assert complex_cond.is_met({"a": False, "b": False, "c": True}) is True
        assert complex_cond.is_met({"a": True, "b": False, "c": False}) is False
        assert complex_cond.is_met({"a": False, "b": False, "c": False}) is False

    def test_permission_condition_with_user(self):
        """Test PermissionCondition checks user permissions."""
        from django.contrib.auth import get_user_model

        get_user_model()  # Verify user model is available

        # Create users (don't save to DB in this simple test)
        class MockUser:
            def has_perm(self, perm):
                return perm == "app.can_do_something"

        condition = PermissionCondition("app.can_do_something")

        context_with_permission = {"user": MockUser()}
        context_without_permission = {"user": type("User", (), {"has_perm": lambda self, perm: False})()}

        assert condition.is_met(context_with_permission) is True
        assert condition.is_met(context_without_permission) is False

    def test_permission_condition_without_user(self):
        """Test PermissionCondition returns False without user."""
        condition = PermissionCondition("app.can_do_something")

        assert condition.is_met({}) is False
        assert condition.is_met({"user": None}) is False


class TestUtilityFunctions:
    """Test utility functions in utils.py."""

    def test_import_by_name_success(self):
        """Test importing a class by name."""
        result = import_by_name("django_stratagem.registry.Registry")
        assert result == Registry

    def test_import_by_name_invalid_module(self):
        """Test import_by_name raises ImportError for invalid module."""
        with pytest.raises(ImportError):
            import_by_name("apps.nonexistent.module.Class")

    def test_import_by_name_invalid_attribute(self):
        """Test import_by_name raises AttributeError for invalid attribute."""
        with pytest.raises(AttributeError):
            import_by_name("django_stratagem.registry.NonExistentClass")

    def test_get_class_with_full_path(self):
        """Test get_class with full module path."""
        result = get_class("django_stratagem.interfaces.Interface")
        assert result == Interface

    def test_get_display_string_with_display_name(self):
        """Test get_display_string uses display_name attribute when specified."""

        class TestClass:
            display_name = "Test Display Name"

        # Without specifying the attribute, uses camel_to_title on class name
        result = get_display_string(TestClass)
        assert result == "Test Class"

        # With display_attribute specified, uses that attribute
        result = get_display_string(TestClass, "display_name")
        assert result == "Test Display Name"

    def test_get_display_string_with_custom_attribute(self):
        """Test get_display_string uses custom attribute."""

        class TestClass:
            custom_label = "Custom Label"

        result = get_display_string(TestClass, "custom_label")
        assert result == "Custom Label"

    def test_get_display_string_fallback_to_name(self):
        """Test get_display_string falls back to camel_to_title(__name__)."""

        class TestClass:
            pass

        result = get_display_string(TestClass)
        # camel_to_title converts TestClass to "Test Class"
        assert result == "Test Class"

    def test_get_display_string_with_callable_attribute(self):
        """Test get_display_string calls callable attributes."""

        class TestClass:
            @staticmethod
            def custom_label():
                return "Callable Label"

        result = get_display_string(TestClass, "custom_label")
        assert result == "Callable Label"


@pytest.mark.django_db
class TestSignals:
    """Test signal emission for registry events."""

    def test_implementation_registered_signal(self):
        """Test implementation_registered signal is sent."""
        signal_received = []

        def handler(sender, registry, implementation, **kwargs):
            signal_received.append({"sender": sender, "registry": registry, "implementation": implementation})

        implementation_registered.connect(handler)

        try:
            # Create a test registry
            class TestSignalRegistry(Registry):
                implementations_module = "test_signals"

            # Create and register an implementation
            class TestImpl(Interface):
                slug = "test_signal_impl"
                registry = TestSignalRegistry

            # Should have received signal
            assert len(signal_received) == 1
            assert signal_received[0]["sender"] == TestSignalRegistry
            assert signal_received[0]["implementation"] == TestImpl

        finally:
            implementation_registered.disconnect(handler)

    def test_implementation_unregistered_signal(self):
        """Test implementation_unregistered signal is sent."""
        signal_received = []

        def handler(sender, registry, slug, **kwargs):
            signal_received.append({"sender": sender, "registry": registry, "slug": slug})

        implementation_unregistered.connect(handler)

        try:
            # Create a test registry with an implementation
            class TestUnregisterRegistry(Registry):
                implementations_module = "test_unregister"

            class TestImpl(Interface):
                slug = "test_unregister_impl"
                registry = TestUnregisterRegistry

            # Unregister it
            TestUnregisterRegistry.unregister("test_unregister_impl")

            # Should have received signal
            assert len(signal_received) == 1
            assert signal_received[0]["sender"] == TestUnregisterRegistry
            assert signal_received[0]["slug"] == "test_unregister_impl"

        finally:
            implementation_unregistered.disconnect(handler)

    def test_registry_reloaded_signal(self):
        """Test registry_reloaded signal is sent."""
        signal_received = []

        def handler(sender, registry, **kwargs):
            signal_received.append({"sender": sender, "registry": registry})

        registry_reloaded.connect(handler)

        try:
            # Discover registries which sends reload signal
            discover_registries()

            # Should have received signals for all registries
            assert len(signal_received) > 0

        finally:
            registry_reloaded.disconnect(handler)


@pytest.mark.django_db
class TestRegistryEdgeCases:
    """Test edge cases and error conditions in Registry."""

    def test_register_without_slug_raises_error(self):
        """Test registering implementation without slug raises ValueError."""

        class TestRegistryNoSlug(Registry):
            implementations_module = "test_no_slug"

        class ImplWithoutSlug(Interface):
            registry = TestRegistryNoSlug
            # No slug defined

        # Should not be registered due to missing slug
        assert "implwithoutslug" not in TestRegistryNoSlug.implementations

    def test_unregister_nonexistent_slug_raises_error(self):
        """Test unregistering non-existent slug raises ImplementationNotFound."""

        class TestRegistryUnregister(Registry):
            implementations_module = "test_unregister_missing"

        with pytest.raises(ImplementationNotFound):
            TestRegistryUnregister.unregister("does_not_exist")

    def test_get_with_invalid_slug_raises_error(self):
        """Test get() with invalid slug raises ImplementationNotFound."""

        class TestRegistryInvalidSlug(Registry):
            implementations_module = "test_invalid_slug"

        with pytest.raises(ImplementationNotFound):
            TestRegistryInvalidSlug.get(slug="invalid_slug")

    def test_get_without_arguments_raises_error(self):
        """Test get() without slug or fully_qualified_name raises ValueError."""

        class TestRegistryNoArgs(Registry):
            implementations_module = "test_no_args"

        with pytest.raises(ValueError, match="Either 'slug' or 'fully_qualified_name' must be provided"):
            TestRegistryNoArgs.get()

    def test_cache_operations(self):
        """Test cache is populated and cleared correctly."""

        class TestRegistryCache(Registry):
            implementations_module = "test_cache"

        class TestCacheImpl(Interface):
            slug = "test_cache_impl"
            display_name = "Test Cache"
            registry = TestRegistryCache

        # Get choices to populate cache
        choices = TestRegistryCache.get_choices()
        assert len(choices) > 0

        # Check cache is populated
        cache_key = TestRegistryCache.get_cache_key("choices")
        cached_choices = cache.get(cache_key)
        assert cached_choices is not None

        # Clear cache
        TestRegistryCache.clear_cache()

        # Cache should be cleared
        cached_choices_after = cache.get(cache_key)
        assert cached_choices_after is None

    def test_check_health(self):
        """Test check_health returns metrics."""

        class TestRegistryHealth(Registry):
            implementations_module = "test_health"

        class TestHealthImpl(Interface):
            slug = "test_health_impl"
            registry = TestRegistryHealth

        health = TestRegistryHealth.check_health()

        assert "count" in health
        assert health["count"] >= 1
        assert "last_updated" in health

    def test_contains_method(self):
        """Test contains() method."""

        class TestRegistryContains(Registry):
            implementations_module = "test_contains"

        class TestContainsImpl(Interface):
            slug = "test_contains_impl"
            registry = TestRegistryContains

        assert TestRegistryContains.contains("test_contains_impl") is True
        assert TestRegistryContains.contains("invalid") is False
        assert TestRegistryContains.contains(TestContainsImpl) is True

    def test_count_implementations(self):
        """Test count_implementations returns correct count."""

        class TestRegistryCount(Registry):
            implementations_module = "test_count"

        initial_count = TestRegistryCount.count_implementations()

        class TestCountImpl1(Interface):
            slug = "test_count_impl1"
            registry = TestRegistryCount

        class TestCountImpl2(Interface):
            slug = "test_count_impl2"
            registry = TestRegistryCount

        assert TestRegistryCount.count_implementations() == initial_count + 2


@pytest.mark.django_db
class TestHierarchicalInterfaces:
    """Test hierarchical interface functionality."""

    def test_is_valid_for_parent_single_parent(self):
        """Test is_valid_for_parent with single parent_slug."""

        class ChildImpl(HierarchicalInterface):
            slug = "child"
            parent_slug = "parent1"

        assert ChildImpl.is_valid_for_parent("parent1") is True
        assert ChildImpl.is_valid_for_parent("parent2") is False

    def test_is_valid_for_parent_multiple_parents(self):
        """Test is_valid_for_parent with parent_slugs list."""

        class MultiParentImpl(HierarchicalInterface):
            slug = "multi_child"
            parent_slugs = ["parent1", "parent2"]

        assert MultiParentImpl.is_valid_for_parent("parent1") is True
        assert MultiParentImpl.is_valid_for_parent("parent2") is True
        assert MultiParentImpl.is_valid_for_parent("parent3") is False

    def test_is_valid_for_parent_no_restriction(self):
        """Test is_valid_for_parent returns True when no parent specified."""

        class NoParentImpl(HierarchicalInterface):
            slug = "no_parent"

        assert NoParentImpl.is_valid_for_parent("any_parent") is True


@pytest.mark.django_db
class TestContextAwareImplementations:
    """Test context-aware implementation selection."""

    def test_get_available_implementations_without_is_available(self):
        """Test get_available_implementations returns all when no is_available method."""

        class TestContextRegistry(Registry):
            implementations_module = "test_context"

        class AlwaysAvailableImpl(Interface):
            slug = "always_available"
            registry = TestContextRegistry

        available = TestContextRegistry.get_available_implementations()

        assert "always_available" in available

    def test_get_available_implementations_with_is_available(self):
        """Test get_available_implementations respects is_available method."""

        class TestContextRegistry2(Registry):
            implementations_module = "test_context2"

        class ConditionalImpl(Interface):
            slug = "conditional"
            registry = TestContextRegistry2

            @classmethod
            def is_available(cls, context):
                return context.get("enabled", False) if context else False

        # Without enabled context
        available = TestContextRegistry2.get_available_implementations({})
        assert "conditional" not in available

        # With enabled context
        available_enabled = TestContextRegistry2.get_available_implementations({"enabled": True})
        assert "conditional" in available_enabled

    def test_get_choices_for_context(self):
        """Test get_choices_for_context filters by context."""

        class TestChoicesContextRegistry(Registry):
            implementations_module = "test_choices_context"

        class EnabledImpl(Interface):
            slug = "enabled_impl"
            display_name = "Enabled Implementation"
            registry = TestChoicesContextRegistry

            @classmethod
            def is_available(cls, context):
                return context.get("enabled", False) if context else False

        class AlwaysImpl(Interface):
            slug = "always_impl"
            display_name = "Always Available"
            registry = TestChoicesContextRegistry

        # Without enabled context
        choices = TestChoicesContextRegistry.get_choices_for_context({})
        slugs = [slug for slug, _ in choices]
        assert "always_impl" in slugs
        assert "enabled_impl" not in slugs

        # With enabled context
        choices_enabled = TestChoicesContextRegistry.get_choices_for_context({"enabled": True})
        slugs_enabled = [slug for slug, _ in choices_enabled]
        assert "always_impl" in slugs_enabled
        assert "enabled_impl" in slugs_enabled


class TestAppSettingsDynamic:
    """Test that app_settings reads settings dynamically at call time."""

    def test_get_cache_timeout_default(self):
        """Test default cache timeout is 300."""
        from django_stratagem.app_settings import get_cache_timeout

        assert get_cache_timeout() == 300

    def test_get_cache_timeout_override(self, settings):
        """Test cache timeout respects override_settings."""
        from django_stratagem.app_settings import get_cache_timeout

        settings.DJANGO_STRATAGEM = {"CACHE_TIMEOUT": 600}
        assert get_cache_timeout() == 600

    def test_get_cache_timeout_reverts_after_override(self, settings):
        """Test cache timeout reverts after settings change."""
        from django_stratagem.app_settings import get_cache_timeout

        settings.DJANGO_STRATAGEM = {"CACHE_TIMEOUT": 999}
        assert get_cache_timeout() == 999

        # Remove the override
        del settings.DJANGO_STRATAGEM
        assert get_cache_timeout() == 300

    def test_get_skip_during_migrations_default(self):
        """Test default skip_during_migrations is True."""
        from django_stratagem.app_settings import get_skip_during_migrations

        assert get_skip_during_migrations() is True

    def test_get_skip_during_migrations_override(self, settings):
        """Test skip_during_migrations respects override_settings."""
        from django_stratagem.app_settings import get_skip_during_migrations

        settings.DJANGO_STRATAGEM = {"SKIP_DURING_MIGRATIONS": False}
        assert get_skip_during_migrations() is False


class TestMigrationDetection:
    """Test is_running_migrations detection."""

    def test_is_running_migrations_normal_execution(self):
        """Test is_running_migrations returns False during normal execution."""
        assert is_running_migrations() is False

    # Note: Testing True case would require actually running migrations
    # which is not practical in a unit test


@pytest.mark.django_db
class TestInterfaceAutoRegistration:
    """Test Interface auto-registration behavior."""

    def test_interface_without_registry_not_registered(self):
        """Test Interface without registry is not registered."""

        class NoRegistryImpl(Interface):
            slug = "no_registry"
            # No registry specified

        # Should not raise error, just log and skip

    def test_interface_without_slug_not_registered(self):
        """Test Interface without slug is not registered."""

        class TestRegistryNoSlugImpl(Registry):
            implementations_module = "test_no_slug_impl"

        class NoSlugImpl(Interface):
            registry = TestRegistryNoSlugImpl
            # No slug specified

        # Should not be in implementations
        assert len([k for k in TestRegistryNoSlugImpl.implementations.keys() if "noslug" in k.lower()]) == 0

    def test_interface_with_invalid_registry_not_registered(self):
        """Test Interface with invalid registry is not registered."""

        class InvalidRegistryImpl(Interface):
            slug = "invalid_registry"
            registry = "not a registry class"

        # Should not raise error, just log and skip


@pytest.mark.django_db
class TestRegistryMetadata:
    """Test registry implementation metadata."""

    def test_get_implementation_meta(self):
        """Test get_implementation_meta returns full metadata."""

        class TestMetaRegistry(Registry):
            implementations_module = "test_meta"

        class TestMetaImpl(Interface):
            slug = "test_meta_impl"
            description = "Test Description"
            icon = "fa-solid fa-test"
            priority = 10
            registry = TestMetaRegistry

        meta = TestMetaRegistry.get_implementation_meta("test_meta_impl")

        assert meta["klass"] == TestMetaImpl
        assert meta["description"] == "Test Description"
        assert meta["icon"] == "fa-solid fa-test"
        assert meta["priority"] == 10

    def test_get_implementation_meta_nonexistent_raises_error(self):
        """Test get_implementation_meta raises error for nonexistent slug."""

        class TestMetaRegistry2(Registry):
            implementations_module = "test_meta2"

        with pytest.raises(ImplementationNotFound):
            TestMetaRegistry2.get_implementation_meta("nonexistent")

    def test_iter_implementations(self):
        """Test iter_implementations returns metadata."""

        class TestIterRegistry(Registry):
            implementations_module = "test_iter"

        class TestIterImpl(Interface):
            slug = "test_iter_impl"
            registry = TestIterRegistry

        implementations = list(TestIterRegistry.iter_implementations())

        assert len(implementations) > 0
        assert all(isinstance(impl, dict) for impl in implementations)
        assert all("klass" in impl for impl in implementations)


class TestSkipDuringMigrations:
    """Test skip_during_migrations decorator return values."""

    def test_skip_during_migrations_get_choices(self):
        """Test skip_during_migrations returns [] for get_choices."""
        from django_stratagem.registry import skip_during_migrations

        @skip_during_migrations
        def get_choices():
            return [("a", "A")]

        with patch("django_stratagem.registry.is_running_migrations", return_value=True):
            assert get_choices() == []

    def test_skip_during_migrations_discover_implementations(self):
        """Test skip_during_migrations returns None for discover_implementations."""
        from django_stratagem.registry import skip_during_migrations

        @skip_during_migrations
        def discover_implementations():
            return "discovered"

        with patch("django_stratagem.registry.is_running_migrations", return_value=True):
            assert discover_implementations() is None

    def test_skip_during_migrations_get_items(self):
        """Test skip_during_migrations returns [] for get_items."""
        from django_stratagem.registry import skip_during_migrations

        @skip_during_migrations
        def get_items():
            return [("a", "A")]

        with patch("django_stratagem.registry.is_running_migrations", return_value=True):
            assert get_items() == []

    def test_skip_during_migrations_check_health(self):
        """Test skip_during_migrations returns health default for check_health."""
        from django_stratagem.registry import skip_during_migrations

        @skip_during_migrations
        def check_health():
            return {"count": 10}

        with patch("django_stratagem.registry.is_running_migrations", return_value=True):
            result = check_health()
            assert result == {"count": 0, "last_updated": None}

    def test_skip_during_migrations_other_method(self):
        """Test skip_during_migrations returns None for other methods."""
        from django_stratagem.registry import skip_during_migrations

        @skip_during_migrations
        def some_other_method():
            return "something"

        with patch("django_stratagem.registry.is_running_migrations", return_value=True):
            assert some_other_method() is None


class TestUpdateChoicesFields:
    """Test update_choices_fields edge cases."""

    def test_update_choices_fields_exception_handling(self):
        """Test update_choices_fields handles LookupError/AttributeError."""
        from django_stratagem.registry import update_choices_fields

        # Create a registry with a bad choices_field reference
        class TestBadChoicesRegistry(Registry):
            implementations_module = "test_bad_choices"

        class TestBadChoicesImpl(Interface):
            slug = "test_bad"
            registry = TestBadChoicesRegistry

        # Add a bad choices field reference
        TestBadChoicesRegistry.choices_fields.append(
            (
                "nonexistent_field",
                type(
                    "FakeModel",
                    (),
                    {
                        "_meta": type("Meta", (), {"app_label": "nonexistent_app", "model_name": "nonexistent"})(),
                    },
                ),
            )
        )

        # Should not raise, just log error
        update_choices_fields()


class TestRegistryEdgeCasesExtended:
    """Extended edge case tests for Registry."""

    def test_get_for_context_no_slug_no_fqn(self, test_strategy_registry):
        """Test get_for_context with neither slug nor FQN returns first available."""
        result = test_strategy_registry.get_for_context()
        assert result is not None

    def test_get_with_invalid_fqn_raises(self):
        """Test get() with invalid FQN that raises ImportError."""

        class TestGetFqnRegistry(Registry):
            implementations_module = "test_get_fqn"

        with pytest.raises((ImportError, AttributeError, ImplementationNotFound)):
            TestGetFqnRegistry.get(fully_qualified_name="nonexistent.module.Class")

    def test_get_class_without_arguments_raises(self):
        """Test get_class() without slug or FQN raises ValueError."""

        class TestGetClassRegistry(Registry):
            implementations_module = "test_get_class_no_args"

        with pytest.raises(ValueError, match="Either 'slug' or 'fully_qualified_name' must be provided"):
            TestGetClassRegistry.get_class()

    def test_get_implementation_meta_missing_slug(self):
        """Test get_implementation_meta with missing slug raises ImplementationNotFound."""

        class TestMetaMissingRegistry(Registry):
            implementations_module = "test_meta_missing"

        with pytest.raises(ImplementationNotFound):
            TestMetaMissingRegistry.get_implementation_meta("nonexistent_slug")

    def test_get_implementation_class_missing_slug(self):
        """Test get_implementation_class with missing slug raises ImplementationNotFound."""

        class TestImplClassMissingRegistry(Registry):
            implementations_module = "test_impl_class_missing"

        with pytest.raises(ImplementationNotFound):
            TestImplClassMissingRegistry.get_implementation_class("nonexistent_slug")

    def test_registry_is_valid_with_instance(self, test_strategy_registry, email_strategy):
        """Test is_valid with an instance."""
        instance = email_strategy()
        assert test_strategy_registry.is_valid(instance) is True


class TestCacheHitPaths:
    """Test that cache hit branches return cached (stale) data."""

    def test_get_choices_serves_from_cache(self, test_strategy_registry):
        """Calling get_choices twice returns cached data even after mutation."""
        # First call populates cache
        choices1 = test_strategy_registry.get_choices()
        assert len(choices1) == 3

        # Mutate implementations to add a fourth entry
        test_strategy_registry.implementations["phantom"] = {
            "klass": None,
            "description": "",
            "icon": "",
            "priority": 0,
        }

        # Second call should return stale (cached) data - still 3 choices
        choices2 = test_strategy_registry.get_choices()
        assert choices2 == choices1

        # Clean up
        test_strategy_registry.implementations.pop("phantom", None)

    def test_get_items_serves_from_cache(self, test_strategy_registry):
        """Calling get_items twice returns cached data even after mutation."""
        items1 = test_strategy_registry.get_items()
        assert len(items1) == 3

        test_strategy_registry.implementations["phantom"] = {
            "klass": None,
            "description": "",
            "icon": "",
            "priority": 0,
        }

        items2 = test_strategy_registry.get_items()
        assert items2 == items1

        test_strategy_registry.implementations.pop("phantom", None)

    def test_get_hierarchy_map_serves_from_cache(self, parent_registry, child_registry):
        """Calling get_hierarchy_map twice returns cached data even after mutation."""
        map1 = child_registry.get_hierarchy_map()
        assert len(map1) > 0

        # Mutate by removing an implementation
        removed_slug = next(iter(child_registry.implementations))
        removed_meta = child_registry.implementations.pop(removed_slug)

        map2 = child_registry.get_hierarchy_map()
        assert map2 == map1

        # Restore
        child_registry.implementations[removed_slug] = removed_meta

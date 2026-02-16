"""Tests for HierarchicalRegistry, RegistryRelationship, and parent-child validation."""

from __future__ import annotations

import pytest
from django.core.cache import cache

from django_stratagem.interfaces import HierarchicalInterface, Interface
from django_stratagem.registry import HierarchicalRegistry, Registry, RegistryRelationship, register

pytestmark = pytest.mark.django_db


class TestHierarchicalRegistry:
    """Tests for HierarchicalRegistry class functionality."""

    def test_get_parent_registry(self, parent_registry, child_registry):
        """Test get_parent_registry returns the parent."""
        assert child_registry.get_parent_registry() == parent_registry

    def test_get_parent_registry_when_none(self):
        """Test get_parent_registry returns None when no parent is set."""

        class StandaloneHierarchicalRegistry(HierarchicalRegistry):
            implementations_module = "standalone_test"
            parent_registry = None

        assert StandaloneHierarchicalRegistry.get_parent_registry() is None

    def test_get_children_for_parent_returns_implementations(self, child_registry):
        """Test get_children_for_parent returns implementations for valid parent."""
        from tests.registries_fixtures import ChildOfA

        children = child_registry.get_children_for_parent("category_a")

        # Should include ChildOfA and ChildOfBoth (which works with both)
        assert "child_of_a" in children
        assert "child_of_both" in children
        assert children["child_of_a"] == ChildOfA

    def test_get_children_for_parent_with_context(self, child_registry, premium_user):
        """Test get_children_for_parent respects context filtering."""
        context = {"user": premium_user}
        children = child_registry.get_children_for_parent("category_a", context)

        # Without conditional implementations, should return all
        assert len(children) >= 1

    def test_get_choices_for_parent(self, child_registry):
        """Test get_choices_for_parent returns choices for valid parent."""
        choices = child_registry.get_choices_for_parent("category_a")

        # Should be a list of tuples (slug, display_name)
        assert isinstance(choices, list)
        slugs = [slug for slug, _ in choices]
        assert "child_of_a" in slugs
        assert "child_of_both" in slugs

    def test_validate_parent_child_relationship_valid(self, child_registry):
        """Test validation passes for valid parent-child relationship."""
        assert child_registry.validate_parent_child_relationship("category_a", "child_of_a") is True
        assert child_registry.validate_parent_child_relationship("category_b", "child_of_b") is True

    def test_validate_parent_child_relationship_invalid_child(self, child_registry):
        """Test validation fails for invalid child slug."""
        assert child_registry.validate_parent_child_relationship("category_a", "nonexistent") is False

    def test_get_hierarchy_map(self, parent_registry, child_registry):
        """Test get_hierarchy_map returns mapping of parent to children."""
        hierarchy_map = child_registry.get_hierarchy_map()

        assert isinstance(hierarchy_map, dict)
        # Should have entries for each parent
        assert "category_a" in hierarchy_map or "category_b" in hierarchy_map

    def test_get_hierarchy_map_caching(self, parent_registry, child_registry):
        """Test that hierarchy map is cached properly."""
        # Clear cache first
        cache_key = child_registry.get_cache_key("hierarchy_map")
        cache.delete(cache_key)

        # First call should populate cache
        result1 = child_registry.get_hierarchy_map()

        # Second call should use cache
        result2 = child_registry.get_hierarchy_map()

        assert result1 == result2
        # Check cache was populated
        cached = cache.get(cache_key)
        assert cached is not None

    def test_get_hierarchy_map_without_parent_registry(self):
        """Test get_hierarchy_map returns empty dict when no parent registry."""

        class NoParentHierarchicalRegistry(HierarchicalRegistry):
            implementations_module = "no_parent_test"
            parent_registry = None

        result = NoParentHierarchicalRegistry.get_hierarchy_map()
        assert result == {}


class TestHierarchicalRegistryWithRestrictedParents:
    """Tests for hierarchical registries with parent_slugs restrictions."""

    def test_get_children_for_parent_respects_parent_slugs(self):
        """Test that parent_slugs restriction filters results."""

        class RestrictedParentRegistry(Registry):
            implementations_module = "restricted_parent_test"

        class ParentImplA(Interface):
            slug = "parent_a"
            registry = RestrictedParentRegistry

        class ParentImplB(Interface):
            slug = "parent_b"
            registry = RestrictedParentRegistry

        class RestrictedChildRegistry(HierarchicalRegistry):
            implementations_module = "restricted_child_test"
            parent_registry = RestrictedParentRegistry
            parent_slugs = ["parent_a"]  # Only valid for parent_a

        class ChildImpl(Interface):
            slug = "child"
            registry = RestrictedChildRegistry

        # Should return children for allowed parent
        children_a = RestrictedChildRegistry.get_children_for_parent("parent_a")
        assert "child" in children_a

        # Should return empty for non-allowed parent
        children_b = RestrictedChildRegistry.get_children_for_parent("parent_b")
        assert children_b == {}

    def test_validate_parent_child_with_restricted_parents(self):
        """Test validation fails when parent not in parent_slugs."""

        class ValidatingParentRegistry(Registry):
            implementations_module = "validating_parent_test"

        class ValidatingChildRegistry(HierarchicalRegistry):
            implementations_module = "validating_child_test"
            parent_registry = ValidatingParentRegistry
            parent_slugs = ["allowed_parent"]

        class ValidatingChildImpl(Interface):
            slug = "validating_child"
            registry = ValidatingChildRegistry

        # Should fail for non-allowed parent
        assert ValidatingChildRegistry.validate_parent_child_relationship("not_allowed", "validating_child") is False

        # Should pass for allowed parent
        assert ValidatingChildRegistry.validate_parent_child_relationship("allowed_parent", "validating_child") is True


class TestRegistryRelationship:
    """Tests for RegistryRelationship class."""

    def setup_method(self):
        """Clear relationships before each test."""
        RegistryRelationship.clear_relationships()

    def teardown_method(self):
        """Clear relationships after each test."""
        RegistryRelationship.clear_relationships()

    def test_register_child(self):
        """Test registering a child registry with a parent."""

        class TestParentRegistry(Registry):
            implementations_module = "test_parent_rel"

        class TestChildRegistry(HierarchicalRegistry):
            implementations_module = "test_child_rel"
            parent_registry = None

        RegistryRelationship.register_child(TestParentRegistry, TestChildRegistry)

        children = RegistryRelationship.get_children_registries(TestParentRegistry)
        assert TestChildRegistry in children
        assert TestChildRegistry.parent_registry == TestParentRegistry

    def test_register_child_prevents_duplicates(self):
        """Test that registering the same child twice doesn't create duplicates."""

        class DuplicateParentRegistry(Registry):
            implementations_module = "dup_parent_rel"

        class DuplicateChildRegistry(HierarchicalRegistry):
            implementations_module = "dup_child_rel"
            parent_registry = None

        RegistryRelationship.register_child(DuplicateParentRegistry, DuplicateChildRegistry)
        RegistryRelationship.register_child(DuplicateParentRegistry, DuplicateChildRegistry)

        children = RegistryRelationship.get_children_registries(DuplicateParentRegistry)
        assert children.count(DuplicateChildRegistry) == 1

    def test_get_children_registries_empty(self):
        """Test get_children_registries returns empty list for unregistered parent."""

        class UnrelatedRegistry(Registry):
            implementations_module = "unrelated_rel"

        children = RegistryRelationship.get_children_registries(UnrelatedRegistry)
        assert children == []

    def test_get_all_descendants(self):
        """Test getting all descendants recursively."""

        class GrandparentRegistry(Registry):
            implementations_module = "grandparent_test"

        class ParentChildRegistry(HierarchicalRegistry):
            implementations_module = "parent_child_test"
            parent_registry = None

        class GrandchildRegistry(HierarchicalRegistry):
            implementations_module = "grandchild_test"
            parent_registry = None

        # Set up hierarchy: Grandparent -> Parent -> Grandchild
        RegistryRelationship.register_child(GrandparentRegistry, ParentChildRegistry)
        RegistryRelationship.register_child(ParentChildRegistry, GrandchildRegistry)

        descendants = RegistryRelationship.get_all_descendants(GrandparentRegistry)

        assert ParentChildRegistry in descendants
        assert GrandchildRegistry in descendants

    def test_clear_relationships(self):
        """Test clearing all relationships."""

        class ClearTestParentRegistry(Registry):
            implementations_module = "clear_parent_test"

        class ClearTestChildRegistry(HierarchicalRegistry):
            implementations_module = "clear_child_test"
            parent_registry = None

        RegistryRelationship.register_child(ClearTestParentRegistry, ClearTestChildRegistry)
        assert len(RegistryRelationship.get_children_registries(ClearTestParentRegistry)) > 0

        RegistryRelationship.clear_relationships()
        assert RegistryRelationship._relationships == {}


class TestRegisterDecorator:
    """Tests for the @register decorator."""

    def test_register_decorator(self):
        """Test that @register decorator registers implementation."""

        class DecoratorTestRegistry(Registry):
            implementations_module = "decorator_test"

        @register(DecoratorTestRegistry)
        class DecoratedImpl(Interface):
            slug = "decorated"

        assert "decorated" in DecoratorTestRegistry.implementations
        assert DecoratorTestRegistry.implementations["decorated"]["klass"] == DecoratedImpl

    def test_register_decorator_returns_class(self):
        """Test that @register decorator returns the decorated class."""

        class ReturnTestRegistry(Registry):
            implementations_module = "return_test"

        @register(ReturnTestRegistry)
        class ReturnedImpl(Interface):
            slug = "returned"

        # Should be able to instantiate the class
        instance = ReturnedImpl()
        assert instance is not None


class TestRegistryFactoryMethods:
    """Tests for Registry factory methods."""

    def test_choices_field_creates_registry_class_field(self, test_strategy_registry):
        """Test choices_field creates a RegistryClassField."""
        from django_stratagem.fields import RegistryClassField

        field = test_strategy_registry.choices_field()

        assert isinstance(field, RegistryClassField)
        assert field.registry == test_strategy_registry

    def test_instance_field_creates_registry_field(self, test_strategy_registry):
        """Test instance_field creates a RegistryField."""
        from django_stratagem.fields import RegistryField

        field = test_strategy_registry.instance_field()

        assert isinstance(field, RegistryField)
        assert field.registry == test_strategy_registry

    def test_choices_field_with_kwargs(self, test_strategy_registry):
        """Test choices_field passes kwargs to field."""
        field = test_strategy_registry.choices_field(blank=True, null=True)

        assert field.blank is True
        assert field.null is True

    def test_instance_field_with_kwargs(self, test_strategy_registry):
        """Test instance_field passes kwargs to field."""
        field = test_strategy_registry.instance_field(blank=True, null=True)

        assert field.blank is True
        assert field.null is True


class TestContextAwareImplementations:
    """Tests for get_for_context functionality."""

    def test_get_for_context_with_available_implementation(self, test_strategy_registry):
        """Test get_for_context returns available implementation."""
        impl = test_strategy_registry.get_for_context(context={}, slug="email")

        assert impl is not None
        assert impl.execute() == "email_sent"

    def test_get_for_context_with_fallback(self, test_strategy_registry):
        """Test get_for_context uses fallback when primary not available."""
        impl = test_strategy_registry.get_for_context(context={}, slug="nonexistent", fallback="email")

        assert impl is not None
        assert impl.execute() == "email_sent"

    def test_get_for_context_raises_when_no_available(self):
        """Test get_for_context raises error when no implementations available."""
        from django_stratagem.exceptions import ImplementationNotFound

        class EmptyContextRegistry(Registry):
            implementations_module = "empty_context_test"

        with pytest.raises(ImplementationNotFound):
            EmptyContextRegistry.get_for_context(context={}, slug="nonexistent")


class TestRegistryIsValid:
    """Tests for Registry.is_valid method with various inputs."""

    def test_is_valid_with_slug_string(self, test_strategy_registry):
        """Test is_valid with valid slug string."""
        assert test_strategy_registry.is_valid("email") is True

    def test_is_valid_with_invalid_slug(self, test_strategy_registry):
        """Test is_valid with invalid slug string."""
        assert test_strategy_registry.is_valid("nonexistent_slug") is False

    def test_is_valid_with_class(self, test_strategy_registry, email_strategy):
        """Test is_valid with registered class."""
        assert test_strategy_registry.is_valid(email_strategy) is True

    def test_is_valid_with_unregistered_class(self, test_strategy_registry):
        """Test is_valid with unregistered class."""

        class UnregisteredImpl:
            pass

        assert test_strategy_registry.is_valid(UnregisteredImpl) is False

    def test_is_valid_with_instance(self, test_strategy_registry, email_strategy):
        """Test is_valid with instance of registered class."""
        instance = email_strategy()
        assert test_strategy_registry.is_valid(instance) is True

    def test_is_valid_with_fully_qualified_name(self, test_strategy_registry):
        """Test is_valid with fully qualified class name."""
        fqn = "tests.registries_fixtures.EmailStrategy"
        assert test_strategy_registry.is_valid(fqn) is True

    def test_is_valid_with_invalid_fqn(self, test_strategy_registry):
        """Test is_valid with invalid fully qualified name."""
        assert test_strategy_registry.is_valid("invalid.module.Class") is False

    @pytest.mark.parametrize(
        "invalid_value",
        [
            None,
            123,
            12.5,
            [],
            {},
            set(),
        ],
    )
    def test_is_valid_with_invalid_types(self, test_strategy_registry, invalid_value):
        """Test is_valid returns False for various invalid types."""
        assert test_strategy_registry.is_valid(invalid_value) is False


class TestHierarchicalInterfaceValidation:
    """Tests for HierarchicalInterface validation methods."""

    def test_is_valid_for_parent_with_single_parent_slug(self):
        """Test is_valid_for_parent with single parent_slug."""
        from tests.registries_fixtures import ChildOfA

        assert ChildOfA.is_valid_for_parent("category_a") is True
        assert ChildOfA.is_valid_for_parent("category_b") is False

    def test_is_valid_for_parent_with_multiple_parent_slugs(self):
        """Test is_valid_for_parent with parent_slugs list."""
        from tests.registries_fixtures import ChildOfBoth

        assert ChildOfBoth.is_valid_for_parent("category_a") is True
        assert ChildOfBoth.is_valid_for_parent("category_b") is True
        assert ChildOfBoth.is_valid_for_parent("category_c") is False

    def test_is_valid_for_parent_without_restrictions(self):
        """Test is_valid_for_parent returns True when no parent restriction."""

        class UnrestrictedChild(HierarchicalInterface):
            slug = "unrestricted"
            # No parent_slug or parent_slugs

        assert UnrestrictedChild.is_valid_for_parent("any_parent") is True
        assert UnrestrictedChild.is_valid_for_parent("another_parent") is True

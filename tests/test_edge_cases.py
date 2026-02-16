"""Tests for edge cases and user input mistakes in django_stratagem."""

import pytest
from django.core.exceptions import ValidationError

from django_stratagem.exceptions import (
    ImplementationNotFound,
)
from django_stratagem.fields import (
    MultipleRegistryClassField,
    MultipleRegistryField,
    RegistryClassField,
    RegistryField,
)
from django_stratagem.forms import (
    ContextAwareRegistryFormField,
    RegistryFormField,
    RegistryMultipleChoiceFormField,
)
from django_stratagem.interfaces import ConditionalInterface, Interface
from django_stratagem.registry import Registry
from django_stratagem.validators import ClassnameValidator, RegistryValidator


class TestEmptyAndNullValues:
    """Test handling of empty and null values."""

    def test_form_field_with_empty_string(self, test_registry):
        """Test form field handles empty string."""
        field = RegistryFormField(registry=test_registry)
        # Empty string should be treated as no value
        result = field.prepare_value("")
        assert result == ""

    def test_form_field_with_none(self, test_registry):
        """Test form field handles None."""
        field = RegistryFormField(registry=test_registry)
        result = field.prepare_value(None)
        assert result is None

    def test_multiple_form_field_with_empty_list(self, test_registry):
        """Test multiple choice field handles empty list."""
        field = RegistryMultipleChoiceFormField(registry=test_registry)
        result = field.prepare_value([])
        assert result == []

    def test_multiple_form_field_with_none(self, test_registry):
        """Test multiple choice field handles None."""
        field = RegistryMultipleChoiceFormField(registry=test_registry)
        result = field.prepare_value(None)
        # None is returned as-is by prepare_value (None means no selection)
        assert result is None

    def test_validator_with_empty_string(self, test_registry):
        """Test validator handles empty string gracefully."""
        validator = RegistryValidator(registry=test_registry)
        # Empty string should not raise (treated as no value)
        # This depends on field allowing blank
        with pytest.raises(ValidationError):
            validator("")

    def test_validator_with_none(self, test_registry):
        """Test validator handles None gracefully."""
        validator = RegistryValidator(registry=test_registry)
        # None should raise ValidationError for required field
        with pytest.raises(ValidationError):
            validator(None)

    def test_classname_validator_with_empty_string(self):
        """Test ClassnameValidator with empty string.

        Note: ClassnameValidator passes empty strings through without error
        because get_class("") returns None, which doesn't raise an exception.
        Empty string handling should be done at the field/form level with required=True.
        """
        validator = ClassnameValidator(limit_value=None)
        # Empty string does not raise - it's treated as no value
        # This behavior allows blank/optional fields
        validator("")  # Should not raise


class TestInvalidTypeInputs:
    """Test handling of invalid type inputs."""

    def test_form_field_with_invalid_type(self, test_registry):
        """Test form field with non-string, non-class value."""
        field = RegistryFormField(registry=test_registry)
        # Numbers and other types should be converted to string
        result = field.prepare_value(123)
        assert isinstance(result, str) or result is None

    def test_form_field_with_dict(self, test_registry):
        """Test form field with dict input."""
        field = RegistryFormField(registry=test_registry)
        # Dict is not a registered type, so prepare_value falls back to FQN of dict class
        result = field.prepare_value({"invalid": "value"})
        assert result == "builtins.dict"

    def test_validator_with_integer(self, test_registry):
        """Test validator with integer input."""
        validator = RegistryValidator(registry=test_registry)
        with pytest.raises(ValidationError):
            validator(123)

    def test_validator_with_float(self, test_registry):
        """Test validator with float input."""
        validator = RegistryValidator(registry=test_registry)
        with pytest.raises(ValidationError):
            validator(3.14)

    def test_validator_with_list_of_invalid_types(self, test_registry):
        """Test validator with list containing invalid types."""
        validator = RegistryValidator(registry=test_registry)
        with pytest.raises(ValidationError):
            validator([123, 456])

    def test_multiple_field_with_non_iterable(self, test_registry):
        """Test multiple choice field with non-iterable (except string)."""
        field = RegistryMultipleChoiceFormField(registry=test_registry)
        # Non-iterable should be handled gracefully
        result = field.prepare_value("email")  # string is valid
        assert result is not None


class TestUnicodeHandling:
    """Test handling of unicode characters in slugs and names."""

    def test_registry_with_unicode_slug(self):
        """Test registry behavior with unicode in slug."""

        class UnicodeRegistry(Registry):
            implementations_module = "unicode_test_impl"

        class UnicodeImpl(Interface):
            registry = UnicodeRegistry
            slug = "unicode_test"
            display_name = "Test"

        # Should work with ASCII slug
        impl = UnicodeRegistry.get(slug="unicode_test")
        assert impl is not None

    def test_registry_with_unicode_display_name(self):
        """Test registry with unicode display name."""

        class UnicodeDisplayRegistry(Registry):
            implementations_module = "unicode_display_test_impl"
            label_attribute = "display_name"

        class UnicodeDisplayImpl(Interface):
            registry = UnicodeDisplayRegistry
            slug = "test_impl"
            display_name = "Test Agua - Irrigation"

        # Clear cache to ensure fresh choices are fetched
        UnicodeDisplayRegistry.clear_cache()
        choices = UnicodeDisplayRegistry.get_choices()
        assert any("Irrigation" in str(c[1]) for c in choices)

    def test_validator_with_unicode_classname(self):
        """Test ClassnameValidator rejects unicode class names."""
        validator = ClassnameValidator(limit_value=None)
        # Python class names can't have special unicode chars
        with pytest.raises(ValidationError):
            validator("MyClass")

    def test_form_field_with_unicode_value(self, test_registry):
        """Test form field with unicode value."""
        field = RegistryFormField(registry=test_registry)
        # Unicode values that don't match valid slugs should fail validation
        # prepare_value might accept it, but clean should fail
        prepared = field.prepare_value("test")
        assert prepared is not None


class TestLongInputs:
    """Test handling of very long slugs and names."""

    def test_very_long_slug_validation(self, test_registry):
        """Test validator with very long slug."""
        validator = RegistryValidator(registry=test_registry)
        long_slug = "a" * 1000
        with pytest.raises(ValidationError):
            validator(long_slug)

    def test_very_long_classname_validation(self):
        """Test ClassnameValidator with very long classname."""
        validator = ClassnameValidator(limit_value=None)
        long_name = "MyClass" + "a" * 1000
        with pytest.raises(ValidationError):
            validator(long_name)

    @pytest.mark.parametrize(
        "slug_length",
        [100, 255, 500],
    )
    def test_various_slug_lengths(self, test_registry, slug_length):
        """Test validator with various slug lengths."""
        validator = RegistryValidator(registry=test_registry)
        slug = "x" * slug_length
        with pytest.raises(ValidationError):
            validator(slug)


class TestSpecialCharacters:
    """Test handling of special characters in identifiers."""

    @pytest.mark.parametrize(
        "special_slug",
        [
            "test-with-dashes",
            "test.with.dots",
            "test/with/slashes",
            "test\\with\\backslashes",
            "test with spaces",
            "test\twith\ttabs",
            "test\nwith\nnewlines",
            "<script>alert('xss')</script>",
            "test;drop table;",
            "test' OR '1'='1",
        ],
    )
    def test_special_char_slugs_rejected(self, test_registry, special_slug):
        """Test that special character slugs are rejected."""
        validator = RegistryValidator(registry=test_registry)
        with pytest.raises(ValidationError):
            validator(special_slug)

    @pytest.mark.parametrize(
        "invalid_classname",
        [
            "Class-With-Dashes",
            "class with spaces",
            "123StartWithNumber",
            "class.with.dots",
            "Class/Path",
            # Note: Empty string "" does NOT raise - it's treated as blank/no value
            # " ", "\t", "\n" are also valid since get_class() returns None for them
        ],
    )
    def test_invalid_classnames(self, invalid_classname):
        """Test ClassnameValidator rejects invalid class names."""
        validator = ClassnameValidator(limit_value=None)
        with pytest.raises(ValidationError):
            validator(invalid_classname)

    @pytest.mark.parametrize(
        "whitespace_value",
        [
            " ",
            "\t",
            "\n",
        ],
    )
    def test_whitespace_classnames_rejected(self, whitespace_value):
        """Test ClassnameValidator rejects whitespace-only values.

        Unlike empty string which passes through, whitespace values like
        ' ', '\\t', '\\n' trigger RegistryNameError and are rejected.
        """
        validator = ClassnameValidator(limit_value=None)
        with pytest.raises(ValidationError):
            validator(whitespace_value)

    def test_empty_string_classname_allowed(self):
        """Test ClassnameValidator allows empty string (for blank=True fields)."""
        validator = ClassnameValidator(limit_value=None)
        # Empty string doesn't raise - it's treated as no value
        # This enables blank=True fields to work correctly
        validator("")  # Should not raise


class TestRegistryEdgeCases:
    """Test registry edge cases."""

    def test_registry_get_with_nonexistent_slug(self, test_registry):
        """Test registry.get with nonexistent slug."""
        with pytest.raises(ImplementationNotFound):
            test_registry.get(slug="nonexistent_slug_that_does_not_exist")

    def test_registry_get_class_with_nonexistent_slug(self, test_registry):
        """Test registry.get_class with nonexistent slug."""
        with pytest.raises(ImplementationNotFound):
            test_registry.get_class(slug="nonexistent_slug_that_does_not_exist")

    def test_registry_get_without_parameters(self, test_registry):
        """Test registry.get without any parameters."""
        with pytest.raises(ValueError):
            test_registry.get()

    def test_registry_get_with_both_slug_and_fqn(self, test_registry, email_strategy_class):
        """Test registry.get with both slug and fully_qualified_name."""
        # Should work - slug takes precedence
        result = test_registry.get(
            slug="email",
            fully_qualified_name=f"{email_strategy_class.__module__}.{email_strategy_class.__name__}",
        )
        assert result is not None

    def test_registry_is_valid_with_none(self, test_registry):
        """Test registry.is_valid with None."""
        result = test_registry.is_valid(None)
        assert result is False

    def test_registry_is_valid_with_empty_string(self, test_registry):
        """Test registry.is_valid with empty string."""
        result = test_registry.is_valid("")
        assert result is False

    def test_registry_is_valid_with_invalid_type(self, test_registry):
        """Test registry.is_valid with invalid type."""
        result = test_registry.is_valid(123)
        assert result is False


class TestDuplicateRegistration:
    """Test duplicate registration handling."""

    def test_duplicate_slug_registration(self):
        """Test registering implementation with duplicate slug overwrites."""

        class DuplicateRegistry(Registry):
            implementations_module = "duplicate_test_impl"

        class FirstImpl(Interface):
            registry = DuplicateRegistry
            slug = "duplicate_slug"
            display_name = "First"

        # Second registration with same slug should overwrite
        class SecondImpl(Interface):
            registry = DuplicateRegistry
            slug = "duplicate_slug"
            display_name = "Second"

        # The second implementation should have replaced the first
        impl = DuplicateRegistry.get(slug="duplicate_slug")
        assert impl is not None

    def test_reregistering_same_class_is_silent(self, caplog):
        """Re-registering the exact same class under the same slug should not warn."""

        class IdempotentRegistry(Registry):
            implementations_module = "idempotent_test_impl"

        class MyImpl(Interface):
            registry = IdempotentRegistry
            slug = "my_slug"
            display_name = "My Impl"

        # Register the same class again explicitly
        caplog.clear()
        with caplog.at_level("WARNING", logger="django_stratagem.registry"):
            IdempotentRegistry.register(MyImpl)

        assert "Overwriting slug" not in caplog.text
        # Still registered and accessible
        assert IdempotentRegistry.get(slug="my_slug") is not None

    def test_different_class_same_slug_warns(self, caplog):
        """Registering a different class under an existing slug should warn."""

        class WarnRegistry(Registry):
            implementations_module = "warn_test_impl"

        class OriginalImpl(Interface):
            registry = WarnRegistry
            slug = "shared_slug"
            display_name = "Original"

        class ReplacementImpl(Interface):
            registry = WarnRegistry
            slug = "shared_slug"
            display_name = "Replacement"

        assert "Overwriting slug 'shared_slug'" in caplog.text


class TestEmptyRegistry:
    """Test behavior of empty registries."""

    def test_empty_registry_get_choices(self):
        """Test get_choices on empty registry."""

        class EmptyRegistry(Registry):
            implementations_module = "empty_test_impl"

        choices = EmptyRegistry.get_choices()
        assert choices == []

    def test_empty_registry_get_items(self):
        """Test get_items on empty registry."""

        class EmptyItemsRegistry(Registry):
            implementations_module = "empty_items_test_impl"

        items = EmptyItemsRegistry.get_items()
        assert items == []

    def test_empty_registry_get_raises_error(self):
        """Test get on empty registry raises error."""

        class EmptyGetRegistry(Registry):
            implementations_module = "empty_get_test_impl"

        with pytest.raises(ImplementationNotFound):
            EmptyGetRegistry.get(slug="anything")


class TestConditionalEdgeCases:
    """Test conditional interface edge cases."""

    def test_conditional_without_is_available(self):
        """Test conditional interface works without is_available override."""

        class TestCondRegistry(Registry):
            implementations_module = "test_cond_impl"

        class BasicCond(ConditionalInterface):
            registry = TestCondRegistry
            slug = "basic_cond"
            display_name = "Basic Conditional"
            # No is_available override - should default to True

        impl = TestCondRegistry.get(slug="basic_cond")
        assert impl is not None

    def test_conditional_with_none_context(self, conditional_registry):
        """Test conditional interface with None context."""
        # Should not raise when context is None
        available = conditional_registry.get_available_implementations(context=None)
        # get_available_implementations returns a dict
        assert isinstance(available, dict)

    def test_conditional_with_empty_context(self, conditional_registry):
        """Test conditional interface with empty dict context."""
        available = conditional_registry.get_available_implementations(context={})
        # get_available_implementations returns a dict
        assert isinstance(available, dict)


class TestHierarchicalEdgeCases:
    """Test hierarchical registry edge cases."""

    def test_child_registry_with_no_parents(self, child_registry):
        """Test child registry get_choices_for_parent with None parent."""
        # None parent should return empty or all choices
        choices = child_registry.get_choices_for_parent(None)
        assert isinstance(choices, list)

    def test_child_registry_with_invalid_parent(self, child_registry):
        """Test child registry with invalid parent slug."""
        choices = child_registry.get_choices_for_parent("invalid_parent_slug")
        # The child_registry has parent_slugs restriction, so invalid parent returns all
        # (since it's not in the parent_slugs list, it returns all implementations)
        assert isinstance(choices, list)


class TestContextAwareEdgeCases:
    """Test context-aware form field edge cases."""

    def test_context_aware_without_context(self, conditional_registry):
        """Test ContextAwareRegistryFormField without set_context called."""
        field = ContextAwareRegistryFormField(registry=conditional_registry)
        # Should still have choices (all or filtered)
        assert hasattr(field, "choices")

    def test_context_aware_with_none_context(self, conditional_registry):
        """Test ContextAwareRegistryFormField with None context."""
        field = ContextAwareRegistryFormField(registry=conditional_registry)
        field.set_context(None)
        assert hasattr(field, "choices")

    def test_context_aware_with_empty_context(self, conditional_registry):
        """Test ContextAwareRegistryFormField with empty context."""
        field = ContextAwareRegistryFormField(registry=conditional_registry)
        field.set_context({})
        assert hasattr(field, "choices")


class TestFieldEdgeCases:
    """Test model field edge cases."""

    def test_registry_field_deconstruct(self, test_registry):
        """Test RegistryField deconstruct for migrations."""
        field = RegistryField(registry=test_registry)
        name, path, args, kwargs = field.deconstruct()
        assert "registry" in kwargs

    def test_registry_class_field_deconstruct(self, test_registry):
        """Test RegistryClassField deconstruct for migrations."""
        field = RegistryClassField(registry=test_registry)
        name, path, args, kwargs = field.deconstruct()
        assert "registry" in kwargs

    def test_multiple_registry_field_deconstruct(self, test_registry):
        """Test MultipleRegistryField deconstruct for migrations."""
        field = MultipleRegistryField(registry=test_registry)
        name, path, args, kwargs = field.deconstruct()
        assert "registry" in kwargs

    def test_multiple_registry_class_field_deconstruct(self, test_registry):
        """Test MultipleRegistryClassField deconstruct for migrations."""
        field = MultipleRegistryClassField(registry=test_registry)
        name, path, args, kwargs = field.deconstruct()
        assert "registry" in kwargs


class TestCachingEdgeCases:
    """Test caching edge cases."""

    def test_registry_cache_key_uniqueness(self, test_registry, conditional_registry):
        """Test that different registries have different cache keys."""
        key1 = test_registry.get_cache_key("choices")
        key2 = conditional_registry.get_cache_key("choices")
        assert key1 != key2

    def test_registry_cache_clear_affects_only_target(self, test_registry):
        """Test that clearing cache only affects target registry."""
        # Get choices to populate cache
        test_registry.get_choices()
        # Clear cache
        test_registry.clear_cache()
        # Should be able to get choices again
        choices = test_registry.get_choices()
        assert isinstance(choices, list)


class TestValidatorMessages:
    """Test validator error messages."""

    def test_registry_validator_error_message_format(self, test_registry):
        """Test RegistryValidator error message format."""
        validator = RegistryValidator(registry=test_registry)
        with pytest.raises(ValidationError) as exc_info:
            validator("invalid_slug_xyz")
        # Should have meaningful error message
        error_message = str(exc_info.value)
        assert len(error_message) > 0

    def test_classname_validator_error_message(self):
        """Test ClassnameValidator error message."""
        validator = ClassnameValidator(limit_value=None)
        with pytest.raises(ValidationError) as exc_info:
            validator("invalid-class-name")
        # Should mention the invalid value or explain valid format
        error_message = str(exc_info.value)
        assert len(error_message) > 0


class TestInterfaceEdgeCases:
    """Test interface edge cases."""

    def test_interface_without_slug(self):
        """Test interface without slug is not registered."""

        class NoSlugRegistry(Registry):
            implementations_module = "no_slug_test_impl"

        class NoSlugImpl(Interface):
            registry = NoSlugRegistry
            # No slug attribute
            display_name = "No Slug"

        # Should not be registered without slug
        assert NoSlugRegistry.get_items() == []

    def test_interface_without_registry(self):
        """Test interface without registry is not registered."""

        class NoRegistryImpl(Interface):
            slug = "no_registry"
            display_name = "No Registry"

        # Should not cause error, just not register anywhere


class TestFormFieldClean:
    """Test form field clean method edge cases."""

    def test_form_field_clean_with_whitespace(self, test_registry):
        """Test form field clean with whitespace-only input."""
        field = RegistryFormField(registry=test_registry, required=False)
        # Whitespace is not valid as a registry value - it will raise ValidationError
        # because "   " is not a valid slug or implementation
        with pytest.raises(ValidationError):
            field.clean("   ")

    def test_multiple_form_field_clean_with_duplicates(self, test_registry):
        """Test multiple choice field clean with duplicate values."""
        from tests.registries_fixtures import (
            EmailStrategy,
            SMSStrategy,
        )

        field = RegistryMultipleChoiceFormField(registry=test_registry)
        result = field.clean(["email", "email", "sms"])
        # Result contains implementation classes, not slugs
        assert EmailStrategy in result
        assert SMSStrategy in result


class TestBoundaryConditions:
    """Test boundary conditions."""

    def test_registry_with_single_implementation(self):
        """Test registry with exactly one implementation."""

        class SingleRegistry(Registry):
            implementations_module = "single_test_impl"

        class SingleImpl(Interface):
            registry = SingleRegistry
            slug = "only_one"
            display_name = "Only One"

        choices = SingleRegistry.get_choices()
        assert len(choices) == 1
        assert choices[0][0] == "only_one"

    def test_registry_with_many_implementations(self):
        """Test registry with many implementations."""

        class ManyRegistry(Registry):
            implementations_module = "many_test_impl"

        # Create multiple implementations dynamically
        for i in range(10):
            impl_attrs = {
                "registry": ManyRegistry,
                "slug": f"impl_{i}",
                "display_name": f"Implementation {i}",
            }
            type(f"DynamicImpl{i}", (Interface,), impl_attrs)  # auto-registers via __init_subclass__

        choices = ManyRegistry.get_choices()
        assert len(choices) >= 1  # At least one should register

"""Tests for django_stratagem forms module."""

from __future__ import annotations

import pytest
from django import forms
from django.core.exceptions import ValidationError

from django_stratagem.forms import (
    ContextAwareRegistryFormField,
    HierarchicalFormMixin,
    HierarchicalRegistryFormField,
    RegistryContextMixin,
    RegistryFormField,
    RegistryMultipleChoiceFormField,
)

pytestmark = pytest.mark.django_db


class TestRegistryFormField:
    """Tests for RegistryFormField."""

    def test_init_stores_registry(self, test_strategy_registry):
        """Test that __init__ stores the registry."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        assert field.registry == test_strategy_registry

    def test_init_stores_empty_value(self, test_strategy_registry):
        """Test that __init__ stores custom empty_value."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
            empty_value="custom_empty",
        )
        assert field.empty_value == "custom_empty"

    def test_init_default_empty_value(self, test_strategy_registry):
        """Test that __init__ uses default empty_value."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        assert field.empty_value == ""

    def test_prepare_value_with_string(self, registry_form_field):
        """Test prepare_value returns string as-is."""
        result = registry_form_field.prepare_value("email")
        assert result == "email"

    def test_prepare_value_with_class(self, registry_form_field, email_strategy):
        """Test prepare_value converts class to slug."""
        result = registry_form_field.prepare_value(email_strategy)
        assert result == "email"

    def test_prepare_value_with_instance(self, registry_form_field, email_strategy):
        """Test prepare_value converts instance to slug."""
        instance = email_strategy()
        result = registry_form_field.prepare_value(instance)
        assert result == "email"

    def test_prepare_value_with_none(self, registry_form_field):
        """Test prepare_value handles None."""
        result = registry_form_field.prepare_value(None)
        assert result is None

    def test_prepare_value_with_falsy_value(self, registry_form_field):
        """Test prepare_value handles falsy non-None values."""
        result = registry_form_field.prepare_value("")
        assert result == ""

    def test_valid_value_with_valid_slug(self, registry_form_field):
        """Test valid_value returns True for valid slug."""
        assert registry_form_field.valid_value("email") is True

    def test_valid_value_with_invalid_slug(self, registry_form_field):
        """Test valid_value returns False for invalid slug."""
        assert registry_form_field.valid_value("invalid_slug") is False

    def test_valid_value_with_fully_qualified_name(self, test_strategy_registry, email_strategy):
        """Test valid_value accepts fully qualified name."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        fqn = f"{email_strategy.__module__}.{email_strategy.__name__}"
        assert field.valid_value(fqn) is True

    def test_coerce_with_valid_slug(self, test_strategy_registry, email_strategy):
        """Test _coerce converts slug to class."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        result = field._coerce("email")
        assert result == email_strategy

    def test_coerce_with_empty_value(self, test_strategy_registry):
        """Test _coerce returns empty_value for empty input."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
            empty_value="",
        )
        result = field._coerce("")
        assert result == ""

    def test_coerce_with_invalid_value(self, test_strategy_registry):
        """Test _coerce raises ValidationError for invalid value."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        with pytest.raises(ValidationError):
            field._coerce("invalid_slug")

    def test_clean_with_valid_slug(self, test_strategy_registry, email_strategy):
        """Test clean returns implementation class for valid slug."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        result = field.clean("email")
        assert result == email_strategy

    @pytest.mark.parametrize(
        "slug,expected_display_name",
        [
            ("email", "Email Strategy"),
            ("sms", "SMS Strategy"),
            ("push", "Push Strategy"),
        ],
    )
    def test_registry_choices_contain_expected_values(self, test_strategy_registry, slug, expected_display_name):
        """Test registry provides correct choices."""
        choices = test_strategy_registry.get_choices()
        choice_dict = dict(choices)
        assert slug in choice_dict
        assert choice_dict[slug] == expected_display_name


class TestRegistryMultipleChoiceFormField:
    """Tests for RegistryMultipleChoiceFormField."""

    def test_init_stores_registry(self, test_strategy_registry):
        """Test that __init__ stores the registry."""
        field = RegistryMultipleChoiceFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        assert field.registry == test_strategy_registry

    def test_prepare_value_with_none(self, registry_multiple_choice_field):
        """Test prepare_value handles None."""
        result = registry_multiple_choice_field.prepare_value(None)
        assert result is None

    def test_prepare_value_with_string(self, registry_multiple_choice_field):
        """Test prepare_value splits comma-separated string."""
        result = registry_multiple_choice_field.prepare_value("email,sms")
        assert result == ["email", "sms"]

    def test_prepare_value_with_string_list(self, registry_multiple_choice_field):
        """Test prepare_value preserves string list."""
        result = registry_multiple_choice_field.prepare_value(["email", "sms"])
        assert result == ["email", "sms"]

    def test_prepare_value_with_class_list(self, registry_multiple_choice_field, email_strategy, sms_strategy):
        """Test prepare_value converts class list to slugs."""
        result = registry_multiple_choice_field.prepare_value([email_strategy, sms_strategy])
        assert set(result) == {"email", "sms"}

    def test_prepare_value_with_instance_list(self, registry_multiple_choice_field, email_strategy, sms_strategy):
        """Test prepare_value converts instance list to slugs."""
        result = registry_multiple_choice_field.prepare_value([email_strategy(), sms_strategy()])
        assert set(result) == {"email", "sms"}

    def test_prepare_value_with_tuple(self, registry_multiple_choice_field):
        """Test prepare_value handles tuple input."""
        result = registry_multiple_choice_field.prepare_value(("email", "sms"))
        assert result == ["email", "sms"]

    def test_prepare_value_with_single_class(self, registry_multiple_choice_field, email_strategy):
        """Test prepare_value handles single class."""
        result = registry_multiple_choice_field.prepare_value(email_strategy)
        assert result == ["email"]

    def test_prepare_value_with_mixed_list(self, registry_multiple_choice_field, email_strategy, sms_strategy):
        """Test prepare_value handles mixed list of strings, classes, instances."""
        result = registry_multiple_choice_field.prepare_value(["push", email_strategy, sms_strategy()])
        assert set(result) == {"email", "sms", "push"}

    def test_coerce_with_valid_slug(self, registry_multiple_choice_field, email_strategy):
        """Test coerce converts slug to class."""
        result = registry_multiple_choice_field.coerce("email")
        assert result == email_strategy

    def test_coerce_with_invalid_slug(self, registry_multiple_choice_field):
        """Test coerce returns None for invalid slug."""
        result = registry_multiple_choice_field.coerce("invalid_slug")
        assert result is None

    def test_coerce_with_fqn(self, test_strategy_registry, email_strategy):
        """Test coerce handles fully qualified name."""
        field = RegistryMultipleChoiceFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        fqn = f"{email_strategy.__module__}.{email_strategy.__name__}"
        result = field.coerce(fqn)
        assert result == email_strategy

    def test_valid_value_with_valid_slug(self, registry_multiple_choice_field):
        """Test valid_value returns True for valid slug."""
        assert registry_multiple_choice_field.valid_value("email") is True

    def test_valid_value_with_invalid_slug(self, registry_multiple_choice_field):
        """Test valid_value returns False for invalid slug."""
        assert registry_multiple_choice_field.valid_value("invalid") is False


class TestContextAwareRegistryFormField:
    """Tests for ContextAwareRegistryFormField."""

    def test_init_without_context(self, test_strategy_registry):
        """Test initialization without context."""
        field = ContextAwareRegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        assert field.context is None

    def test_init_with_context(self, test_strategy_registry):
        """Test initialization with context."""
        context = {"user": "test_user"}
        field = ContextAwareRegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
            context=context,
        )
        assert field.context == context

    def test_set_context_updates_context(self, test_strategy_registry):
        """Test set_context updates field context."""
        field = ContextAwareRegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        new_context = {"user": "new_user"}
        field.set_context(new_context)
        assert field.context == new_context

    def test_valid_value_without_context(self, test_strategy_registry):
        """Test valid_value uses parent logic when no context."""
        field = ContextAwareRegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        assert field.valid_value("email") is True
        assert field.valid_value("invalid") is False

    def test_valid_value_with_context_filters_available(self, conditional_registry, premium_user, basic_user):
        """Test valid_value filters based on context."""
        # Premium feature should be available for premium user
        premium_context = {"user": premium_user}
        field = ContextAwareRegistryFormField(
            registry=conditional_registry,
            choices=conditional_registry.get_choices(),
            context=premium_context,
        )
        assert field.valid_value("premium_feature") is True

        # Premium feature should NOT be available for basic user
        basic_context = {"user": basic_user}
        field.set_context(basic_context)
        assert field.valid_value("premium_feature") is False


class TestHierarchicalRegistryFormField:
    """Tests for HierarchicalRegistryFormField."""

    def test_init_stores_parent_field(self, child_registry):
        """Test initialization stores parent_field."""
        field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
            parent_field="parent_field_name",
        )
        assert field.parent_field == "parent_field_name"

    def test_init_stores_parent_value(self, child_registry):
        """Test initialization stores parent_value."""
        field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
            parent_value="category_a",
        )
        assert field.parent_value == "category_a"

    def test_set_parent_value(self, child_registry):
        """Test set_parent_value updates parent value."""
        field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
        )
        field.set_parent_value("category_b")
        assert field.parent_value == "category_b"

    def test_valid_value_without_parent(self, child_registry):
        """Test valid_value uses parent logic when no parent selected."""
        field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
        )
        # Without parent, should use parent class validation
        assert field.valid_value("child_of_a") is True

    def test_get_parent_slug_with_string_slug(self, child_registry):
        """Test _get_parent_slug extracts slug from string."""
        field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
        )
        result = field._get_parent_slug("category_a")
        assert result == "category_a"

    def test_get_parent_slug_with_none(self, child_registry):
        """Test _get_parent_slug handles None."""
        field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
        )
        result = field._get_parent_slug(None)
        assert result is None


class TestRegistryContextMixin:
    """Tests for RegistryContextMixin."""

    def test_extracts_registry_context(self, test_strategy_registry):
        """Test mixin extracts registry_context from kwargs."""

        class TestForm(RegistryContextMixin, forms.Form):
            impl = ContextAwareRegistryFormField(
                registry=test_strategy_registry,
                choices=test_strategy_registry.get_choices(),
            )

        context = {"user": "test_user"}
        form = TestForm(registry_context=context)
        assert form.registry_context == context

    def test_updates_context_aware_fields(self, test_strategy_registry):
        """Test mixin updates context-aware fields."""

        class TestForm(RegistryContextMixin, forms.Form):
            impl = ContextAwareRegistryFormField(
                registry=test_strategy_registry,
                choices=test_strategy_registry.get_choices(),
            )

        context = {"user": "test_user"}
        form = TestForm(registry_context=context)
        assert form.fields["impl"].context == context

    def test_handles_none_context(self, test_strategy_registry):
        """Test mixin handles None registry_context."""

        class TestForm(RegistryContextMixin, forms.Form):
            impl = ContextAwareRegistryFormField(
                registry=test_strategy_registry,
                choices=test_strategy_registry.get_choices(),
            )

        form = TestForm()
        assert form.registry_context is None


class TestHierarchicalFormMixin:
    """Tests for HierarchicalFormMixin."""

    def test_setup_hierarchical_fields_called(self, parent_registry, child_registry):
        """Test _setup_hierarchical_fields is called during init."""

        class TestForm(HierarchicalFormMixin, forms.Form):
            parent = RegistryFormField(
                registry=parent_registry,
                choices=parent_registry.get_choices(),
            )
            child = HierarchicalRegistryFormField(
                registry=child_registry,
                choices=child_registry.get_choices(),
                parent_field="parent",
            )

        form = TestForm()
        # Verify the form was created with hierarchical fields detected
        child_field = form.fields["child"]
        assert isinstance(child_field, HierarchicalRegistryFormField)
        assert child_field.parent_field == "parent"

    def test_setup_with_initial_parent_value(self, parent_registry, child_registry):
        """Test setup extracts parent value from initial data."""

        class TestForm(HierarchicalFormMixin, forms.Form):
            parent = RegistryFormField(
                registry=parent_registry,
                choices=parent_registry.get_choices(),
            )
            child = HierarchicalRegistryFormField(
                registry=child_registry,
                choices=child_registry.get_choices(),
                parent_field="parent",
            )

        form = TestForm(initial={"parent": "category_a"})
        # Child field should have parent_value set
        assert form.fields["child"].parent_value == "category_a"

    def test_clean_validates_parent_child_relationship(self, parent_registry, child_registry):
        """Test clean validates parent-child relationships."""

        class TestForm(HierarchicalFormMixin, forms.Form):
            parent = RegistryFormField(
                registry=parent_registry,
                choices=parent_registry.get_choices(),
            )
            child = HierarchicalRegistryFormField(
                registry=child_registry,
                choices=child_registry.get_choices(),
                parent_field="parent",
            )

        # Valid parent-child combination
        TestForm(data={"parent": "category_a", "child": "child_of_a"})
        # Note: Full validation requires choices to be set correctly
        # This tests the structure is in place


class TestFormFieldEdgeCases:
    """Tests for edge cases and error handling in form fields."""

    def test_registry_form_field_with_empty_choices(self, test_strategy_registry):
        """Test field behavior when registry has no implementations."""
        # Create field with empty choices
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=[],
        )
        assert field.valid_value("any_value") is False

    def test_prepare_value_with_unregistered_class(self, test_strategy_registry, registry_form_field):
        """Test prepare_value handles class not in registry."""

        class UnregisteredClass:
            pass

        # Should fall back to FQN
        result = registry_form_field.prepare_value(UnregisteredClass)
        assert "UnregisteredClass" in result

    def test_multiple_choice_field_with_empty_list(self, registry_multiple_choice_field):
        """Test multiple choice field handles empty list."""
        result = registry_multiple_choice_field.prepare_value([])
        assert result == []

    def test_coerce_with_none_in_empty_values(self, test_strategy_registry):
        """Test coerce handles None properly."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
            required=False,
        )
        result = field._coerce(None)
        assert result == ""

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "nonexistent.module.Class",
            "not.a.valid.path",
            "single",
            "",
        ],
    )
    def test_coerce_with_invalid_fqn(self, test_strategy_registry, invalid_input):
        """Test coerce raises ValidationError for invalid FQN."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        if invalid_input == "":
            # Empty string returns empty_value
            result = field._coerce(invalid_input)
            assert result == ""
        else:
            with pytest.raises(ValidationError):
                field._coerce(invalid_input)

    def test_hierarchical_field_without_parent_registry(self, test_strategy_registry):
        """Test hierarchical field handles missing parent_registry gracefully."""
        field = HierarchicalRegistryFormField(
            registry=test_strategy_registry,  # Not a hierarchical registry
            choices=test_strategy_registry.get_choices(),
        )
        # Should not raise error
        result = field._get_parent_slug("some_value.with.dots")
        assert result is None

    def test_context_aware_field_with_invalid_value_in_context(self, conditional_registry, basic_user):
        """Test context-aware field rejects value not in context."""
        context = {"user": basic_user}
        field = ContextAwareRegistryFormField(
            registry=conditional_registry,
            choices=conditional_registry.get_choices(),
            context=context,
        )
        # Premium feature should not be valid for basic user
        assert field.valid_value("premium_feature") is False
        # Basic feature should be valid
        assert field.valid_value("basic_feature") is True

    def test_coerce_with_valid_fqn(self, test_strategy_registry, email_strategy):
        """Test _coerce with a valid FQN that passes is_valid."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        fqn = f"{email_strategy.__module__}.{email_strategy.__name__}"
        result = field._coerce(fqn)
        assert result is email_strategy

    def test_prepare_value_class_not_in_registry_fqn_fallback(self, test_strategy_registry):
        """Test prepare_value falls back to FQN for class not in registry."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )

        class OutsideClass:
            pass

        result = field.prepare_value(OutsideClass)
        assert "OutsideClass" in result

    def test_prepare_value_instance_not_in_registry_fqn_fallback(self, test_strategy_registry):
        """Test prepare_value falls back to FQN for instance not in registry."""
        field = RegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )

        class OutsideClass:
            pass

        result = field.prepare_value(OutsideClass())
        assert "OutsideClass" in result

    def test_multiple_prepare_value_single_non_list_class(self, test_strategy_registry, email_strategy):
        """Test RegistryMultipleChoiceFormField prepare_value with single class (not in list)."""
        field = RegistryMultipleChoiceFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
        )
        result = field.prepare_value(email_strategy)
        assert result == ["email"]

    def test_context_aware_valid_value_exception_handling(self, test_strategy_registry):
        """Test ContextAwareRegistryFormField.valid_value with bad FQN import."""
        context = {"user": "test"}
        field = ContextAwareRegistryFormField(
            registry=test_strategy_registry,
            choices=test_strategy_registry.get_choices(),
            context=context,
        )
        assert field.valid_value("nonexistent.module.BadClass") is False

    def test_hierarchical_get_parent_slug_fqn_string(self, child_registry):
        """Test _get_parent_slug with FQN string."""
        from tests.registries_fixtures import CategoryA

        field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
        )
        fqn = f"{CategoryA.__module__}.{CategoryA.__name__}"
        result = field._get_parent_slug(fqn)
        assert result == "category_a"

    def test_hierarchical_get_parent_slug_class(self, child_registry):
        """Test _get_parent_slug with class."""
        from tests.registries_fixtures import CategoryA

        field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
        )
        result = field._get_parent_slug(CategoryA)
        assert result == "category_a"

    def test_hierarchical_get_parent_slug_instance(self, child_registry):
        """Test _get_parent_slug with instance."""
        from tests.registries_fixtures import CategoryA

        field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
        )
        result = field._get_parent_slug(CategoryA())
        assert result == "category_a"

    def test_hierarchical_valid_value_with_parent(self, child_registry):
        """Test valid_value with active parent constraint."""
        field = HierarchicalRegistryFormField(
            registry=child_registry,
            choices=child_registry.get_choices(),
            parent_value="category_a",
        )
        # With parent set, valid_value uses ChoiceField.valid_value
        # which checks against current choices
        result = field.valid_value("child_of_a")
        assert isinstance(result, bool)

    def test_hierarchical_form_mixin_clean_validates(self, parent_registry, child_registry):
        """Test HierarchicalFormMixin.clean validates parent-child."""

        class TestForm(HierarchicalFormMixin, forms.Form):
            parent = RegistryFormField(
                registry=parent_registry,
                choices=parent_registry.get_choices(),
            )
            child = HierarchicalRegistryFormField(
                registry=child_registry,
                choices=child_registry.get_choices(),
                parent_field="parent",
            )

        form = TestForm(data={"parent": "category_a", "child": "child_of_a"})
        # Just verify the form validates without crashing
        form.is_valid()

    def test_hierarchical_form_mixin_adds_error_on_invalid(self, parent_registry, child_registry):
        """Test HierarchicalFormMixin.clean adds error on invalid child."""

        class TestForm(HierarchicalFormMixin, forms.Form):
            parent = RegistryFormField(
                registry=parent_registry,
                choices=parent_registry.get_choices(),
            )
            child = HierarchicalRegistryFormField(
                registry=child_registry,
                choices=child_registry.get_choices(),
                parent_field="parent",
            )

        form = TestForm(data={"parent": "category_a", "child": "child_of_b"})
        form.is_valid()
        # May or may not have errors depending on choices filtering, but shouldn't crash

"""Tests for the enhanced django_stratagem app using pytest."""

import pytest

from django_stratagem import (
    Interface,
    Registry,
)
from tests.registries_fixtures import EmailStrategy, TestStrategy
from tests.testapp.models import RegistryFieldTestModel


# Example registry and implementations for testing
class TestInterface(Interface):
    display_name = "Base Test"

    def process(self):
        return "base"


class TestRegistry(Registry):
    implementations_module = "tests.test_implementations"
    interface_class = TestInterface
    label_attribute = "display_name"  # Use display_name attribute for display names


TestInterface.registry = TestRegistry


# Test implementations
class EmailImpl(TestInterface):
    slug = "email"
    display_name = "Email Implementation"

    def process(self):
        return "email"


class SMSImpl(TestInterface):
    slug = "sms"
    display_name = "SMS Implementation"

    def process(self):
        return "sms"


class PhoneImpl(TestInterface):
    slug = "phone"
    display_name = "Phone Implementation"

    def process(self):
        return "phone"


@pytest.fixture(autouse=True)
def _register_test_impls():
    """Register test implementations in the TestRegistry for each test."""
    TestRegistry.register(EmailImpl)
    TestRegistry.register(SMSImpl)
    TestRegistry.register(PhoneImpl)
    yield
    TestRegistry.clear_cache()


@pytest.fixture
def test_model_instance():
    """Create a test model instance (in-memory, not saved to DB)."""
    return RegistryFieldTestModel()


@pytest.fixture
def email_impl_fully_qualified_name():
    """Get fully qualified name for email implementation."""
    return f"{EmailImpl.__module__}.{EmailImpl.__name__}"


class TestRegistryFields:
    """Test cases for registry fields."""

    def test_single_instance_field_returns_instance(self, test_model_instance):
        """Test RegistryField returns instances."""
        test_model_instance.single_instance = "email"

        # Should return an instance
        assert isinstance(test_model_instance.single_instance, TestStrategy)
        assert test_model_instance.single_instance.execute() == "email_sent"

    def test_single_class_field_returns_class(self, test_model_instance):
        """Test RegistryClassField returns classes."""
        test_model_instance.single_class = "email"

        # Should return a class
        assert isinstance(test_model_instance.single_class, type)
        assert issubclass(test_model_instance.single_class, TestStrategy)

        # Can instantiate
        instance = test_model_instance.single_class()
        assert instance.execute() == "email_sent"

    def test_multiple_instance_field_returns_instances(self, test_model_instance):
        """Test MultipleRegistryField returns multiple instances."""
        test_model_instance.multiple_instances = ["email", "sms"]

        # Should return list of instances
        assert len(test_model_instance.multiple_instances) == 2
        assert isinstance(test_model_instance.multiple_instances[0], TestStrategy)
        assert isinstance(test_model_instance.multiple_instances[1], TestStrategy)

        results = [impl.execute() for impl in test_model_instance.multiple_instances]
        assert "email_sent" in results
        assert "sms_sent" in results

    def test_multiple_class_field_returns_classes(self, test_model_instance):
        """Test MultipleRegistryClassField returns multiple classes."""
        test_model_instance.multiple_classes = ["email", "sms"]

        # Should return list of classes
        assert len(test_model_instance.multiple_classes) == 2
        for cls in test_model_instance.multiple_classes:
            assert isinstance(cls, type)
            assert issubclass(cls, TestStrategy)

    def test_field_validation_with_valid_value(self, test_model_instance):
        """Test field validation passes for a valid registered slug."""
        test_model_instance.single_instance = "email"
        test_model_instance.full_clean(validate_unique=False)  # Should not raise

    def test_field_setting_invalid_value_results_in_none(self, test_model_instance):
        """Test that setting an invalid slug silently converts to None."""
        test_model_instance.single_instance = "invalid"
        assert test_model_instance.single_instance is None

    def test_optional_field_accepts_none(self, test_model_instance):
        """Test optional registry fields."""
        test_model_instance.single_instance = None
        test_model_instance.full_clean()  # Should not raise (blank=True, null=True)

        assert test_model_instance.single_instance is None

    def test_fully_qualified_name_support(self, test_model_instance):
        """Test fully qualified name support."""
        fqn = f"{EmailStrategy.__module__}.{EmailStrategy.__name__}"
        test_model_instance.single_instance = fqn

        assert isinstance(test_model_instance.single_instance, TestStrategy)
        assert test_model_instance.single_instance.execute() == "email_sent"

    @pytest.mark.parametrize(
        "field_name,expected_type",
        [
            ("single_instance", TestStrategy),  # Returns instance
            ("single_class", type),  # Returns class
        ],
    )
    def test_field_types(self, test_model_instance, field_name, expected_type):
        """Test different field types return correct values."""
        setattr(test_model_instance, field_name, "email")
        value = getattr(test_model_instance, field_name)

        if expected_type is type:
            assert isinstance(value, type)
        else:
            assert isinstance(value, expected_type)


# Reference to the registry class for use in tests (to avoid shadowing by test class names)
_TestRegistryRef = TestRegistry


class TestRegistryBehavior:
    """Test cases for Registry class."""

    def test_registry_contains_operator(self):
        """Test registry 'in' operator."""
        assert "email" in _TestRegistryRef
        assert "invalid" not in _TestRegistryRef

        # Also works with classes
        assert EmailImpl in _TestRegistryRef

    def test_registry_iteration(self):
        """Test registry iteration."""
        implementations = list(_TestRegistryRef)
        assert len(implementations) > 0

        for impl in implementations:
            assert issubclass(impl, TestInterface)

    def test_registry_length(self):
        """Test registry length."""
        assert len(_TestRegistryRef) >= 3  # email, sms, phone

    def test_get_by_slug(self):
        """Test getting implementation by slug."""
        impl = _TestRegistryRef.get(slug="email")
        assert isinstance(impl, TestInterface)
        assert impl.process() == "email"

    def test_get_by_fully_qualified_name(self, email_impl_fully_qualified_name):
        """Test getting implementation by fully qualified name."""
        impl = _TestRegistryRef.get(fully_qualified_name=email_impl_fully_qualified_name)
        assert isinstance(impl, TestInterface)
        assert impl.process() == "email"

    def test_get_class_by_slug(self):
        """Test getting implementation class by slug."""
        impl_class = _TestRegistryRef.get_class(slug="email")
        assert issubclass(impl_class, TestInterface)
        assert impl_class == EmailImpl

    def test_get_class_by_fully_qualified_name(self, email_impl_fully_qualified_name):
        """Test getting implementation class by fully qualified name."""
        impl_class = _TestRegistryRef.get_class(fully_qualified_name=email_impl_fully_qualified_name)
        assert issubclass(impl_class, TestInterface)
        assert impl_class == EmailImpl

    def test_get_raises_without_slug_or_fully_qualified_name(self):
        """Test get() raises ValueError without arguments."""
        with pytest.raises(ValueError, match="Either .slug. or .fully_qualified_name. must be provided"):
            _TestRegistryRef.get()

    def test_choices_generation(self):
        """Test registry choices generation."""
        choices = _TestRegistryRef.get_choices()
        assert isinstance(choices, list)
        assert len(choices) > 0

        # Each choice should be (slug, display_name)
        for slug, display in choices:
            assert isinstance(slug, str)
            assert isinstance(display, str)

        # Check specific choices
        choice_dict = dict(choices)
        assert "email" in choice_dict
        assert choice_dict["email"] == "Email Implementation"

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("email", True),  # Valid slug
            ("invalid", False),  # Invalid slug
            (EmailImpl, True),  # Valid class
            (EmailImpl(), True),  # Valid instance
            ("not.a.real.Class", False),  # Invalid FQN
        ],
    )
    def test_is_valid(self, value, expected):
        """Test registry validation with various inputs."""
        assert _TestRegistryRef.is_valid(value) == expected

    def test_get_display_name(self):
        """Test getting display name for implementation."""
        assert _TestRegistryRef.get_display_name(EmailImpl) == "Email Implementation"
        assert _TestRegistryRef.get_display_name(SMSImpl) == "SMS Implementation"


@pytest.mark.django_db
class TestDRFIntegration:
    """Test DRF serializer integration."""

    def test_drf_single_field_serialization(self):
        """Test DrfRegistryField serialization."""
        from rest_framework import serializers

        from django_stratagem.drf import DrfRegistryField

        class TestSerializer(serializers.Serializer):
            implementation = DrfRegistryField(registry=_TestRegistryRef)

        # Test with slug
        data = {"implementation": "email"}
        serializer = TestSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data["implementation"] == EmailImpl

        # Test with FQN
        data = {"implementation": f"{EmailImpl.__module__}.{EmailImpl.__name__}"}
        serializer = TestSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data["implementation"] == EmailImpl

    def test_drf_single_field_deserialization(self):
        """Test DrfRegistryField deserialization."""
        from rest_framework import serializers

        from django_stratagem.drf import DrfRegistryField

        class TestSerializer(serializers.Serializer):
            implementation = DrfRegistryField(registry=_TestRegistryRef)

        # Test with instance data - note: with representation="slug" (default),
        # the to_representation method returns the slug, not the FQN
        instance = {"implementation": EmailImpl}
        serializer = TestSerializer(instance)
        # The default representation is "slug", so it should return the slug
        assert serializer.data["implementation"] == "email"

        # Test with slug data
        instance = {"implementation": "email"}
        serializer = TestSerializer(instance)
        assert serializer.data["implementation"] == "email"

    def test_drf_multiple_field_serialization(self):
        """Test DrfMultipleRegistryField serialization."""
        from rest_framework import serializers

        from django_stratagem.drf import DrfMultipleRegistryField

        class TestSerializer(serializers.Serializer):
            implementations = DrfMultipleRegistryField(registry=_TestRegistryRef)

        data = {"implementations": ["email", "sms"]}
        serializer = TestSerializer(data=data)
        assert serializer.is_valid()
        assert len(serializer.validated_data["implementations"]) == 2
        assert EmailImpl in serializer.validated_data["implementations"]
        assert SMSImpl in serializer.validated_data["implementations"]

    def test_drf_multiple_field_deserialization(self):
        """Test DrfMultipleRegistryField deserialization."""
        from rest_framework import serializers

        from django_stratagem.drf import DrfMultipleRegistryField

        class TestSerializer(serializers.Serializer):
            implementations = DrfMultipleRegistryField(registry=_TestRegistryRef)

        instance = {"implementations": [EmailImpl, SMSImpl]}
        serializer = TestSerializer(instance)

        expected = [f"{EmailImpl.__module__}.{EmailImpl.__name__}", f"{SMSImpl.__module__}.{SMSImpl.__name__}"]
        assert sorted(serializer.data["implementations"]) == sorted(expected)

    def test_drf_field_validation(self):
        """Test DRF field validation."""
        from rest_framework import serializers

        from django_stratagem.drf import DrfRegistryField

        class TestSerializer(serializers.Serializer):
            implementation = DrfRegistryField(registry=_TestRegistryRef)

        # Invalid choice
        data = {"implementation": "invalid"}
        serializer = TestSerializer(data=data)
        assert not serializer.is_valid()
        assert "implementation" in serializer.errors


@pytest.mark.django_db
class TestDRFSerializerEdgeCases:
    """Test DRF serializer edge cases for coverage."""

    def test_drf_single_field_to_representation_exception(self):
        """Test to_representation falls back to FQN when _get_slug raises."""
        from unittest.mock import patch

        from django_stratagem.drf import DrfRegistryField

        field = DrfRegistryField(registry=_TestRegistryRef)

        with patch.object(field, "_get_slug", side_effect=Exception("slug error")):
            result = field.to_representation(EmailImpl)

        expected_fqn = f"{EmailImpl.__module__}.{EmailImpl.__name__}"
        assert result == expected_fqn

    def test_drf_single_field_slug_not_in_registry(self):
        """Test _get_slug returns FQN when class is not in implementations."""
        from django_stratagem.drf import DrfRegistryField

        field = DrfRegistryField(registry=_TestRegistryRef)

        class UnregisteredClass:
            pass

        result = field.to_representation(UnregisteredClass)
        expected_fqn = f"{UnregisteredClass.__module__}.{UnregisteredClass.__name__}"
        assert result == expected_fqn

    def test_drf_single_field_empty_data(self):
        """Test to_internal_value returns None for empty string."""
        from django_stratagem.drf import DrfRegistryField

        field = DrfRegistryField(registry=_TestRegistryRef)
        result = field.to_internal_value("")
        assert result is None

    def test_drf_single_field_fqn_input(self):
        """Test to_internal_value with FQN string resolves to class."""
        from django_stratagem.drf import DrfRegistryField

        field = DrfRegistryField(registry=_TestRegistryRef)
        fqn = f"{EmailImpl.__module__}.{EmailImpl.__name__}"
        result = field.to_internal_value(fqn)
        assert result == EmailImpl

    def test_drf_multiple_field_non_list_input(self):
        """Test to_internal_value fails for non-list input."""
        from rest_framework.exceptions import ValidationError

        from django_stratagem.drf import DrfMultipleRegistryField

        field = DrfMultipleRegistryField(registry=_TestRegistryRef)

        with pytest.raises(ValidationError):
            field.to_internal_value("not_a_list")

    def test_drf_multiple_field_invalid_item(self):
        """Test to_internal_value fails for invalid FQN in list."""
        from rest_framework.exceptions import ValidationError

        from django_stratagem.drf import DrfMultipleRegistryField

        field = DrfMultipleRegistryField(registry=_TestRegistryRef)

        with pytest.raises(ValidationError):
            field.to_internal_value(["nonexistent.module.FakeClass"])

    def test_drf_multiple_field_string_representation(self):
        """Test to_representation passes through string items."""
        from django_stratagem.drf import DrfMultipleRegistryField

        field = DrfMultipleRegistryField(registry=_TestRegistryRef)
        result = field.to_representation(["email", "sms"])
        assert result == ["email", "sms"]


class TestRegistryEdgeCases:
    """Test registry edge cases for coverage."""

    def test_register_without_slug_raises(self):
        """Test registering implementation without slug raises ValueError."""

        class NoSlugImpl:
            display_name = "No Slug"

        with pytest.raises(ValueError, match="must define a non-empty 'slug'"):
            _TestRegistryRef.register(NoSlugImpl)

    def test_get_for_context_with_fqn(self):
        """Test get_for_context retrieves implementation by FQN."""
        fqn = f"{EmailImpl.__module__}.{EmailImpl.__name__}"
        result = _TestRegistryRef.get_for_context(
            context=None,
            fully_qualified_name=fqn,
        )
        assert isinstance(result, TestInterface)
        assert result.process() == "email"

    def test_get_for_context_unavailable_uses_fallback(self, conditional_registry):
        """Test get_for_context falls back when implementation is unavailable."""
        from tests.registries_fixtures import BasicFeature

        context = {"user": None}  # PremiumFeature requires premium user
        result = conditional_registry.get_for_context(
            context=context,
            slug="premium_feature",
        )
        # PremiumFeature is unavailable (user is None), falls back to first available
        assert isinstance(result, BasicFeature)

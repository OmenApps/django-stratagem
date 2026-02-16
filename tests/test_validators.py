"""Tests for django_stratagem validators module."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from django_stratagem.validators import ClassnameValidator, RegistryValidator

pytestmark = pytest.mark.django_db


class TestClassnameValidator:
    """Tests for ClassnameValidator."""

    def test_valid_builtin_class(self):
        """Test validation passes for valid builtin class name."""
        validator = ClassnameValidator(limit_value=None)
        # Should not raise for valid importable class
        validator("builtins.str")

    def test_valid_stdlib_class(self):
        """Test validation passes for valid stdlib class name."""
        validator = ClassnameValidator(limit_value=None)
        validator("datetime.datetime")

    def test_valid_project_class(self, email_strategy):
        """Test validation passes for valid project class name."""
        validator = ClassnameValidator(limit_value=None)
        fqn = f"{email_strategy.__module__}.{email_strategy.__name__}"
        validator(fqn)

    def test_invalid_class_name_raises_error(self):
        """Test validation fails for invalid class name."""
        validator = ClassnameValidator(limit_value=None)
        with pytest.raises(ValidationError) as exc_info:
            validator("nonexistent.module.FakeClass")
        assert exc_info.value.code == "classname"

    def test_invalid_module_raises_error(self):
        """Test validation fails for nonexistent module."""
        validator = ClassnameValidator(limit_value=None)
        with pytest.raises(ValidationError) as exc_info:
            validator("this.module.does.not.exist.MyClass")
        assert exc_info.value.code == "classname"

    @pytest.mark.parametrize(
        "invalid_value",
        [
            # "" is NOT included - empty string passes through for blank fields
            "not-a-valid-name",
            "single",
            "with spaces.Class",
            "123.numbers.First",
        ],
    )
    def test_malformed_class_names(self, invalid_value):
        """Test validation fails for malformed class names."""
        validator = ClassnameValidator(limit_value=None)
        with pytest.raises(ValidationError):
            validator(invalid_value)

    def test_empty_string_passes_validation(self):
        """Test empty string does not raise - allows blank fields."""
        validator = ClassnameValidator(limit_value=None)
        # Empty string is treated as "no value" and passes through
        # This enables blank=True fields to work correctly
        validator("")  # Should not raise

    def test_error_message_contains_value(self):
        """Test error message includes the invalid value."""
        validator = ClassnameValidator(limit_value=None)
        with pytest.raises(ValidationError) as exc_info:
            validator("invalid.class.Name")
        # Verify params contain the value
        assert "show_value" in exc_info.value.params

    def test_custom_message(self):
        """Test custom message is used."""
        custom_msg = "Custom error message for %(show_value)s"
        validator = ClassnameValidator(limit_value=None, message=custom_msg)
        validator.message = custom_msg
        with pytest.raises(ValidationError) as exc_info:
            validator("invalid.module.Class")
        assert "Custom error message" in str(exc_info.value.message)


class TestRegistryValidator:
    """Tests for RegistryValidator."""

    def test_valid_slug(self, test_strategy_registry):
        """Test validation passes for valid slug."""
        validator = RegistryValidator(registry=test_strategy_registry)
        # Should not raise for valid registered slug
        validator("email")

    def test_valid_fqn(self, test_strategy_registry, email_strategy):
        """Test validation passes for valid fully qualified name."""
        validator = RegistryValidator(registry=test_strategy_registry)
        fqn = f"{email_strategy.__module__}.{email_strategy.__name__}"
        validator(fqn)

    def test_invalid_slug_raises_error(self, test_strategy_registry):
        """Test validation fails for invalid slug."""
        validator = RegistryValidator(registry=test_strategy_registry)
        with pytest.raises(ValidationError) as exc_info:
            validator("invalid_slug")
        assert exc_info.value.code == "registry"

    def test_invalid_fqn_raises_error(self, test_strategy_registry):
        """Test validation fails for invalid fully qualified name."""
        validator = RegistryValidator(registry=test_strategy_registry)
        with pytest.raises(ValidationError) as exc_info:
            validator("nonexistent.module.UnregisteredClass")
        assert exc_info.value.code == "registry"

    def test_valid_class_not_in_registry_raises_error(self, test_strategy_registry):
        """Test validation fails for valid class not registered."""
        validator = RegistryValidator(registry=test_strategy_registry)
        # datetime.datetime is valid class but not registered
        with pytest.raises(ValidationError):
            validator("datetime.datetime")

    def test_list_all_valid(self, test_strategy_registry):
        """Test validation passes for list of valid values."""
        validator = RegistryValidator(registry=test_strategy_registry)
        # Should not raise
        validator(["email", "sms"])

    def test_list_one_invalid(self, test_strategy_registry):
        """Test validation fails with single error for list with one invalid."""
        validator = RegistryValidator(registry=test_strategy_registry)
        with pytest.raises(ValidationError) as exc_info:
            validator(["email", "invalid_slug"])
        # Should use singular message for one error
        assert exc_info.value.code == "registry"
        assert "invalid_slug" in str(exc_info.value.params.get("show_value", ""))

    def test_list_multiple_invalid(self, test_strategy_registry):
        """Test validation fails with plural message for multiple invalid."""
        validator = RegistryValidator(registry=test_strategy_registry)
        with pytest.raises(ValidationError) as exc_info:
            validator(["email", "invalid1", "invalid2"])
        # Should use plural message for multiple errors
        assert exc_info.value.code == "registry"
        show_value = exc_info.value.params.get("show_value", "")
        assert "invalid1" in show_value
        assert "invalid2" in show_value

    def test_tuple_input(self, test_strategy_registry):
        """Test validation works with tuple input."""
        validator = RegistryValidator(registry=test_strategy_registry)
        # Should not raise
        validator(("email", "sms", "push"))

    def test_empty_list(self, test_strategy_registry):
        """Test validation passes for empty list."""
        validator = RegistryValidator(registry=test_strategy_registry)
        # Empty list should not raise (no invalid items)
        validator([])

    @pytest.mark.parametrize(
        "valid_slug",
        [
            "email",
            "sms",
            "push",
        ],
    )
    def test_all_registered_slugs_valid(self, test_strategy_registry, valid_slug):
        """Test all registered slugs pass validation."""
        validator = RegistryValidator(registry=test_strategy_registry)
        # Should not raise
        validator(valid_slug)

    def test_custom_message(self, test_strategy_registry):
        """Test custom message is used."""
        custom_msg = "Not a valid strategy: %(show_value)s"
        validator = RegistryValidator(registry=test_strategy_registry, message=custom_msg)
        with pytest.raises(ValidationError) as exc_info:
            validator("invalid")
        assert "Not a valid strategy" in str(exc_info.value.message)

    def test_deconstructible(self, test_strategy_registry):
        """Test validator is deconstructible for migrations."""
        validator = RegistryValidator(registry=test_strategy_registry)
        # Deconstructible objects have deconstruct method
        path, args, kwargs = validator.deconstruct()
        assert "RegistryValidator" in path
        assert "registry" in kwargs


class TestValidatorEdgeCases:
    """Tests for edge cases in validators."""

    def test_classname_validator_with_none(self):
        """Test ClassnameValidator handles None.

        None is treated as "no value" and passes through without error.
        This enables nullable fields to work correctly.
        """
        validator = ClassnameValidator(limit_value=None)
        # None does not raise - it's treated as empty/no value
        validator(None)  # Should not raise

    def test_registry_validator_with_none(self, test_strategy_registry):
        """Test RegistryValidator handles None."""
        validator = RegistryValidator(registry=test_strategy_registry)
        with pytest.raises(ValidationError):
            validator(None)

    def test_registry_validator_with_instance(self, test_strategy_registry, email_strategy):
        """Test RegistryValidator with instance instead of class/slug."""
        validator = RegistryValidator(registry=test_strategy_registry)
        instance = email_strategy()
        # Instance should be valid (registry.is_valid handles instances)
        validator(instance)

    def test_registry_validator_with_class(self, test_strategy_registry, email_strategy):
        """Test RegistryValidator with class object."""
        validator = RegistryValidator(registry=test_strategy_registry)
        # Class object should be valid
        validator(email_strategy)

    def test_list_with_mixed_types(self, test_strategy_registry, email_strategy):
        """Test validation with mixed types in list."""
        validator = RegistryValidator(registry=test_strategy_registry)
        # Mix of slugs and classes
        validator(["email", email_strategy])

    @pytest.mark.parametrize(
        "unicode_value",
        [
            "unicodemodule",
            "module.with.special_chars_123",
        ],
    )
    def test_unicode_in_values(self, test_strategy_registry, unicode_value):
        """Test validators handle various string formats."""
        validator = RegistryValidator(registry=test_strategy_registry)
        # These are invalid but should not crash
        with pytest.raises(ValidationError):
            validator(unicode_value)

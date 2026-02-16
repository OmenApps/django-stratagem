"""Tests for django_stratagem exceptions module."""

from __future__ import annotations

import pytest

from django_stratagem.exceptions import (
    ImplementationNotFound,
    RegistryAttributeError,
    RegistryClassError,
    RegistryImportError,
    RegistryNameError,
)


class TestImplementationNotFound:
    """Tests for ImplementationNotFound exception."""

    def test_inherits_from_key_error(self):
        """Test exception inherits from KeyError."""
        exc = ImplementationNotFound("slug")
        assert isinstance(exc, KeyError)

    def test_can_be_raised(self):
        """Test exception can be raised and caught."""
        with pytest.raises(ImplementationNotFound):
            raise ImplementationNotFound("missing_implementation")

    def test_message_preserved(self):
        """Test exception message is preserved."""
        exc = ImplementationNotFound("test_slug")
        assert "test_slug" in str(exc)

    def test_can_catch_as_key_error(self):
        """Test can be caught as KeyError."""
        with pytest.raises(KeyError):
            raise ImplementationNotFound("test")


class TestRegistryNameError:
    """Tests for RegistryNameError exception."""

    def test_inherits_from_value_error(self):
        """Test exception inherits from ValueError."""
        exc = RegistryNameError("invalid_name")
        assert isinstance(exc, ValueError)

    def test_stores_name(self):
        """Test exception stores the name attribute."""
        exc = RegistryNameError("test_name")
        assert exc.name == "test_name"

    def test_default_message(self):
        """Test exception uses default message."""
        exc = RegistryNameError("invalid.name")
        assert "valid python dotted name" in exc.message

    def test_custom_message(self):
        """Test exception accepts custom message."""
        custom_msg = "Custom error: %s is invalid"
        exc = RegistryNameError("test", message=custom_msg)
        assert exc.message == custom_msg

    def test_repr_formats_message(self):
        """Test __repr__ formats message with name."""
        exc = RegistryNameError("bad_name")
        repr_str = repr(exc)
        assert "bad_name" in repr_str

    def test_can_be_raised(self):
        """Test exception can be raised and caught."""
        with pytest.raises(RegistryNameError):
            raise RegistryNameError("invalid")

    def test_can_catch_as_value_error(self):
        """Test can be caught as ValueError."""
        with pytest.raises(ValueError):
            raise RegistryNameError("test")

    @pytest.mark.parametrize(
        "name",
        [
            "simple",
            "with.dots",
            "with_underscores",
            "CamelCase",
            "mixed.Case_name",
            123,  # Non-string converted to string
        ],
    )
    def test_various_name_types(self, name):
        """Test exception handles various name types."""
        exc = RegistryNameError(name)
        assert exc.name == str(name)


class TestRegistryClassError:
    """Tests for RegistryClassError exception."""

    def test_inherits_from_value_error(self):
        """Test exception inherits from ValueError."""
        exc = RegistryClassError("invalid_class")
        assert isinstance(exc, ValueError)

    def test_stores_name(self):
        """Test exception stores the name attribute."""
        exc = RegistryClassError("TestClass")
        assert exc.name == "TestClass"

    def test_default_message(self):
        """Test exception uses default message."""
        exc = RegistryClassError("BadClass")
        assert "invalid python name" in exc.message

    def test_custom_message(self):
        """Test exception accepts custom message."""
        custom_msg = "Could not find class: %s"
        exc = RegistryClassError("Missing", message=custom_msg)
        assert exc.message == custom_msg

    def test_repr_formats_message(self):
        """Test __repr__ formats message with name."""
        exc = RegistryClassError("InvalidClass")
        repr_str = repr(exc)
        assert "InvalidClass" in repr_str

    def test_can_be_raised(self):
        """Test exception can be raised and caught."""
        with pytest.raises(RegistryClassError):
            raise RegistryClassError("invalid")


class TestRegistryImportError:
    """Tests for RegistryImportError exception."""

    def test_inherits_from_import_error(self):
        """Test exception inherits from ImportError."""
        exc = RegistryImportError("Could not import module")
        assert isinstance(exc, ImportError)

    def test_can_be_raised(self):
        """Test exception can be raised and caught."""
        with pytest.raises(RegistryImportError):
            raise RegistryImportError("Import failed")

    def test_can_catch_as_import_error(self):
        """Test can be caught as ImportError."""
        with pytest.raises(ImportError):
            raise RegistryImportError("test")

    def test_message_preserved(self):
        """Test exception message is preserved."""
        msg = "Could not import my.module.Class"
        exc = RegistryImportError(msg)
        assert msg in str(exc)


class TestRegistryAttributeError:
    """Tests for RegistryAttributeError exception."""

    def test_inherits_from_attribute_error(self):
        """Test exception inherits from AttributeError."""
        exc = RegistryAttributeError(
            name="my.module.Class",
            module_path="my.module",
            class_str="Class",
        )
        assert isinstance(exc, AttributeError)

    def test_stores_name(self):
        """Test exception stores the name attribute."""
        exc = RegistryAttributeError(
            name="full.path.Class",
            module_path="full.path",
            class_str="Class",
        )
        assert exc.name == "full.path.Class"

    def test_stores_module_path(self):
        """Test exception stores the module_path attribute."""
        exc = RegistryAttributeError(
            name="my.module.Class",
            module_path="my.module",
            class_str="Class",
        )
        assert exc.module_path == "my.module"

    def test_stores_class_str(self):
        """Test exception stores the class_str attribute."""
        exc = RegistryAttributeError(
            name="my.module.MyClass",
            module_path="my.module",
            class_str="MyClass",
        )
        assert exc.class_str == "MyClass"

    def test_default_message(self):
        """Test exception uses default message."""
        exc = RegistryAttributeError(
            name="test.module.TestClass",
            module_path="test.module",
            class_str="TestClass",
        )
        assert "Unable to import" in exc.message
        assert "does not have" in exc.message
        assert "attribute" in exc.message

    def test_custom_message(self):
        """Test exception accepts custom message."""
        custom_msg = "Custom: %(name)s from %(module)s missing %(class_str)s"
        exc = RegistryAttributeError(
            name="test",
            module_path="module",
            class_str="Class",
            message=custom_msg,
        )
        assert exc.message == custom_msg

    def test_repr_formats_message(self):
        """Test __repr__ formats message with all attributes."""
        exc = RegistryAttributeError(
            name="app.models.MyModel",
            module_path="app.models",
            class_str="MyModel",
        )
        repr_str = repr(exc)
        assert "app.models.MyModel" in repr_str
        assert "app.models" in repr_str
        assert "MyModel" in repr_str

    def test_can_be_raised(self):
        """Test exception can be raised and caught."""
        with pytest.raises(RegistryAttributeError):
            raise RegistryAttributeError(
                name="test",
                module_path="module",
                class_str="Class",
            )

    def test_can_catch_as_attribute_error(self):
        """Test can be caught as AttributeError."""
        with pytest.raises(AttributeError):
            raise RegistryAttributeError(
                name="test",
                module_path="module",
                class_str="Class",
            )


class TestExceptionHierarchy:
    """Tests for exception inheritance hierarchy."""

    @pytest.mark.parametrize(
        "exception_class,base_class",
        [
            (ImplementationNotFound, KeyError),
            (RegistryNameError, ValueError),
            (RegistryClassError, ValueError),
            (RegistryImportError, ImportError),
            (RegistryAttributeError, AttributeError),
        ],
    )
    def test_exception_inheritance(self, exception_class, base_class):
        """Test each exception inherits from expected base class."""
        assert issubclass(exception_class, base_class)

    @pytest.mark.parametrize(
        "exception_class",
        [
            ImplementationNotFound,
            RegistryNameError,
            RegistryClassError,
            RegistryImportError,
            RegistryAttributeError,
        ],
    )
    def test_all_exceptions_inherit_from_exception(self, exception_class):
        """Test all exceptions inherit from Exception."""
        assert issubclass(exception_class, Exception)


class TestExceptionStrOutput:
    """Tests that str() on exceptions produces meaningful output."""

    def test_registry_name_error_str_contains_name(self):
        """Test str(RegistryNameError) contains the invalid name."""
        exc = RegistryNameError("bad_name")
        assert "bad_name" in str(exc)

    def test_registry_name_error_str_equals_repr(self):
        """Test str() and repr() produce the same output."""
        exc = RegistryNameError("bad_name")
        assert str(exc) == repr(exc)

    def test_registry_class_error_str_contains_name(self):
        """Test str(RegistryClassError) contains the invalid name."""
        exc = RegistryClassError("BadClass")
        assert "BadClass" in str(exc)

    def test_registry_class_error_str_equals_repr(self):
        """Test str() and repr() produce the same output."""
        exc = RegistryClassError("BadClass")
        assert str(exc) == repr(exc)

    def test_registry_attribute_error_str_contains_details(self):
        """Test str(RegistryAttributeError) contains all relevant details."""
        exc = RegistryAttributeError(
            name="my.module.Class",
            module_path="my.module",
            class_str="Class",
        )
        result = str(exc)
        assert "my.module.Class" in result
        assert "my.module" in result
        assert "Class" in result

    def test_registry_attribute_error_str_equals_repr(self):
        """Test str() and repr() produce the same output."""
        exc = RegistryAttributeError(
            name="my.module.Class",
            module_path="my.module",
            class_str="Class",
        )
        assert str(exc) == repr(exc)

    def test_registry_name_error_str_not_empty(self):
        """Test str(RegistryNameError) is never empty."""
        exc = RegistryNameError("x")
        assert str(exc) != ""

    def test_registry_class_error_str_not_empty(self):
        """Test str(RegistryClassError) is never empty."""
        exc = RegistryClassError("x")
        assert str(exc) != ""

    def test_registry_attribute_error_str_not_empty(self):
        """Test str(RegistryAttributeError) is never empty."""
        exc = RegistryAttributeError(name="x", module_path="y", class_str="z")
        assert str(exc) != ""

    def test_exception_str_in_fstring(self):
        """Test exceptions produce meaningful output when used in f-strings."""
        exc = RegistryNameError("bad_name")
        msg = f"Error occurred: {exc}"
        assert "bad_name" in msg
        assert msg != "Error occurred: "


class TestExceptionEdgeCases:
    """Tests for edge cases in exception handling."""

    def test_registry_name_error_with_none(self):
        """Test RegistryNameError handles None-like value."""
        exc = RegistryNameError("")
        assert exc.name == ""

    def test_registry_class_error_with_special_chars(self):
        """Test RegistryClassError handles special characters."""
        exc = RegistryClassError("Class<with>special&chars")
        assert exc.name == "Class<with>special&chars"

    def test_registry_attribute_error_empty_strings(self):
        """Test RegistryAttributeError handles empty strings."""
        exc = RegistryAttributeError(
            name="",
            module_path="",
            class_str="",
        )
        assert exc.name == ""
        assert exc.module_path == ""
        assert exc.class_str == ""

    def test_exceptions_are_distinct_types(self):
        """Test all exception types are distinct."""
        exception_types = [
            ImplementationNotFound,
            RegistryNameError,
            RegistryClassError,
            RegistryImportError,
            RegistryAttributeError,
        ]

        for i, exc_type in enumerate(exception_types):
            for other_type in exception_types[i + 1 :]:
                assert exc_type is not other_type

    def test_exception_can_be_used_in_try_except(self):
        """Test exceptions work in typical try/except pattern."""

        def function_that_raises():
            raise RegistryNameError("test_name")

        caught = False
        try:
            function_that_raises()
        except RegistryNameError as e:
            caught = True
            assert e.name == "test_name"

        assert caught is True

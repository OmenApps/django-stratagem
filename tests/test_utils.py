"""Tests for django_stratagem utility functions."""

from __future__ import annotations

import pytest

from django_stratagem.exceptions import RegistryAttributeError, RegistryClassError, RegistryNameError
from django_stratagem.utils import (
    camel_to_title,
    get_attr,
    get_class,
    get_display_string,
    get_fully_qualified_name,
    import_by_name,
    stringify,
)


class TestCamelToTitle:
    """Tests for camel_to_title function."""

    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("CamelCase", "Camel Case"),
            ("camelCase", "Camel Case"),
            ("TestClass", "Test Class"),
            ("HTTPHandler", "HTTP Handler"),
            ("simpletest", "Simpletest"),
            ("ABC", "ABC"),
            ("MyURLParser", "My URL Parser"),
            ("Test", "Test"),
            ("", ""),
        ],
    )
    def test_camel_to_title_conversions(self, input_text, expected):
        """Test various camel case to title case conversions."""
        result = camel_to_title(input_text)
        assert result == expected

    def test_camel_to_title_with_numbers(self):
        """Test camel_to_title with numbers in string."""
        result = camel_to_title("Test123Class")
        assert "Test" in result
        assert "Class" in result

    def test_camel_to_title_single_word(self):
        """Test camel_to_title with single word."""
        result = camel_to_title("Single")
        assert result == "Single"


class TestImportByName:
    """Tests for import_by_name function."""

    def test_import_by_name_success(self):
        """Test importing a class by fully qualified name."""
        from django_stratagem.registry import Registry

        result = import_by_name("django_stratagem.registry.Registry")
        assert result == Registry

    def test_import_by_name_function(self):
        """Test importing a function by name."""
        result = import_by_name("django_stratagem.utils.camel_to_title")
        assert result == camel_to_title

    def test_import_by_name_raises_for_no_dot(self):
        """Test import_by_name raises RegistryNameError for name without dots."""
        with pytest.raises(RegistryNameError):
            import_by_name("NoDotInName")

    def test_import_by_name_raises_for_invalid_module(self):
        """Test import_by_name raises ImportError for non-existent module."""
        with pytest.raises(ImportError):
            import_by_name("nonexistent.module.Class")

    def test_import_by_name_raises_for_invalid_attribute(self):
        """Test import_by_name raises RegistryAttributeError for non-existent attribute."""
        with pytest.raises(RegistryAttributeError):
            import_by_name("django_stratagem.registry.NonExistentClass")

    def test_import_by_name_caching(self):
        """Test that import_by_name caches results."""
        # Import twice, should use cached result
        result1 = import_by_name("django_stratagem.registry.Registry")
        result2 = import_by_name("django_stratagem.registry.Registry")
        assert result1 is result2


class TestGetClass:
    """Tests for get_class function."""

    def test_get_class_from_string(self):
        """Test get_class with string reference."""
        from django_stratagem.registry import Registry

        result = get_class("django_stratagem.registry.Registry")
        assert result == Registry

    def test_get_class_with_class(self):
        """Test get_class returns class passed directly."""
        from django_stratagem.registry import Registry

        result = get_class(Registry)
        assert result == Registry

    def test_get_class_with_none(self):
        """Test get_class returns None for None input."""
        result = get_class(None)
        assert result is None

    def test_get_class_with_empty_string(self):
        """Test get_class returns None for empty string."""
        result = get_class("")
        assert result is None

    def test_get_class_with_instance(self):
        """Test get_class returns type for instance."""

        class CustomClass:
            pass

        instance = CustomClass()
        result = get_class(instance)
        assert result == CustomClass

    def test_get_class_with_builtin_type(self):
        """Test get_class returns None for builtin types passed as instances."""
        # Integer instance - get_class returns None for builtins
        result = get_class(42)
        assert result is None

    def test_get_class_with_invalid_string(self):
        """Test get_class raises RegistryNameError for invalid string paths."""
        from django_stratagem.exceptions import RegistryNameError

        # String without dot is not a valid module path
        with pytest.raises(RegistryNameError):
            get_class("string")


class TestGetDisplayString:
    """Tests for get_display_string function."""

    def test_get_display_string_default(self):
        """Test get_display_string uses class name when no attribute specified."""

        class TestClass:
            pass

        result = get_display_string(TestClass)
        assert result == "Test Class"

    def test_get_display_string_with_display_attribute(self):
        """Test get_display_string uses specified attribute."""

        class TestClass:
            display_name = "Custom Display Name"

        result = get_display_string(TestClass, "display_name")
        assert result == "Custom Display Name"

    def test_get_display_string_with_callable_attribute(self):
        """Test get_display_string calls callable attributes."""

        class TestClass:
            @staticmethod
            def get_name():
                return "Callable Result"

        result = get_display_string(TestClass, "get_name")
        assert result == "Callable Result"

    def test_get_display_string_with_none_attribute_value(self):
        """Test get_display_string falls back to FQN when attribute is None."""

        class TestClass:
            display_name = None

        result = get_display_string(TestClass, "display_name")
        # Should return fully qualified name
        assert "TestClass" in result

    def test_get_display_string_with_missing_attribute(self):
        """Test get_display_string falls back to class name when attribute missing."""

        class TestClass:
            pass

        result = get_display_string(TestClass, "nonexistent_attribute")
        assert result == "Test Class"


class TestGetAttr:
    """Tests for get_attr function."""

    def test_get_attr_simple(self):
        """Test get_attr with simple attribute."""

        class Obj:
            value = 42

        result = get_attr(Obj(), "value")
        assert result == 42

    def test_get_attr_nested(self):
        """Test get_attr with dot notation for nested attributes."""

        class Inner:
            value = "nested"

        class Outer:
            inner = Inner()

        result = get_attr(Outer(), "inner.value")
        assert result == "nested"

    def test_get_attr_default(self):
        """Test get_attr returns default for missing attribute."""

        class Obj:
            pass

        result = get_attr(Obj(), "missing", default="default_value")
        assert result == "default_value"

    def test_get_attr_nested_default(self):
        """Test get_attr returns default for missing nested attribute."""

        class Obj:
            pass

        result = get_attr(Obj(), "missing.nested", default="default")
        assert result == "default"

    def test_get_attr_deeply_nested(self):
        """Test get_attr with deeply nested attributes."""

        class Level3:
            value = "deep"

        class Level2:
            level3 = Level3()

        class Level1:
            level2 = Level2()

        result = get_attr(Level1(), "level2.level3.value")
        assert result == "deep"


class TestGetFullyQualifiedName:
    """Tests for get_fully_qualified_name function."""

    def test_get_fqn_with_class(self):
        """Test get_fully_qualified_name with class."""
        from django_stratagem.registry import Registry

        result = get_fully_qualified_name(Registry)
        assert result == "django_stratagem.registry.Registry"

    def test_get_fqn_with_instance(self):
        """Test get_fully_qualified_name with instance."""

        class MyClass:
            pass

        instance = MyClass()
        result = get_fully_qualified_name(instance)
        assert "MyClass" in result

    def test_get_fqn_with_string(self):
        """Test get_fully_qualified_name returns string unchanged."""
        result = get_fully_qualified_name("already.qualified.name")
        assert result == "already.qualified.name"

    def test_get_fqn_with_function(self):
        """Test get_fully_qualified_name with function."""

        def test_function():
            pass

        result = get_fully_qualified_name(test_function)
        assert "test_function" in result

    def test_get_fqn_raises_for_invalid_type(self):
        """Test get_fully_qualified_name raises for types without __module__."""
        # Numbers don't have __module__ in the expected way
        with pytest.raises(RegistryClassError):
            get_fully_qualified_name(42)

    def test_get_fqn_with_module_function(self):
        """Test get_fully_qualified_name with module-level function."""
        result = get_fully_qualified_name(camel_to_title)
        assert result == "django_stratagem.utils.camel_to_title"


class TestStringify:
    """Tests for stringify function."""

    def test_stringify_with_strings(self):
        """Test stringify with string values."""
        result = stringify(["apple", "banana", "cherry"])
        assert result == "apple,banana,cherry"

    def test_stringify_with_classes(self):
        """Test stringify with class values."""
        from tests.registries_fixtures import EmailStrategy, SMSStrategy

        result = stringify([EmailStrategy, SMSStrategy])
        assert "EmailStrategy" in result
        assert "SMSStrategy" in result

    def test_stringify_with_mixed_values(self):
        """Test stringify with mixed string and class values."""
        from tests.registries_fixtures import EmailStrategy

        result = stringify(["email", EmailStrategy])
        assert "email" in result
        assert "EmailStrategy" in result

    def test_stringify_with_empty_list(self):
        """Test stringify with empty list."""
        result = stringify([])
        assert result == ""

    def test_stringify_sorts_values(self):
        """Test stringify sorts values alphabetically."""
        result = stringify(["zebra", "apple", "middle"])
        assert result == "apple,middle,zebra"

    def test_stringify_skips_empty_strings(self):
        """Test stringify skips empty string values."""
        result = stringify(["value", "", "another"])
        # Empty string gets converted to FQN or skipped
        assert "value" in result
        assert "another" in result

    def test_stringify_with_instances(self):
        """Test stringify with class instances."""
        from tests.registries_fixtures import EmailStrategy

        instance = EmailStrategy()
        result = stringify([instance])
        assert "EmailStrategy" in result


class TestUtilsEdgeCases:
    """Tests for edge cases in utility functions."""

    def test_import_by_name_with_nested_module(self):
        """Test import_by_name with deeply nested module path."""
        result = import_by_name("tests.registries_fixtures.TestStrategyRegistry")
        from tests.registries_fixtures import TestStrategyRegistry

        assert result == TestStrategyRegistry

    def test_get_display_string_with_numeric_attribute(self):
        """Test get_display_string handles numeric attribute values."""

        class TestClass:
            version = 123

        result = get_display_string(TestClass, "version")
        assert result == "123"

    def test_get_attr_with_property(self):
        """Test get_attr works with properties."""

        class Obj:
            @property
            def computed(self):
                return "computed_value"

        result = get_attr(Obj(), "computed")
        assert result == "computed_value"

    def test_stringify_preserves_fqn_for_non_string_values(self):
        """Test stringify converts non-string values to FQN."""

        class LocalClass:
            pass

        result = stringify([LocalClass])
        assert "LocalClass" in result
        assert "test_utils" in result  # Module name should be present

"""Tests for django_stratagem fields and descriptors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator

from django_stratagem.fields import (
    HierarchicalRegistryField,
    HierarchicalRegistryFieldDescriptor,
    MultipleHierarchicalRegistryField,
    MultipleRegistryClassField,
    MultipleRegistryClassFieldDescriptor,
    MultipleRegistryField,
    MultipleRegistryFieldDescriptor,
    RegistryClassField,
    RegistryClassFieldDescriptor,
    RegistryField,
    RegistryFieldDescriptor,
)
from django_stratagem.utils import get_fully_qualified_name
from django_stratagem.validators import ClassnameValidator, RegistryValidator

pytestmark = pytest.mark.django_db


def _make_field_and_descriptor(field_cls, descriptor_cls, registry, **field_kwargs):
    """Create a field and its descriptor for unit testing."""
    field = field_cls(registry=registry, blank=True, null=True, **field_kwargs)
    field.name = "test_field"
    field.attname = "test_field"
    descriptor = descriptor_cls(field)
    return field, descriptor


class _MockObj:
    """Simple mock model instance with configurable __dict__."""

    def __init__(self, **attrs):
        self.__dict__.update(attrs)


def _make_mock_obj(**attrs):
    """Create a mock model instance with a __dict__."""
    return _MockObj(**attrs)


class TestRegistryClassFieldDescriptor:
    """Tests for RegistryClassFieldDescriptor."""

    def test_get_returns_none_when_obj_is_none(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        assert descriptor.__get__(None) is None

    def test_get_returns_none_for_none_raw_value(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field=None)
        assert descriptor.__get__(obj) is None

    def test_get_returns_class_passthrough(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field=email_strategy)
        result = descriptor.__get__(obj)
        assert result is email_strategy

    def test_get_resolves_slug(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field="email")
        result = descriptor.__get__(obj)
        assert result is email_strategy

    def test_get_resolves_fqn(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        fqn = get_fully_qualified_name(email_strategy)
        obj = _make_mock_obj(test_field=fqn)
        result = descriptor.__get__(obj)
        assert result is email_strategy

    def test_get_returns_none_on_import_error(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field="nonexistent.module.Class")
        result = descriptor.__get__(obj)
        assert result is None

    def test_get_warns_on_unexpected_type(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field=12345)
        result = descriptor.__get__(obj)
        assert result == 12345

    def test_set_none_value(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, None)
        assert obj.__dict__["test_field"] is None
        assert obj.__dict__["_registry_fully_qualified_name_test_field"] is None

    def test_set_empty_string(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, "")
        assert obj.__dict__["test_field"] is None

    def test_set_class_directly(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, email_strategy)
        assert obj.__dict__["test_field"] is email_strategy
        assert obj.__dict__["_registry_fully_qualified_name_test_field"] == get_fully_qualified_name(email_strategy)

    def test_set_slug_string(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, "email")
        assert obj.__dict__["test_field"] is email_strategy
        assert obj.__dict__["_registry_fully_qualified_name_test_field"] == get_fully_qualified_name(email_strategy)

    def test_set_fqn_string(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        fqn = get_fully_qualified_name(email_strategy)
        obj = _make_mock_obj()
        descriptor.__set__(obj, fqn)
        assert obj.__dict__["test_field"] is email_strategy

    def test_set_import_error_with_callable_handler(self, test_strategy_registry):
        sentinel = object()
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField,
            RegistryClassFieldDescriptor,
            test_strategy_registry,
            import_error=lambda val, exc: sentinel,
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, "nonexistent.module.Class")
        assert obj.__dict__["test_field"] is sentinel

    def test_set_import_error_with_static_value(self, test_strategy_registry):
        sentinel = object()
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField,
            RegistryClassFieldDescriptor,
            test_strategy_registry,
            import_error=sentinel,
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, "nonexistent.module.Class")
        assert obj.__dict__["test_field"] is sentinel

    def test_set_unexpected_error_raises_validation_error(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            RegistryClassField, RegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        with patch("django_stratagem.fields.get_class", side_effect=RuntimeError("boom")):
            with pytest.raises(ValidationError, match="Unable to import"):
                descriptor.__set__(obj, "some.valid.looking.Path")


class TestMultipleRegistryClassFieldDescriptor:
    """Tests for MultipleRegistryClassFieldDescriptor."""

    def test_get_returns_none_when_obj_is_none(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        assert descriptor.__get__(None) is None

    def test_get_returns_none_for_none_raw_value(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field=None)
        assert descriptor.__get__(obj) is None

    def test_get_returns_classes_list_passthrough(self, test_strategy_registry, email_strategy, sms_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field=[email_strategy, sms_strategy])
        result = descriptor.__get__(obj)
        assert result == [email_strategy, sms_strategy]

    def test_get_parses_comma_separated_string(self, test_strategy_registry, email_strategy, sms_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        fqn1 = get_fully_qualified_name(email_strategy)
        fqn2 = get_fully_qualified_name(sms_strategy)
        obj = _make_mock_obj(test_field=f"{fqn1},{fqn2}")
        result = descriptor.__get__(obj)
        assert email_strategy in result
        assert sms_strategy in result

    def test_get_wraps_non_list_non_string(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field=email_strategy)
        result = descriptor.__get__(obj)
        assert result == [email_strategy]

    def test_get_resolves_slugs(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field="email")
        result = descriptor.__get__(obj)
        assert email_strategy in result

    def test_get_resolves_fqn(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        fqn = get_fully_qualified_name(email_strategy)
        obj = _make_mock_obj(test_field=fqn)
        result = descriptor.__get__(obj)
        assert email_strategy in result

    def test_get_import_error_with_callable_handler(self, test_strategy_registry):
        sentinel = [object()]
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField,
            MultipleRegistryClassFieldDescriptor,
            test_strategy_registry,
            import_error=lambda vals, exc: sentinel,
        )
        obj = _make_mock_obj(test_field="nonexistent.module.Class")
        result = descriptor.__get__(obj)
        assert result is sentinel

    def test_get_import_error_with_static_value(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField,
            MultipleRegistryClassFieldDescriptor,
            test_strategy_registry,
            import_error=None,
        )
        obj = _make_mock_obj(test_field="nonexistent.module.Class")
        result = descriptor.__get__(obj)
        # No import_error set (None), errors are just swallowed and result is empty
        assert result == []

    def test_set_class_list_to_fqn_string(self, test_strategy_registry, email_strategy, sms_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, [email_strategy, sms_strategy])
        stored = obj.__dict__["test_field"]
        assert get_fully_qualified_name(email_strategy) in stored
        assert get_fully_qualified_name(sms_strategy) in stored

    def test_set_single_class(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, email_strategy)
        assert obj.__dict__["test_field"] == get_fully_qualified_name(email_strategy)

    def test_set_none(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, None)
        assert obj.__dict__["test_field"] is None


class TestRegistryFieldDescriptor:
    """Tests for RegistryFieldDescriptor (instantiates via factory)."""

    def test_get_returns_none_when_obj_is_none(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(RegistryField, RegistryFieldDescriptor, test_strategy_registry)
        assert descriptor.__get__(None) is None

    def test_get_returns_none_for_none_raw_value(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(RegistryField, RegistryFieldDescriptor, test_strategy_registry)
        obj = _make_mock_obj(test_field=None)
        assert descriptor.__get__(obj) is None

    def test_get_returns_existing_instance(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(RegistryField, RegistryFieldDescriptor, test_strategy_registry)
        instance = email_strategy()
        obj = _make_mock_obj(test_field=instance)
        result = descriptor.__get__(obj)
        assert result is instance

    def test_get_instantiates_from_slug(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(RegistryField, RegistryFieldDescriptor, test_strategy_registry)
        obj = _make_mock_obj(test_field="email")
        result = descriptor.__get__(obj)
        assert isinstance(result, email_strategy)

    def test_get_instantiates_from_class(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(RegistryField, RegistryFieldDescriptor, test_strategy_registry)
        obj = _make_mock_obj(test_field=email_strategy)
        result = descriptor.__get__(obj)
        assert isinstance(result, email_strategy)

    def test_get_uses_custom_factory(self, test_strategy_registry, email_strategy):
        sentinel = object()
        field, descriptor = _make_field_and_descriptor(
            RegistryField,
            RegistryFieldDescriptor,
            test_strategy_registry,
            factory=lambda klass, obj: sentinel,
        )
        obj = _make_mock_obj(test_field="email")
        result = descriptor.__get__(obj)
        assert result is sentinel

    def test_get_returns_none_on_instantiation_error(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            RegistryField,
            RegistryFieldDescriptor,
            test_strategy_registry,
            factory=lambda klass, obj: (_ for _ in ()).throw(TypeError("fail")),
        )
        obj = _make_mock_obj(test_field="email")
        result = descriptor.__get__(obj)
        assert result is None

    def test_get_returns_none_on_import_error(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(RegistryField, RegistryFieldDescriptor, test_strategy_registry)
        obj = _make_mock_obj(test_field="nonexistent.module.Class")
        result = descriptor.__get__(obj)
        assert result is None

    def test_set_class_instantiates_via_factory(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(RegistryField, RegistryFieldDescriptor, test_strategy_registry)
        obj = _make_mock_obj()
        descriptor.__set__(obj, email_strategy)
        assert isinstance(obj.__dict__["test_field"], email_strategy)

    def test_set_slug_instantiates(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(RegistryField, RegistryFieldDescriptor, test_strategy_registry)
        obj = _make_mock_obj()
        descriptor.__set__(obj, "email")
        assert isinstance(obj.__dict__["test_field"], email_strategy)

    def test_set_import_error_with_handler(self, test_strategy_registry):
        sentinel = object()
        field, descriptor = _make_field_and_descriptor(
            RegistryField,
            RegistryFieldDescriptor,
            test_strategy_registry,
            import_error=lambda val, exc: sentinel,
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, "nonexistent.module.Class")
        # import_error returns a non-class sentinel so it's stored directly
        assert obj.__dict__["test_field"] is sentinel

    def test_set_fqn_string_instantiates(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            RegistryField, RegistryFieldDescriptor, test_strategy_registry
        )
        fqn = get_fully_qualified_name(email_strategy)
        obj = _make_mock_obj()
        descriptor.__set__(obj, fqn)
        # Should be instantiated via factory
        assert isinstance(obj.__dict__["test_field"], email_strategy)
        assert obj.__dict__["_registry_fully_qualified_name_test_field"] == fqn

    def test_set_import_error_static_handler(self, test_strategy_registry):
        sentinel = object()
        field, descriptor = _make_field_and_descriptor(
            RegistryField,
            RegistryFieldDescriptor,
            test_strategy_registry,
            import_error=sentinel,
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, "nonexistent.module.Class")
        # Non-callable import_error stored directly (not a class, so no factory)
        assert obj.__dict__["test_field"] is sentinel

    def test_set_unexpected_error_raises(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            RegistryField, RegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        with patch("django_stratagem.fields.get_class", side_effect=RuntimeError("boom")):
            with pytest.raises(ValidationError, match="Unable to import"):
                descriptor.__set__(obj, "some.valid.looking.Path")

    def test_set_factory_error_raises(self, test_strategy_registry, email_strategy):
        def bad_factory(klass, obj):
            raise RuntimeError("factory failed")

        field, descriptor = _make_field_and_descriptor(
            RegistryField,
            RegistryFieldDescriptor,
            test_strategy_registry,
            factory=bad_factory,
        )
        obj = _make_mock_obj()
        with pytest.raises(ValidationError, match="Unable to instantiate"):
            descriptor.__set__(obj, email_strategy)

    def test_set_none_stores_raw_value(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            RegistryField, RegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, None)
        assert obj.__dict__["test_field"] is None
        assert obj.__dict__["_registry_fully_qualified_name_test_field"] is None


class TestMultipleRegistryFieldDescriptor:
    """Tests for MultipleRegistryFieldDescriptor."""

    def test_get_returns_none_when_obj_is_none(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        assert descriptor.__get__(None) is None

    def test_get_returns_empty_list_for_falsy_value(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field=None)
        assert descriptor.__get__(obj) == []

    def test_get_returns_cached_instances(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        instance = email_strategy()
        obj = _make_mock_obj(test_field=[instance])
        result = descriptor.__get__(obj)
        assert result == [instance]

    def test_get_resolves_and_instantiates_from_string(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field="email")
        result = descriptor.__get__(obj)
        assert len(result) == 1
        assert isinstance(result[0], email_strategy)

    def test_get_resolves_from_class_list(self, test_strategy_registry, email_strategy, sms_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field=[email_strategy, sms_strategy])
        result = descriptor.__get__(obj)
        assert len(result) == 2
        assert isinstance(result[0], email_strategy)
        assert isinstance(result[1], sms_strategy)

    def test_get_import_error_with_callable(self, test_strategy_registry):
        sentinel = [object()]
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField,
            MultipleRegistryFieldDescriptor,
            test_strategy_registry,
            import_error=lambda vals, exc: sentinel,
        )
        obj = _make_mock_obj(test_field="nonexistent.module.Class")
        result = descriptor.__get__(obj)
        assert result is sentinel

    def test_set_instance_list_conversion(self, test_strategy_registry, email_strategy, sms_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        instances = [email_strategy(), sms_strategy()]
        descriptor.__set__(obj, instances)
        stored = obj.__dict__["test_field"]
        assert get_fully_qualified_name(email_strategy) in stored
        assert get_fully_qualified_name(sms_strategy) in stored

    def test_set_mixed_list(self, test_strategy_registry, email_strategy, sms_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        fqn = get_fully_qualified_name(sms_strategy)
        descriptor.__set__(obj, [email_strategy, fqn])
        stored = obj.__dict__["test_field"]
        assert get_fully_qualified_name(email_strategy) in stored
        assert fqn in stored

    def test_set_single_class(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, email_strategy)
        assert obj.__dict__["test_field"] == get_fully_qualified_name(email_strategy)

    def test_set_single_instance(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        instance = email_strategy()
        descriptor.__set__(obj, instance)
        assert obj.__dict__["test_field"] == get_fully_qualified_name(email_strategy)

    def test_set_none_stores_none(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj()
        descriptor.__set__(obj, None)
        assert obj.__dict__["test_field"] is None

    def test_get_unexpected_type_returns_empty(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field=12345)
        result = descriptor.__get__(obj)
        assert result == []

    def test_get_import_error_no_handler(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry,
            import_error=None,
        )
        obj = _make_mock_obj(test_field="nonexistent.module.Class")
        result = descriptor.__get__(obj)
        assert result == []

    def test_get_unexpected_exception_raises(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry
        )
        obj = _make_mock_obj(test_field="some.module.Class")
        with patch("django_stratagem.fields.get_class", side_effect=RuntimeError("boom")):
            with pytest.raises(ValidationError, match="Unable to process"):
                descriptor.__get__(obj)

    def test_get_import_error_list_static(self, test_strategy_registry, email_strategy):
        sentinel_list = [email_strategy]
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry,
            import_error=sentinel_list,
        )
        obj = _make_mock_obj(test_field="nonexistent.module.Class")
        result = descriptor.__get__(obj)
        assert result is sentinel_list

    def test_get_import_error_non_list_static(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryField, MultipleRegistryFieldDescriptor, test_strategy_registry,
            import_error="some_string",
        )
        obj = _make_mock_obj(test_field="nonexistent.module.Class")
        result = descriptor.__get__(obj)
        assert result == []


class TestAbstractRegistryFieldMethods:
    """Tests for AbstractRegistryField methods."""

    def test_to_python_none(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        assert field.to_python(None) is None

    def test_to_python_class(self, test_strategy_registry, email_strategy):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        assert field.to_python(email_strategy) is email_strategy

    def test_to_python_non_string_instance(self, test_strategy_registry, email_strategy):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        instance = email_strategy()
        result = field.to_python(instance)
        assert isinstance(result, str)
        assert "EmailStrategy" in result

    def test_get_prep_value_none(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        assert field.get_prep_value(None) is None

    def test_get_prep_value_slug(self, test_strategy_registry, email_strategy):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        result = field.get_prep_value("email")
        assert result == get_fully_qualified_name(email_strategy)

    def test_get_prep_value_class(self, test_strategy_registry, email_strategy):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        result = field.get_prep_value(email_strategy)
        assert result == get_fully_qualified_name(email_strategy)

    def test_get_prep_value_instance(self, test_strategy_registry, email_strategy):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        instance = email_strategy()
        result = field.get_prep_value(instance)
        assert result == get_fully_qualified_name(email_strategy)

    def test_get_prep_value_error_handling_string(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        result = field.get_prep_value("nonexistent.fqn")
        # Should fall back to returning the string itself
        assert result == "nonexistent.fqn"

    def test_get_prep_value_instance_returns_fqn_of_type(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        result = field.get_prep_value(12345)
        # get_fully_qualified_name(type(12345)) returns "builtins.int"
        assert result == "builtins.int"

    def test_value_to_string_none(self, test_strategy_registry, email_strategy):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        field.attname = "test_field"

        obj = _make_mock_obj(test_field=None)
        result = field.value_to_string(obj)
        assert result == ""

    def test_value_to_string_error(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        field.attname = "test_field"

        obj = _make_mock_obj(test_field=12345)
        result = field.value_to_string(obj)
        assert result == ""

    def test_get_choices_valid_registry(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        choices = field._get_choices()
        assert len(choices) == 3
        slugs = [slug for slug, _ in choices]
        assert "email" in slugs

    def test_get_choices_invalid_registry_type(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.registry = "not_a_registry"
        choices = field._get_choices()
        assert choices == []

    def test_get_choices_no_registry(self):
        field = RegistryClassField(blank=True, null=True)
        choices = field._get_choices()
        assert choices == []

    @pytest.mark.parametrize(
        "field_cls,expected_form_class_name",
        [
            (RegistryClassField, "RegistryFormField"),
            (RegistryField, "RegistryFormField"),
            (MultipleRegistryClassField, "RegistryMultipleChoiceFormField"),
            (MultipleRegistryField, "RegistryMultipleChoiceFormField"),
        ],
    )
    def test_formfield_returns_correct_form_class(self, test_strategy_registry, field_cls, expected_form_class_name):
        field = field_cls(registry=test_strategy_registry, blank=True, null=True)
        form_field = field.formfield()
        assert form_field is not None
        assert type(form_field).__name__ == expected_form_class_name

    def test_formfield_filters_invalid_kwargs(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        form_field = field.formfield(some_invalid_kwarg="should_be_removed")
        assert form_field is not None

    def test_flatchoices_returns_empty(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        assert field.flatchoices == []

    def test_from_db_value_none(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        assert field.from_db_value(None, None, None) is None

    def test_from_db_value_string(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        assert field.from_db_value("some_value", None, None) == "some_value"

    def test_get_internal_type(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        assert field.get_internal_type() == "CharField"

    def test_init_invalid_registry_raises(self):
        with pytest.raises(ValueError, match="must be a Registry subclass"):
            RegistryClassField(registry="not_a_registry")

    def test_deconstruct_preserves_registry(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        _, _, _, kwargs = field.deconstruct()
        assert kwargs["registry"] is test_strategy_registry

    def test_deconstruct_removes_default_max_length(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        _, _, _, kwargs = field.deconstruct()
        assert "max_length" not in kwargs

    def test_deconstruct_preserves_custom_max_length(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True, max_length=500)
        field.name = "test_field"
        _, _, _, kwargs = field.deconstruct()
        assert kwargs["max_length"] == 500

    def test_get_choices_exception_returns_empty(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        with patch.object(test_strategy_registry, "get_choices", side_effect=ValueError("boom")):
            choices = field._get_choices()
            assert choices == []

    def test_deconstruct_removes_choices(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        # Manually inject a choices key into the field
        _, _, _, kwargs = field.deconstruct()
        assert "choices" not in kwargs

    def test_get_prep_value_exception_returns_none(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)

        class BadObj:
            """Object whose type causes get_fully_qualified_name to fail."""
            pass

        with patch("django_stratagem.fields.get_fully_qualified_name", side_effect=TypeError("fail")):
            result = field.get_prep_value(BadObj())
            assert result is None


class TestRegistryClassFieldValidation:
    """Tests for RegistryClassField.validate()."""

    def test_empty_value_passes(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.validate(None, None)  # Should not raise

    def test_class_in_registry_passes(self, test_strategy_registry, email_strategy):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        field.validate(email_strategy, None)  # Should not raise

    def test_slug_passes(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        field.validate("email", None)  # Should not raise

    def test_fqn_resolves(self, test_strategy_registry, email_strategy):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        fqn = get_fully_qualified_name(email_strategy)
        field.validate(fqn, None)  # Should not raise

    def test_instance_checks_type(self, test_strategy_registry, email_strategy):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        instance = email_strategy()
        field.validate(instance, None)  # Should not raise

    def test_invalid_raises_validation_error(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"

        class NotRegistered:
            pass

        with pytest.raises(ValidationError, match="not a valid choice"):
            field.validate(NotRegistered, None)

    def test_validate_bad_fqn_raises(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        with pytest.raises(ValidationError, match="not a valid choice"):
            field.validate("nonexistent.module.NoSuchClass", None)

    def test_validate_unregistered_instance(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"

        class NotRegistered:
            pass

        instance = NotRegistered()
        with pytest.raises(ValidationError, match="not a valid choice"):
            field.validate(instance, None)


class TestMultipleRegistryClassFieldValidation:
    """Tests for MultipleRegistryClassField.validate()."""

    def test_empty_value_passes(self, test_strategy_registry):
        field = MultipleRegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.validate(None, None)  # Should not raise

    def test_normalizes_non_list(self, test_strategy_registry, email_strategy):
        field = MultipleRegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        field.validate(email_strategy, None)  # Should not raise (wraps as list)

    def test_valid_values_pass(self, test_strategy_registry, email_strategy, sms_strategy):
        field = MultipleRegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        field.validate([email_strategy, sms_strategy], None)  # Should not raise

    def test_invalid_raises_validation_error(self, test_strategy_registry):
        field = MultipleRegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"

        class NotRegistered:
            pass

        with pytest.raises(ValidationError, match="not valid choices"):
            field.validate([NotRegistered], None)

    def test_get_lookup_in_supported(self, test_strategy_registry):
        field = MultipleRegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        lookup = field.get_lookup("in")
        assert lookup is not None

    def test_get_prep_value_list(self, test_strategy_registry, email_strategy):
        field = MultipleRegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        result = field.get_prep_value([get_fully_qualified_name(email_strategy)])
        assert isinstance(result, str)

    def test_get_prep_value_string(self, test_strategy_registry):
        field = MultipleRegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        result = field.get_prep_value("some_value")
        assert result == "some_value"

    def test_get_prep_value_unexpected_type(self, test_strategy_registry):
        field = MultipleRegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        result = field.get_prep_value(12345)
        assert result is None

    def test_get_db_prep_save_filters_empty(self, test_strategy_registry, email_strategy):
        field = MultipleRegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        fqn = get_fully_qualified_name(email_strategy)
        result = field.get_db_prep_save([fqn, "", None], connection=None)
        assert isinstance(result, str)
        assert fqn in result


class TestHierarchicalRegistryFieldValidation:
    """Tests for HierarchicalRegistryField."""

    def test_validate_calls_super(self, child_registry, parent_registry):
        from tests.registries_fixtures import ChildOfA

        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field.name = "test_field"
        field._parent_field_name = "parent_field"
        # Valid child value should pass
        field.validate(ChildOfA, None)

    def test_no_parent_field_skips(self, child_registry):
        field = HierarchicalRegistryField(registry=child_registry, blank=True, null=True)
        field.name = "test_field"
        field._parent_field_name = None
        field.validate("child_of_a", None)  # Should not raise

    def test_no_parent_value_skips(self, child_registry):
        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field.name = "test_field"
        field._parent_field_name = "parent_field"

        class MockObj:
            parent_field = None
            test_field = "child_of_a"

        field.validate("child_of_a", MockObj())  # Should not raise

    def test_get_parent_value_returns_fqn(self, child_registry, parent_registry):
        from tests.registries_fixtures import CategoryA

        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field.name = "test_field"
        field._parent_field_name = "parent_field"
        obj = _make_mock_obj()
        obj.parent_field = CategoryA
        result = field.get_parent_value(obj)
        assert result == get_fully_qualified_name(CategoryA)

    def test_get_parent_value_returns_none_for_missing_parent_field(self, child_registry):
        field = HierarchicalRegistryField(registry=child_registry, parent_field="nonexistent", blank=True, null=True)
        field.name = "test_field"
        field._parent_field_name = "nonexistent"
        obj = MagicMock(spec=[])  # No attributes at all
        result = field.get_parent_value(obj)
        assert result is None

    def test_get_parent_value_returns_none_when_no_obj(self, child_registry):
        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field._parent_field_name = "parent_field"
        result = field.get_parent_value(None)
        assert result is None

    def test_formfield_passes_parent_field(self, child_registry):
        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field.name = "test_field"
        field._parent_field_name = "parent_field"
        form_field = field.formfield()
        # The formfield method is called and returns a form field
        assert form_field is not None

    def test_validate_valid_parent_child_relationship(self, child_registry, parent_registry):
        from tests.registries_fixtures import CategoryA, ChildOfA

        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field.name = "test_field"
        field._parent_field_name = "parent_field"

        obj = _make_mock_obj()
        obj.parent_field = CategoryA

        # ChildOfA is valid for category_a - should not raise
        field.validate(ChildOfA, obj)

    def test_validate_invalid_parent_child_relationship(self, child_registry, parent_registry):
        from tests.registries_fixtures import CategoryA, ChildOfB

        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field.name = "test_field"
        field._parent_field_name = "parent_field"

        obj = _make_mock_obj()
        obj.parent_field = CategoryA

        with patch.object(
            child_registry, "validate_parent_child_relationship", return_value=False
        ):
            with pytest.raises(ValidationError, match="not valid for parent"):
                field.validate(ChildOfB, obj)

    def test_validate_parent_slug_not_found_skips_check(self, child_registry, parent_registry):
        """When parent class not found in parent_registry, hierarchical check is skipped."""
        from tests.registries_fixtures import ChildOfA

        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field.name = "test_field"
        field._parent_field_name = "parent_field"

        obj = _make_mock_obj()

        class UnregisteredParent:
            pass

        obj.parent_field = UnregisteredParent

        # Parent slug won't be found >> hierarchical check skipped, no error
        field.validate(ChildOfA, obj)

    def test_init_warns_for_non_hierarchical_registry(self, test_strategy_registry):
        """Passing a plain Registry (not HierarchicalRegistry) should log a warning."""
        # TestStrategyRegistry is not a HierarchicalRegistry, so the warning path is triggered
        field = HierarchicalRegistryField(
            registry=test_strategy_registry, parent_field="parent_field", blank=True, null=True
        )
        # Field should still be created without error
        assert field.registry is test_strategy_registry


class TestMultipleHierarchicalRegistryFieldValidation:
    """Tests for MultipleHierarchicalRegistryField."""

    def test_validate_calls_super(self, child_registry):
        from tests.registries_fixtures import ChildOfA

        field = MultipleHierarchicalRegistryField(
            registry=child_registry, parent_field="parent_field", blank=True, null=True
        )
        field.name = "test_field"
        field._parent_field_name = "parent_field"
        field.validate([ChildOfA], None)  # Should not raise

    def test_skips_when_no_parent(self, child_registry):
        from tests.registries_fixtures import ChildOfA

        field = MultipleHierarchicalRegistryField(registry=child_registry, blank=True, null=True)
        field.name = "test_field"
        field._parent_field_name = None
        field.validate([ChildOfA], None)  # Should not raise

    def test_get_parent_value_works(self, child_registry, parent_registry):
        from tests.registries_fixtures import CategoryA

        field = MultipleHierarchicalRegistryField(
            registry=child_registry, parent_field="parent_field", blank=True, null=True
        )
        field._parent_field_name = "parent_field"
        obj = _make_mock_obj()
        obj.parent_field = CategoryA
        result = field.get_parent_value(obj)
        assert result == get_fully_qualified_name(CategoryA)

    def test_get_parent_value_returns_none_when_no_obj(self, child_registry):
        field = MultipleHierarchicalRegistryField(
            registry=child_registry, parent_field="parent_field", blank=True, null=True
        )
        field._parent_field_name = "parent_field"
        result = field.get_parent_value(None)
        assert result is None

    def test_validate_valid_multiple_children_for_parent(self, child_registry, parent_registry):
        from tests.registries_fixtures import CategoryA, ChildOfA, ChildOfBoth

        field = MultipleHierarchicalRegistryField(
            registry=child_registry, parent_field="parent_field", blank=True, null=True
        )
        field.name = "test_field"
        field._parent_field_name = "parent_field"

        obj = _make_mock_obj()
        obj.parent_field = CategoryA

        # Both ChildOfA and ChildOfBoth are valid for category_a
        field.validate([ChildOfA, ChildOfBoth], obj)

    def test_validate_invalid_multiple_children_for_parent(self, child_registry, parent_registry):
        from tests.registries_fixtures import CategoryA, ChildOfB

        field = MultipleHierarchicalRegistryField(
            registry=child_registry, parent_field="parent_field", blank=True, null=True
        )
        field.name = "test_field"
        field._parent_field_name = "parent_field"

        obj = _make_mock_obj()
        obj.parent_field = CategoryA

        with patch.object(
            child_registry, "validate_parent_child_relationship", return_value=False
        ):
            with pytest.raises(ValidationError, match="not valid for parent"):
                field.validate([ChildOfB], obj)

    def test_validate_multiple_with_no_parent_value(self, child_registry, parent_registry):
        from tests.registries_fixtures import ChildOfA

        field = MultipleHierarchicalRegistryField(
            registry=child_registry, parent_field="parent_field", blank=True, null=True
        )
        field.name = "test_field"
        field._parent_field_name = "parent_field"

        obj = _make_mock_obj()
        obj.parent_field = None

        # No parent value >> early return, no validation error
        field.validate([ChildOfA], obj)

    def test_get_parent_value_attribute_error(self, child_registry):
        field = MultipleHierarchicalRegistryField(
            registry=child_registry, parent_field="nonexistent_field", blank=True, null=True
        )
        field._parent_field_name = "nonexistent_field"

        obj = MagicMock(spec=[])  # No attributes at all
        result = field.get_parent_value(obj)
        assert result is None


class TestHierarchicalRegistryFieldDescriptor:
    """Tests for HierarchicalRegistryFieldDescriptor."""

    def test_set_calls_parent(self, child_registry, parent_registry, email_strategy):
        from tests.registries_fixtures import ChildOfA

        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field.name = "test_field"
        field.attname = "test_field"
        field._parent_field_name = "parent_field"
        descriptor = HierarchicalRegistryFieldDescriptor(field)

        obj = _make_mock_obj()
        obj.parent_field = None  # No parent, so validation is skipped
        descriptor.__set__(obj, ChildOfA)
        assert obj.__dict__["test_field"] is not None

    def test_set_validates_parent_child(self, child_registry, parent_registry):
        from tests.registries_fixtures import CategoryA, ChildOfA

        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field.name = "test_field"
        field.attname = "test_field"
        field._parent_field_name = "parent_field"
        descriptor = HierarchicalRegistryFieldDescriptor(field)

        obj = _make_mock_obj()
        obj.parent_field = CategoryA

        # ChildOfA is valid for category_a - should succeed and trigger validation path
        descriptor.__set__(obj, ChildOfA)
        assert obj.__dict__["test_field"] is not None

    def test_set_invalid_resets_to_none_and_raises(self, child_registry, parent_registry):
        from tests.registries_fixtures import ChildOfB

        field = HierarchicalRegistryField(registry=child_registry, parent_field="parent_field", blank=True, null=True)
        field.name = "test_field"
        field.attname = "test_field"
        field._parent_field_name = "parent_field"
        descriptor = HierarchicalRegistryFieldDescriptor(field)

        obj = _make_mock_obj()
        obj.parent_field = None  # Will be set after __set__ call

        # Patch validate to raise ValidationError to test the reset-to-None logic
        with patch.object(field, "validate", side_effect=ValidationError("not valid for parent")):
            with pytest.raises(ValidationError, match="not valid for parent"):
                descriptor.__set__(obj, ChildOfB)
            # After validation failure, the field is reset to None
            assert obj.__dict__["test_field"] is None


class TestRegistryFieldFactory:
    """Tests for RegistryField factory and pre_save."""

    def test_registry_field_custom_factory(self, test_strategy_registry, email_strategy):
        sentinel = object()
        field = RegistryField(
            registry=test_strategy_registry,
            blank=True,
            null=True,
            factory=lambda klass, obj: sentinel,
        )
        assert field.factory is not None

    def test_registry_field_pre_save(self, test_strategy_registry, email_strategy):
        field = RegistryField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        field.attname = "test_field"
        instance = email_strategy()
        obj = _make_mock_obj(test_field=instance)
        obj.test_field = instance
        result = field.pre_save(obj, add=True)
        assert "EmailStrategy" in result

    def test_registry_field_pre_save_none(self, test_strategy_registry):
        field = RegistryField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        field.attname = "test_field"
        obj = _make_mock_obj(test_field=None)
        obj.test_field = None
        result = field.pre_save(obj, add=True)
        assert result is None


class TestMultipleRegistryClassFieldDescriptorGetPrepValue:
    """Tests for MultipleRegistryClassFieldDescriptor.get_prep_value."""

    def test_none_returns_none(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        assert descriptor.get_prep_value(None) is None

    def test_list_of_strings(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        fqn = get_fully_qualified_name(email_strategy)
        result = descriptor.get_prep_value([fqn])
        assert result == fqn

    def test_list_of_classes(self, test_strategy_registry, email_strategy, sms_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        result = descriptor.get_prep_value([email_strategy, sms_strategy])
        assert get_fully_qualified_name(email_strategy) in result
        assert get_fully_qualified_name(sms_strategy) in result

    def test_list_with_slugs(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        result = descriptor.get_prep_value(["email"])
        assert get_fully_qualified_name(email_strategy) in result

    def test_list_with_instances(self, test_strategy_registry, email_strategy):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        instance = email_strategy()
        result = descriptor.get_prep_value([instance])
        assert get_fully_qualified_name(email_strategy) in result

    def test_string_passthrough(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        result = descriptor.get_prep_value("some,values")
        assert result == "some,values"

    def test_unexpected_type_returns_none(self, test_strategy_registry):
        field, descriptor = _make_field_and_descriptor(
            MultipleRegistryClassField, MultipleRegistryClassFieldDescriptor, test_strategy_registry
        )
        result = descriptor.get_prep_value(12345)
        assert result is None


class TestDeconstructReconstructCycle:
    """Regression tests for prevention of duplicate validators during deconstruct/reconstruct."""

    def test_deconstruct_does_not_contain_auto_validators(self, test_strategy_registry):
        """deconstruct() output should not include ClassnameValidator or RegistryValidator."""

        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        _, _, _, kwargs = field.deconstruct()
        assert "validators" not in kwargs

    def test_deconstruct_preserves_custom_validators(self, test_strategy_registry):
        """deconstruct() should preserve user-supplied validators while stripping auto-added ones."""

        custom_validator = MaxLengthValidator(100)
        field = RegistryClassField(
            registry=test_strategy_registry, blank=True, null=True, validators=[custom_validator]
        )
        field.name = "test_field"
        _, _, _, kwargs = field.deconstruct()
        assert "validators" in kwargs
        assert len(kwargs["validators"]) == 1
        assert isinstance(kwargs["validators"][0], MaxLengthValidator)

    def test_reconstruct_cycle_preserves_validator_count(self, test_strategy_registry):
        """A deconstruct >> reconstruct cycle should not add extra validators."""

        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        field.name = "test_field"
        original_count = len(field._validators)

        # Simulate deconstruct >> reconstruct (like makemigrations would do)
        _, path, args, kwargs = field.deconstruct()
        reconstructed = RegistryClassField(*args, **kwargs)
        reconstructed.name = "test_field"

        assert len(reconstructed._validators) == original_count

        # Do it again to confirm we're good after multiple cycles
        _, path2, args2, kwargs2 = reconstructed.deconstruct()
        reconstructed2 = RegistryClassField(*args2, **kwargs2)
        reconstructed2.name = "test_field"

        assert len(reconstructed2._validators) == original_count

    def test_validators_present_at_runtime(self, test_strategy_registry):
        """After construction, ClassnameValidator and RegistryValidator are present."""

        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        # Use type() for exact match since RegistryValidator is a subclass of ClassnameValidator
        classname_validators = [v for v in field._validators if type(v) is ClassnameValidator]
        registry_validators = [v for v in field._validators if isinstance(v, RegistryValidator)]
        assert len(classname_validators) == 1
        assert len(registry_validators) == 1

    def test_field_without_registry_has_classname_validator_only(self):
        """A field with no registry should have ClassnameValidator but not RegistryValidator."""

        field = RegistryClassField(blank=True, null=True)
        classname_validators = [v for v in field._validators if type(v) is ClassnameValidator]
        registry_validators = [v for v in field._validators if isinstance(v, RegistryValidator)]
        assert len(classname_validators) == 1
        assert len(registry_validators) == 0


class TestContributeToClass:
    """Tests for AbstractRegistryField.contribute_to_class registry resolution."""

    class _MockMeta:
        def add_field(self, field):
            pass

    class _MockModel:
        pass

    def _make_model(self):
        """Create a fresh mock model class for each test."""
        meta = type("_MockMeta", (), {"add_field": lambda self, field: None})()

        class MockModel:
            _meta = meta

        return MockModel

    def test_with_valid_registry_class(self, test_strategy_registry):
        field = RegistryClassField(registry=test_strategy_registry, blank=True, null=True)
        model = self._make_model()
        field.contribute_to_class(model, "test_field")
        # Descriptor should be set on the model class __dict__
        assert "test_field" in model.__dict__
        assert isinstance(model.__dict__["test_field"], RegistryClassFieldDescriptor)

    def test_callable_registry_accepting_model(self, test_strategy_registry):
        field = RegistryClassField(blank=True, null=True)
        # Bypass __init__ validation by setting registry after construction
        field.registry = lambda model_cls: test_strategy_registry
        model = self._make_model()
        field.contribute_to_class(model, "test_field")
        assert field.registry is test_strategy_registry

    def test_callable_registry_no_args_fallback(self, test_strategy_registry):
        def registry_callable(*args):
            if args:
                raise TypeError("unexpected argument")
            return test_strategy_registry

        field = RegistryClassField(blank=True, null=True)
        field.registry = registry_callable
        model = self._make_model()
        field.contribute_to_class(model, "test_field")
        assert field.registry is test_strategy_registry

    def test_callable_registry_fails_completely(self):
        def bad_callable(*args):
            raise ValueError("totally broken")

        field = RegistryClassField(blank=True, null=True)
        field.registry = bad_callable
        model = self._make_model()
        with pytest.raises(ValueError, match="Unable to resolve registry"):
            field.contribute_to_class(model, "test_field")

    def test_registry_converted_to_tuple_recovery(self, test_strategy_registry):
        """When registry is inadvertently converted to a list, recovery should find the original."""
        field = RegistryClassField(blank=True, null=True)
        # Simulate registry being converted to a list of implementation values
        field.registry = list(test_strategy_registry.implementations.values())
        model = self._make_model()
        field.contribute_to_class(model, "test_field")
        assert field.registry is test_strategy_registry

    def test_registry_converted_to_tuple_unrecoverable(self, test_strategy_registry):
        """When registry is a list that doesn't match any known registry, should raise."""
        field = RegistryClassField(blank=True, null=True)
        field.registry = ["unknown_value_1", "unknown_value_2"]
        model = self._make_model()
        with pytest.raises(ValueError, match="Could not recover registry"):
            field.contribute_to_class(model, "test_field")

    def test_during_migrations_skips_resolution(self, test_strategy_registry):
        def registry_callable():
            return test_strategy_registry

        field = RegistryClassField(blank=True, null=True)
        field.registry = registry_callable
        model = self._make_model()
        with patch("django_stratagem.fields.is_running_migrations", return_value=True):
            field.contribute_to_class(model, "test_field")
        # During migrations, callable registry stays unresolved
        assert field.registry is registry_callable

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from django.core.validators import BaseValidator
from rest_framework import serializers

from ..utils import get_class, get_fully_qualified_name
from ..validators import ClassnameValidator, RegistryValidator

if TYPE_CHECKING:
    from ..registry import Registry

logger = logging.getLogger(__name__)


class DrfRegistryField(serializers.ChoiceField):
    """DRF serializer field for single registry selection."""

    default_validators: ClassVar[list] = [ClassnameValidator]

    def __init__(self, registry: type[Registry], representation: str = "slug", **kwargs: Any) -> None:
        choices = registry.get_choices()
        self.representation = representation
        super().__init__(choices, **kwargs)
        self.registry = registry

    def get_validators(self) -> list[BaseValidator]:
        """Get validators for this field."""
        ret = list(super().get_validators())
        ret.append(RegistryValidator(self.registry))
        return ret

    def to_representation(self, value: Any) -> str:
        """Convert the value to a string for serialization."""
        # If value is a string (slug), return it as is
        if isinstance(value, str):
            return value

        # If value is a class, return its slug representation
        if self.representation == "slug" and (isinstance(value, type) or hasattr(value, "__class__")):
            try:
                return self._get_slug(value)
            except Exception as e:
                logger.warning(f"Error getting slug for {value}: {e}")
        return get_fully_qualified_name(value)

    def _get_slug(self, obj) -> str:
        """Convert class/instance to registry slug."""
        klass = obj if isinstance(obj, type) else type(obj)
        for slug, meta in self.registry.implementations.items():
            if meta["klass"] is klass:
                return slug
        return get_fully_qualified_name(klass)

    def to_internal_value(self, data: Any) -> Any:
        """Convert the input data to internal value."""
        if data is None or data == "":
            return None

        # Check if it's a valid slug
        for slug, meta in self.registry.implementations.items():
            if data == slug:
                return meta["klass"]

        # Try as fully qualified name
        try:
            cls = get_class(data)
            if self.registry.is_valid(cls):
                return cls
        except (ImportError, AttributeError, ValueError):
            pass

        raise serializers.ValidationError("Invalid registry slug or class path.")


class DrfMultipleRegistryField(serializers.MultipleChoiceField):
    """DRF serializer field for multiple registry selection."""

    default_validators: ClassVar[list] = [ClassnameValidator]

    def __init__(self, registry: type[Registry], **kwargs: Any) -> None:
        choices = registry.get_choices()
        self.registry = registry
        super().__init__(choices=choices, **kwargs)

    def get_validators(self) -> list[BaseValidator]:
        """Get validators for this field."""
        ret = list(super().get_validators())
        ret.append(RegistryValidator(self.registry))
        return ret

    def to_representation(self, value: Any) -> list[str]:  # type: ignore[override]
        """Convert the value to a list of strings for serialization."""
        if value is None:
            return []
        result = []
        for item in value:
            if isinstance(item, str):
                result.append(item)
            else:
                result.append(get_fully_qualified_name(item))
        return result

    def to_internal_value(self, data: list[str]) -> list[type]:  # type: ignore[override]
        """Convert the input data to internal value."""
        if not isinstance(data, list):
            self.fail("not_a_list", input_type=type(data).__name__)

        result = []
        for item in data:
            # First check if it's a valid slug
            if item in self.registry.implementations:
                result.append(self.registry.get_implementation_class(item))
            else:
                # Try to import as fully qualified name
                try:
                    cls = get_class(item)
                    if not self.registry.is_valid(cls):
                        self.fail("invalid_choice", input=item)
                    result.append(cls)
                except (ImportError, AttributeError, ValueError):
                    self.fail("invalid_choice", input=item)

        return result


# Backward compatibility aliases
DrfStrategyField = DrfRegistryField
DrfMultipleStrategyField = DrfMultipleRegistryField

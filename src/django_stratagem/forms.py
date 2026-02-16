from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.forms.fields import ChoiceField, TypedMultipleChoiceField
from django.forms.forms import BaseForm

from .utils import get_class, get_fully_qualified_name

if TYPE_CHECKING:
    from django.db.models import Model

    from .registry import Registry

logger = logging.getLogger(__name__)


class RegistryFormField(ChoiceField):
    """Form field for selecting a single registry implementation."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.registry = kwargs.pop("registry")
        self.empty_value = kwargs.pop("empty_value", "")
        super().__init__(*args, **kwargs)

    def prepare_value(self, value: str | type) -> str | None:
        """Prepare value for display in form."""
        if isinstance(value, str):
            return value
        if value:
            # Convert class to slug for display
            if isinstance(value, type):
                # Find the slug for this class
                for slug, meta in self.registry.implementations.items():
                    if meta["klass"] == value:
                        return slug
                # Fallback to fully qualified name if slug not found
                logger.warning(f"Could not find slug for class {value} in registry {self.registry}")
                return get_fully_qualified_name(value)
            # It's an instance, get its class and find the slug
            klass = type(value)
            for slug, meta in self.registry.implementations.items():
                if meta["klass"] == klass:
                    return slug
            # Fallback
            return get_fully_qualified_name(klass)
        return None

    def valid_value(self, value: str) -> bool:
        """Check if value is valid for this field."""
        # Check if it's a valid choice slug
        if super().valid_value(value):
            return True
        # Check if it's a valid fully qualified name
        return self.registry.is_valid(value)

    def _coerce(self, value: str) -> Any:
        """Coerce value to the appropriate type."""
        if value == self.empty_value or value in self.empty_values:
            return self.empty_value
        try:
            # First try to get by slug
            if value in self.registry.implementations:
                return self.registry.get_implementation_class(value)
            # Then try as fully qualified name
            v = get_class(value)
            if self.registry.is_valid(v):
                return v
            raise ValidationError(
                self.error_messages["invalid_choice"],
                code="invalid_choice",
                params={"value": f"'{value}'"},
            )
        except (ValueError, TypeError, ValidationError, ImportError, ModuleNotFoundError):
            raise ValidationError(
                self.error_messages["invalid_choice"],
                code="invalid_choice",
                params={"value": f"'{value}'"},
            ) from None

    def clean(self, value: Any) -> type:
        """Clean and validate the value."""
        value = super().clean(value)
        return self._coerce(value)


class RegistryMultipleChoiceFormField(TypedMultipleChoiceField):
    """Form field for selecting multiple registry implementations."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.registry: Registry = kwargs.pop("registry")
        kwargs["coerce"] = self.coerce
        super().__init__(*args, **kwargs)

    def prepare_value(self, value: str | Sequence[str | type]) -> list[str] | None:
        """Prepare value for display in form."""
        if value is None:
            return None

        # Handle string input (comma-separated)
        if isinstance(value, str):
            return [v.strip() for v in value.split(",")]

        # Handle list/tuple input
        if isinstance(value, (list, tuple)):
            ret = []
            for item in value:
                if isinstance(item, str):
                    ret.append(item)
                elif isinstance(item, type):
                    # Convert class to slug
                    found_slug = None
                    for slug, meta in self.registry.implementations.items():
                        if meta["klass"] == item:
                            found_slug = slug
                            break
                    if found_slug:
                        ret.append(found_slug)
                    else:
                        # Fallback to fully qualified name
                        ret.append(get_fully_qualified_name(item))
                else:
                    # It's an instance
                    klass = type(item)
                    found_slug = None
                    for slug, meta in self.registry.implementations.items():
                        if meta["klass"] == klass:
                            found_slug = slug
                            break
                    if found_slug:
                        ret.append(found_slug)
                    else:
                        ret.append(get_fully_qualified_name(klass))
            return ret

        # Single non-string value
        if isinstance(value, type):
            # Convert class to slug
            for slug, meta in self.registry.implementations.items():
                if meta["klass"] == value:
                    return [slug]
            return [get_fully_qualified_name(value)]

        return None

    def coerce(self, value: str) -> type | None:
        """Coerce a single value."""
        # First try to get by slug
        if value in self.registry.implementations:
            return self.registry.get_implementation_class(value)
        # Then try as fully qualified name
        try:
            return get_class(value)
        except (ImportError, ValueError, AttributeError):
            return None

    def valid_value(self, value: str) -> bool:
        """Check if value is valid for this field."""
        return self.registry.is_valid(value)


class ContextAwareRegistryFormField(RegistryFormField):
    """Form field that filters choices based on context."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.context = kwargs.pop("context", None)
        super().__init__(*args, **kwargs)
        self._update_choices()

    def _update_choices(self) -> None:
        """Update choices based on context."""
        if self.context is not None and self.registry:
            self.choices = self.registry.get_choices_for_context(self.context)

    def set_context(self, context: dict[str, Any]) -> None:
        """Update the context and refresh choices."""
        self.context = context
        self._update_choices()

    def valid_value(self, value: str) -> bool:
        """Check if value is valid in the current context."""
        if self.context is None:
            return super().valid_value(value)

        # Check against available implementations
        available = self.registry.get_available_implementations(self.context)

        # Check if it's a valid slug in context
        if value in available:
            return True

        # Check if it's a valid fully qualified name in context
        try:
            impl_cls = get_class(value)
            return impl_cls in available.values()
        except (ImportError, ValueError, AttributeError):
            return False


class HierarchicalRegistryFormField(ContextAwareRegistryFormField):
    """Form field that updates choices based on parent field selection."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.parent_field = kwargs.pop("parent_field", None)
        self.parent_value = kwargs.pop("parent_value", None)
        super().__init__(*args, **kwargs)
        self._update_choices_from_parent()

    def _update_choices_from_parent(self) -> None:
        """Update choices based on current parent value."""
        if not self.parent_value or not hasattr(self.registry, "get_choices_for_parent"):
            return

        # Get parent slug from value
        parent_slug = self._get_parent_slug(self.parent_value)
        if parent_slug:
            # Update choices based on parent
            context = getattr(self, "context", None)
            self.choices = self.registry.get_choices_for_parent(parent_slug, context)

    def _get_parent_slug(self, parent_value: Any) -> str | None:
        """Extract parent slug from parent value."""
        if not parent_value:
            return None

        # If parent_value is already a slug
        if isinstance(parent_value, str) and "." not in parent_value:
            return parent_value

        # Get parent registry and find slug
        if hasattr(self.registry, "parent_registry"):
            parent_registry = self.registry.parent_registry

            try:
                if isinstance(parent_value, str):
                    parent_class = get_class(parent_value)
                else:
                    parent_class = parent_value if isinstance(parent_value, type) else type(parent_value)
            except (ImportError, ValueError, AttributeError):
                return None

            for parent_slug, meta in parent_registry.implementations.items():
                if meta["klass"] == parent_class:
                    return parent_slug

        return None

    def set_parent_value(self, parent_value: Any) -> None:
        """Update parent value and refresh choices."""
        self.parent_value = parent_value
        self._update_choices_from_parent()

    def valid_value(self, value: str) -> bool:
        """Check if value is valid for current parent."""
        if not self.parent_value:
            # No parent selected, check general validity
            return super().valid_value(value)

        # Check if value is in current (parent-filtered) choices
        return ChoiceField.valid_value(self, value)


class RegistryContextMixin(BaseForm):
    """Mixin for forms that need registry context."""

    def __init__(self, *args, **kwargs):
        # Extract context from kwargs
        self.registry_context = kwargs.pop("registry_context", None)
        super().__init__(*args, **kwargs)

        # Update any context-aware registry fields
        for field_name, field in self.fields.items():
            if isinstance(field, ContextAwareRegistryFormField):
                if self.registry_context:
                    field.set_context(self.registry_context)


class HierarchicalFormMixin(BaseForm):
    """Mixin for forms with hierarchical registry fields."""

    instance: Model | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_hierarchical_fields()

    def _setup_hierarchical_fields(self):
        """Set up parent-child relationships in form fields."""
        # Find hierarchical fields
        hierarchical_fields = []
        for name, field in self.fields.items():
            if isinstance(field, HierarchicalRegistryFormField):
                hierarchical_fields.append((name, field))

        # Set up parent values
        for name, field in hierarchical_fields:
            if field.parent_field and field.parent_field in self.fields:
                # Get initial parent value
                parent_value = None
                if getattr(self, "instance", None) and hasattr(self.instance, field.parent_field):
                    parent_value = getattr(self.instance, field.parent_field)
                elif self.initial and field.parent_field in self.initial:
                    parent_value = self.initial[field.parent_field]

                if parent_value:
                    field.set_parent_value(parent_value)

    def clean(self):
        """Validate hierarchical relationships."""
        cleaned_data = super().clean()

        # Validate parent-child relationships
        for name, field in self.fields.items():
            if isinstance(field, HierarchicalRegistryFormField) and field.parent_field:
                parent_value = cleaned_data.get(field.parent_field)
                child_value = cleaned_data.get(name)

                if parent_value and child_value:
                    # Update field with current parent
                    field.set_parent_value(parent_value)

                    # Revalidate child with updated parent
                    if not field.valid_value(child_value):
                        self.add_error(name, f"Invalid selection for the chosen {field.parent_field}")

        return cleaned_data

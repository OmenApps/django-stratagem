from __future__ import annotations

import logging
from collections.abc import Sequence
from inspect import isclass
from typing import TYPE_CHECKING, Any, Protocol

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Field, Model
from django.db.models.fields import BLANK_CHOICE_DASH
from django.db.models.lookups import Lookup
from django.utils.text import capfirst

from .exceptions import RegistryNameError
from .registry import HierarchicalRegistry, Registry
from .utils import get_class, get_fully_qualified_name, is_running_migrations, stringify
from .validators import ClassnameValidator, RegistryValidator

if TYPE_CHECKING:
    from django.db.backends.base.base import BaseDatabaseWrapper
    from django.db.models.base import ModelBase

logger = logging.getLogger(__name__)


class ImplementationDescriptor(Protocol):
    """Protocol for field descriptors that resolve registry implementations."""

    def __init__(self, field: Any) -> None: ...

    def __get__(self, obj: Any, __: Any) -> Any: ...

    def __set__(self, obj: Any, original: Any) -> None: ...


class RegistryClassFieldDescriptor:
    """Descriptor for fields that return implementation classes.

    Resolution order: slug is checked first against registry.implementations,
    then fully qualified name (FQN) is tried via import_by_name().
    """

    def __init__(self, field: RegistryClassField) -> None:
        """Initialize the descriptor with its parent field."""
        self.field = field
        # Only log if not running migrations
        if not is_running_migrations():
            logger.debug(
                f"Initialized RegistryClassFieldDescriptor for field: {field.name if hasattr(field, 'name') else 'unnamed'}"
            )

    def __get__(self, obj: Model | None, value: type[Model] | None = None) -> type | None:
        """Retrieve the class value from the model instance."""
        if obj is None:
            return None

        if self.field.name is None:
            raise RuntimeError("Field name not initialized")
        raw_value = obj.__dict__.get(self.field.name)  # type: ignore[attr-defined]
        if raw_value is None:
            return None

        # If it's already a class, return it
        if isinstance(raw_value, type):
            return raw_value

        # If it's a string (from database), convert it to a class
        if isinstance(raw_value, str):
            try:
                # First check if it's a slug
                if (
                    hasattr(self.field, "registry")
                    and self.field.registry
                    and raw_value in self.field.registry.implementations
                ):
                    value = self.field.registry.get_implementation_class(raw_value)
                else:
                    # Try as fully qualified name
                    value = get_class(raw_value)

                # Cache the converted value
                obj.__dict__[self.field.name] = value  # type: ignore[index]
                return value
            except (ImportError, AttributeError, RegistryNameError, ValueError) as e:
                if not is_running_migrations():
                    logger.warning(
                        f"Failed to convert stored value '{raw_value}' to class for field {self.field.name}: {e}"
                    )
                return None

        # Unknown type
        if not is_running_migrations():
            logger.warning(f"Unexpected type {type(raw_value)} for field {self.field.name}")
        return raw_value

    def __set__(self, obj: Model, original: str | type | None) -> None:
        """Set the field value by converting a string to a class or accepting a class directly."""
        if self.field.name is None:
            raise RuntimeError("Field name not initialized")
        if original is None:
            value = None
            raw_value = None
            if not is_running_migrations():
                logger.debug(f"Setting {self.field.name} to None (empty original value)")
        # Handle case where original is already a class
        elif isinstance(original, type):
            value = original
            raw_value = get_fully_qualified_name(original)
            if not is_running_migrations():
                logger.debug(f"Received class {original} for field {self.field.name}")
        else:
            # Handle string case (fully qualified name or slug)
            try:
                # First check if it's a slug
                if (
                    hasattr(self.field, "registry")
                    and self.field.registry
                    and original in self.field.registry.implementations
                ):
                    value = self.field.registry.get_implementation_class(original)
                    raw_value = get_fully_qualified_name(value)
                    if not is_running_migrations():
                        logger.debug(f"Successfully loaded class from slug {original} for field {self.field.name}")
                else:
                    # Try as fully qualified name
                    value = get_class(original)
                    raw_value = get_fully_qualified_name(original)
                    if not is_running_migrations():
                        logger.debug(f"Successfully loaded class {original} for field {self.field.name}")
            except (AttributeError, ModuleNotFoundError, ImportError, RegistryNameError) as e:
                if not is_running_migrations():
                    logger.warning(
                        f"Failed to import class '{original}' for field {self.field.name}: {type(e).__name__}: {e}"
                    )
                if callable(self.field.import_error):
                    value = self.field.import_error(original, e)
                else:
                    value = self.field.import_error
                raw_value = original  # Store the original value even if import failed
            except Exception as e:
                if not is_running_migrations():
                    logger.exception(f"Unexpected error importing class '{original}' for field {self.field.name}")
                raise ValidationError(f"Unable to import '{original}': {type(e).__name__}: {e!s}") from e

        obj.__dict__[self.field.name] = value  # type: ignore[index]
        obj.__dict__[f"_registry_fully_qualified_name_{self.field.name}"] = raw_value  # type: ignore[index]


class MultipleRegistryClassFieldDescriptor:
    """Descriptor for fields that return multiple implementation classes."""

    def __init__(self, field: MultipleRegistryClassField) -> None:
        """Initialize the descriptor with its parent field."""
        self.field = field
        if not is_running_migrations():
            logger.debug(
                f"Initialized MultipleRegistryClassFieldDescriptor for field: {field.name if hasattr(field, 'name') else 'unnamed'}"
            )

    def __get__(self, obj: Model | None, __: type[ModelBase] | None = None) -> list[type] | None:
        """Retrieve the list of classes from the model instance."""
        if obj is None:
            return None

        if self.field.name is None:
            raise RuntimeError("Field name not initialized")
        values = obj.__dict__.get(self.field.name)  # type: ignore[attr-defined]
        if values is None:
            return None

        # Handle case where values are already classes
        if isinstance(values, list) and all(isinstance(v, type) for v in values):
            return values

        # Normalize value to a list
        normalized = []
        if isinstance(values, str):
            normalized = [value.strip() for value in values.split(",") if value.strip()]
        elif not isinstance(values, (list, tuple)):
            normalized = [values] if values is not None else []
        else:
            normalized = list(values)

        ret = []
        errors = []

        for value in normalized:
            if not value:
                continue

            # If value is already a class, use it directly
            if isinstance(value, type):
                ret.append(value)
                continue

            # Otherwise try to load it
            try:
                # Check if it's a slug first
                if (
                    hasattr(self.field, "registry")
                    and self.field.registry
                    and value in self.field.registry.implementations
                ):
                    class_obj = self.field.registry.get_implementation_class(value)
                else:
                    class_obj = get_class(value)
                ret.append(class_obj)
                if not is_running_migrations():
                    logger.debug(f"Successfully loaded class {value} for field {self.field.name}")
            except (AttributeError, ModuleNotFoundError, ImportError, RegistryNameError) as e:
                if not is_running_migrations():
                    logger.warning(
                        f"Failed to import class '{value}' for field {self.field.name}: {type(e).__name__}: {e}"
                    )
                errors.append((value, e))

        # Handle import errors if any occurred
        if errors and self.field.import_error is not None:
            if callable(self.field.import_error):
                result = self.field.import_error([value for value, _ in errors], errors[0][1])
                return result if isinstance(result, list) else None
            return self.field.import_error if isinstance(self.field.import_error, (list, type(None))) else None

        # Cache the converted values
        if ret:
            obj.__dict__[self.field.name] = ret  # type: ignore[index]

        return ret

    def __set__(self, obj: Model, original: Any) -> None:
        """Store the raw value in the model instance."""
        if self.field.name is None:
            raise RuntimeError("Field name not initialized")
        # Convert classes to fully qualified names for storage
        value = original
        if value is not None:
            if isinstance(value, list) and all(isinstance(v, type) for v in value):
                # Convert list of classes to comma-separated string of fully qualified names
                value = ",".join(get_fully_qualified_name(v) for v in value)
            elif isinstance(value, type):
                # Single class to fully qualified name
                value = get_fully_qualified_name(value)

        obj.__dict__[self.field.name] = value  # type: ignore[index]

    def get_prep_value(self, value: Any) -> Any | None:
        """Convert the value to a string for database storage."""
        if value is None:
            return None

        # Filter out empty values
        if isinstance(value, (list, tuple)):
            value = list(filter(lambda x: x, value))

        # Convert to string
        if isinstance(value, (list, tuple)):
            # Convert each item to fully qualified name
            parts = []
            for item in value:
                if isinstance(item, str):
                    # Check if it's a slug
                    if self.field.registry and item in self.field.registry.implementations:
                        impl_class = self.field.registry.get_implementation_class(item)
                        parts.append(get_fully_qualified_name(impl_class))
                    else:
                        parts.append(item)
                elif isinstance(item, type):
                    parts.append(get_fully_qualified_name(item))
                else:
                    # It's an instance
                    parts.append(get_fully_qualified_name(type(item)))
            return ",".join(parts)

        if isinstance(value, str):
            return value

        if not is_running_migrations():
            logger.warning(f"Unexpected type {type(value)} for MultipleRegistryClassField")
        return None


class RegistryFieldDescriptor(RegistryClassFieldDescriptor):
    """Descriptor for fields that return implementation instances."""

    def __get__(self, obj: Model | None, value: type[Model] | None = None) -> Any | None:
        """Retrieve the instance value from the model instance."""
        if obj is None:
            return None

        if self.field.name is None:
            raise RuntimeError("Field name not initialized")
        raw_value = obj.__dict__.get(self.field.name)  # type: ignore[attr-defined]
        if raw_value is None:
            return None

        # If it's already an instance (not a string or class), return it
        if not isinstance(raw_value, (str, type)):
            return raw_value

        # If it's a string or class, we need to instantiate it
        if isinstance(raw_value, str):
            try:
                # First check if it's a slug
                if (
                    hasattr(self.field, "registry")
                    and self.field.registry
                    and raw_value in self.field.registry.implementations
                ):
                    klass = self.field.registry.get_implementation_class(raw_value)
                else:
                    # Try as fully qualified name
                    klass = get_class(raw_value)
            except (ImportError, AttributeError, RegistryNameError, ValueError) as e:
                if not is_running_migrations():
                    logger.warning(
                        f"Failed to convert stored value '{raw_value}' to class for field {self.field.name}: {e}"
                    )
                return None
        else:
            # It's already a class
            klass = raw_value

        # Instantiate the class
        try:
            factory = getattr(self.field, "factory", lambda klass, obj: klass())
            instance = factory(klass, obj)
            # Cache the instance
            obj.__dict__[self.field.name] = instance  # type: ignore[index]
            return instance
        except (TypeError, ValueError):
            if not is_running_migrations():
                logger.exception(f"Failed to instantiate {klass} for field {self.field.name}")
            return None

    def __set__(self, obj: Model, original: str | type | None) -> None:
        """Set the field value by converting a string to an instance or accepting a class directly."""
        if self.field.name is None:
            raise RuntimeError("Field name not initialized")
        if original is None:
            value = None
            raw_value = None
            if not is_running_migrations():
                logger.debug(f"Setting {self.field.name} to None (empty original value)")
        # Handle case where original is already a class
        elif isinstance(original, type):
            value = original
            raw_value = get_fully_qualified_name(original)
            if not is_running_migrations():
                logger.debug(f"Received class {original} for field {self.field.name}")
        else:
            # Handle string case (fully qualified name or slug)
            try:
                # First check if it's a slug
                if (
                    hasattr(self.field, "registry")
                    and self.field.registry
                    and original in self.field.registry.implementations
                ):
                    value = self.field.registry.get_implementation_class(original)
                    raw_value = get_fully_qualified_name(value)
                    if not is_running_migrations():
                        logger.debug(f"Successfully loaded class from slug {original} for field {self.field.name}")
                else:
                    # Try as fully qualified name
                    value = get_class(original)
                    raw_value = get_fully_qualified_name(original)
                    if not is_running_migrations():
                        logger.debug(f"Successfully loaded class {original} for field {self.field.name}")
            except (AttributeError, ModuleNotFoundError, ImportError, RegistryNameError) as e:
                if not is_running_migrations():
                    logger.warning(
                        f"Failed to import class '{original}' for field {self.field.name}: {type(e).__name__}: {e}"
                    )
                if callable(self.field.import_error):
                    value = self.field.import_error(original, e)
                else:
                    value = self.field.import_error
                raw_value = original
            except Exception as e:
                if not is_running_migrations():
                    logger.exception(f"Unexpected error importing class '{original}' for field {self.field.name}")
                raise ValidationError(f"Unable to import '{original}': {type(e).__name__}: {e!s}") from e

        # Instantiate the class if needed
        if isclass(value):
            try:
                factory = getattr(self.field, "factory", lambda klass, obj: klass())
                value = factory(value, obj)
                if not is_running_migrations():
                    logger.debug(f"Successfully instantiated {original} for field {self.field.name}")
            except Exception as e:
                if not is_running_migrations():
                    logger.exception(f"Failed to instantiate {original} for field {self.field.name}")
                raise ValidationError(f"Unable to instantiate '{original}': {type(e).__name__}: {e!s}") from e

        obj.__dict__[self.field.name] = value  # type: ignore[index]
        obj.__dict__[f"_registry_fully_qualified_name_{self.field.name}"] = raw_value  # type: ignore[index]


class MultipleRegistryFieldDescriptor(MultipleRegistryClassFieldDescriptor):
    """Descriptor for fields that return multiple implementation instances."""

    def __get__(self, obj: Model | None, __: type[ModelBase] | None = None) -> list[Any] | None:
        """Retrieve the list of instances from the model instance."""
        if obj is None:
            return None

        if self.field.name is None:
            raise RuntimeError("Field name not initialized")
        values = obj.__dict__.get(self.field.name)  # type: ignore[attr-defined]
        if not values:
            return []

        # Handle case where values are already instances - must be actual implementation instances
        if (
            isinstance(values, list)
            and len(values) > 0
            and all(not isinstance(v, (str, type, list)) and hasattr(v, "slug") for v in values)
        ):
            # Already instantiated as proper implementation instances
            return values

        # Handle different input types
        normalized = []
        if isinstance(values, str):
            normalized = [value.strip() for value in values.split(",") if value.strip()]
        elif isinstance(values, list) and all(isinstance(v, type) for v in values):
            # List of classes
            normalized = values
        elif not isinstance(values, (list, tuple)):
            if not is_running_migrations():
                logger.warning(f"Unexpected type {type(values)} for field {self.field.name}")
            return []
        else:
            normalized = list(values)

        ret = []
        errors = []

        for value in normalized:
            if not value:
                continue

            try:
                # If value is already a class, use it directly
                if isinstance(value, type):
                    cleaned = value
                # Check if it's a slug first
                elif (
                    hasattr(self.field, "registry")
                    and self.field.registry
                    and value in self.field.registry.implementations
                ):
                    cleaned = self.field.registry.get_implementation_class(value)
                else:
                    cleaned = get_class(value)

                # Instantiate the class
                factory = getattr(self.field, "factory", lambda klass, obj: klass())
                instance = factory(cleaned, obj)
                ret.append(instance)
                if not is_running_migrations():
                    logger.debug(f"Successfully loaded and instantiated {value} for field {self.field.name}")
            except (AttributeError, ModuleNotFoundError, ImportError, RegistryNameError) as e:
                if not is_running_migrations():
                    logger.warning(
                        f"Failed to import class '{value}' for field {self.field.name}: {type(e).__name__}: {e}"
                    )
                errors.append((value, e))
            except Exception as e:
                if not is_running_migrations():
                    logger.exception(f"Failed to process '{value}' for field {self.field.name}")
                raise ValidationError(f"Unable to process '{value}': {type(e).__name__}: {e!s}") from e

        # Handle import errors if any occurred
        if errors and self.field.import_error is not None:
            if callable(self.field.import_error):
                # Return the error handler result instead of partial results
                result = self.field.import_error([value for value, _ in errors], errors[0][1])
                return result if isinstance(result, list) else []
            return self.field.import_error if isinstance(self.field.import_error, list) else []

        # Cache the instances
        if ret:
            obj.__dict__[self.field.name] = ret  # type: ignore[index]

        return ret

    def __set__(self, obj: Model, original: Any) -> None:
        """Store the raw value in the model instance."""
        if self.field.name is None:
            raise RuntimeError("Field name not initialized")
        # Convert classes/instances to fully qualified names for storage
        value = original
        if value is not None:
            if isinstance(value, list):
                # Convert list items to fully qualified names
                normalized = []
                for item in value:
                    if isinstance(item, type):
                        normalized.append(get_fully_qualified_name(item))
                    elif isinstance(item, str):
                        normalized.append(item)
                    else:
                        # It's an instance, get its class name
                        normalized.append(get_fully_qualified_name(type(item)))
                value = ",".join(normalized)
            elif isinstance(value, type):
                # Single class to fully qualified name
                value = get_fully_qualified_name(value)
            elif not isinstance(value, str):
                # It's an instance, get its class name
                value = get_fully_qualified_name(type(value))

        obj.__dict__[self.field.name] = value  # type: ignore[index]


class AbstractRegistryField(Field):
    """Base class for all registry fields."""

    descriptor: type[ImplementationDescriptor]
    registry: type[Registry] | None = None
    form_class: type[forms.Field] | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.import_error = kwargs.pop("import_error", None)
        kwargs["max_length"] = kwargs.get("max_length", 200)
        self.registry = kwargs.pop("registry", None)

        if self.registry is not None and not (isinstance(self.registry, type) and issubclass(self.registry, Registry)):
            raise ValueError(f"'registry' must be a Registry subclass, got {self.registry!r}")

        super().__init__(*args, **kwargs)

        # Add validators if not already present (prevent duplication when reconstructed from deconstruct or cloned)
        if not any(isinstance(v, ClassnameValidator) for v in self._validators):  # type: ignore[union-attr]
            self._validators.append(ClassnameValidator(None))  # type: ignore[union-attr]
        if self.registry and not any(isinstance(v, RegistryValidator) for v in self._validators):  # type: ignore[union-attr]
            self._validators.append(RegistryValidator(self.registry))  # type: ignore[union-attr]

        if not is_running_migrations():
            logger.debug(f"Initialized {self.__class__.__name__} with registry: {self.registry}")

    @property
    def flatchoices(self) -> list[tuple[str, str]]:
        return []

    def contribute_to_class(self, cls: type[Model], name: str, private_only: bool = False) -> None:
        self.set_attributes_from_name(name)
        self.model = cls

        # Skip expensive registry operations during migrations
        if not is_running_migrations():
            # Resolve registry if needed
            if self.registry is not None:
                # Check if registry was inadvertently converted to a tuple/list
                if isinstance(self.registry, (tuple, list)):
                    logger.error(
                        f"Registry for field {name} was converted to {type(self.registry)}. "
                        "This usually happens when Django iterates over the registry class."
                    )
                    # Try to recover by finding the registry class
                    from .registry import django_stratagem_registry

                    for reg_cls in django_stratagem_registry:
                        # Check if the converted data matches this registry's implementations
                        if list(reg_cls.implementations.values()) == list(self.registry):
                            self.registry = reg_cls
                            logger.info(f"Recovered registry {reg_cls.__name__} for field {name}")
                            break
                    else:
                        raise ValueError(
                            f"Could not recover registry for field {name}. "
                            "The registry was converted to a sequence and the original class could not be found."
                        )

                # First check if it's already a Registry class
                if isinstance(self.registry, type) and issubclass(self.registry, Registry):
                    logger.debug(f"Registry {self.registry.__name__} is already a Registry class for field {name}")
                elif callable(self.registry):
                    original_registry = self.registry
                    try:
                        try:
                            self.registry = self.registry(cls)
                            logger.debug(f"Registry resolved with model class for field {name}")
                        except TypeError:
                            try:
                                self.registry = self.registry()
                                logger.debug(f"Registry resolved without arguments for field {name}")
                            except Exception:
                                self.registry = original_registry
                                logger.error(f"Failed to resolve callable registry for field {name}")
                                raise
                    except Exception as e:
                        logger.exception(f"Error resolving registry for field {name}")
                        raise ValueError(f"Unable to resolve registry for field {name}: {e}") from e

        cls._meta.add_field(self)  # type: ignore[attr-defined]
        if self.name is None:
            raise RuntimeError("Field name not initialized")
        setattr(cls, self.name, self.descriptor(self))

    def deconstruct(self) -> tuple[str, str, list[Any], dict[str, Any]]:
        name, path, args, kwargs = super().deconstruct()

        # Remove default values
        if "max_length" in kwargs and kwargs["max_length"] == 200:
            del kwargs["max_length"]

        # Preserve registry
        if self.registry is not None:
            kwargs["registry"] = self.registry

        # Remove choices as they're dynamically generated
        if "choices" in kwargs:
            del kwargs["choices"]

        # Strip auto-added validators to prevent duplication in deconstruct/reconstruct (clone, makemigrations, etc.)
        if "validators" in kwargs:
            kwargs["validators"] = [
                v
                for v in kwargs["validators"]
                if not isinstance(v, (ClassnameValidator, RegistryValidator))
            ]
            if not kwargs["validators"]:
                del kwargs["validators"]

        return name, path, args, kwargs  # type: ignore[return-value]

    def from_db_value(self, value, expression, connection):
        """Convert database value to Python value."""
        if value is None:
            return None
        return value

    def to_python(self, value):
        """Convert value to correct Python type."""
        if value is None:
            return None
        if isinstance(value, type):
            return value
        if not isinstance(value, str):
            try:
                value = get_fully_qualified_name(value)
            except (ImportError, AttributeError, TypeError, ValueError):
                return value
        return value

    def get_prep_value(self, value: Any) -> Any | None:
        if value is None:
            return None

        try:
            if isinstance(value, str):
                if self.registry and value in self.registry.implementations:
                    impl_class = self.registry.get_implementation_class(value)
                    return get_fully_qualified_name(impl_class)
                return value
            if isinstance(value, type):
                return get_fully_qualified_name(value)
            return get_fully_qualified_name(type(value))
        except (ImportError, AttributeError, TypeError, ValueError) as e:
            if not is_running_migrations():
                logger.error(f"Failed to get fully qualified name for {value}: {e}")
            if isinstance(value, str):
                return value
            return None

    def value_to_string(self, obj: Model) -> str:
        value = self.value_from_object(obj)
        if value is None:
            return ""
        try:
            return get_fully_qualified_name(value)
        except (ImportError, AttributeError, TypeError, ValueError) as e:
            if not is_running_migrations():
                logger.error(f"Failed to serialize value {value} for field {self.name}: {e}")
            return ""

    def get_internal_type(self) -> str:
        return "CharField"

    def _get_choices(self) -> list[tuple[str, str]]:
        if is_running_migrations():
            return []
        if self.registry:
            try:
                if isinstance(self.registry, type) and issubclass(self.registry, Registry):
                    return self.registry.get_choices()
                logger.error(f"Registry is not a valid Registry class: {type(self.registry)} - {self.registry!r}")
                return []
            except (ImportError, AttributeError, ValueError) as e:
                logger.error(f"Failed to get choices from registry: {e}")
                return []
        return []

    def _set_choices(self, value: tuple) -> None:
        pass

    choices = property(_get_choices, _set_choices)  # type: ignore[assignment]

    def get_choices(
        self,
        include_blank: bool = True,
        blank_choice: list[tuple[str, str]] = BLANK_CHOICE_DASH,
        limit_choices_to: dict[str, Any] | None = None,
        ordering: Sequence[str] = (),
    ) -> Any:
        first_choice = blank_choice if include_blank else []
        return first_choice + self._get_choices()

    def formfield(self, form_class: Any = None, choices_form_class: Any = None, **kwargs: Any) -> forms.Field | None:
        from .forms import RegistryFormField, RegistryMultipleChoiceFormField
        from .widgets import RegistryDescriptionWidget

        show_description = kwargs.pop("show_description", False)

        defaults = {
            "required": not self.blank,
            "label": capfirst(self.verbose_name),
            "help_text": self.help_text,
            "registry": self.registry,
        }

        if self.has_default():
            if callable(self.default):
                defaults["initial"] = self.default
                defaults["show_hidden_initial"] = True
            else:
                defaults["initial"] = self.get_default()

        include_blank = self.blank or not (self.has_default() or "initial" in kwargs)
        defaults["choices"] = self.get_choices(include_blank=include_blank)

        if self.null:
            defaults["empty_value"] = None

        if show_description and "widget" not in kwargs:
            kwargs["widget"] = RegistryDescriptionWidget(
                registry=self.registry,
                choices=defaults.get("choices", []),
            )

        form_class = form_class or self.form_class
        if form_class is None:
            if isinstance(self, (MultipleRegistryClassField, MultipleRegistryField)):
                form_class = RegistryMultipleChoiceFormField
            else:
                form_class = RegistryFormField

        valid_kwargs = {
            "choices",
            "context",
            "empty_value",
            "error_messages",
            "form_class",
            "help_text",
            "initial",
            "label",
            "parent_field",
            "registry",
            "required",
            "show_hidden_initial",
            "widget",
        }
        for k in list(kwargs):
            if k not in valid_kwargs:
                del kwargs[k]

        defaults.update(kwargs)
        return form_class(**defaults)


class RegistryClassField(AbstractRegistryField):
    """Field that stores a reference to an implementation class."""

    descriptor = RegistryClassFieldDescriptor

    def validate(self, value: Any, model_instance: Model | None) -> None:
        if not value:
            return

        if self.registry:
            if isinstance(value, type):
                check_value = value
            elif isinstance(value, str):
                if value in self.registry.implementations:
                    return
                try:
                    check_value = get_class(value)
                except (ImportError, AttributeError, ValueError):
                    if not is_running_migrations():
                        logger.warning(f"Validation failed: {value} not in registry for field {self.name}")
                    raise ValidationError(f"{value} is not a valid choice")
            else:
                check_value = type(value)

            is_valid = False
            for slug in self.registry.implementations:
                if self.registry.get_implementation_class(slug) == check_value:
                    is_valid = True
                    break

            if not is_valid:
                if not is_running_migrations():
                    logger.warning(f"Validation failed: {value} not in registry for field {self.name}")
                raise ValidationError(f"{value} is not a valid choice")


class MultipleRegistryClassField(AbstractRegistryField):
    """Field that stores references to multiple implementation classes."""

    descriptor = MultipleRegistryClassFieldDescriptor

    def validate(self, value: Any, model_instance: Model | None) -> None:
        if not value:
            return

        normalized = []
        if not isinstance(value, (list, tuple)):
            normalized = [value]
        else:
            normalized = list(value)

        if self.registry:
            invalid_values = []
            for v in normalized:
                is_valid = False
                for slug in self.registry.implementations:
                    if self.registry.get_implementation_class(slug) == v:
                        is_valid = True
                        break

                if not is_valid:
                    invalid_values.append(str(v))

            if invalid_values:
                if not is_running_migrations():
                    logger.warning(f"Validation failed for field {self.name}: {invalid_values} not in registry")
                raise ValidationError(f"The following are not valid choices: {', '.join(invalid_values)}")

    def get_db_prep_save(self, value: Any, connection: BaseDatabaseWrapper) -> Any:
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            value = list(filter(lambda x: x, value))
        return self.get_prep_value(value)

    def get_prep_value(self, value: Any) -> Any | None:
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return stringify(value)
        if isinstance(value, str):
            return value
        if not is_running_migrations():
            logger.warning(f"Unexpected type {type(value)} for MultipleRegistryClassField")
        return None

    def get_lookup(self, lookup_name: str) -> type[Lookup] | None:
        return super().get_lookup(lookup_name)


class RegistryField(RegistryClassField):
    """Field that stores a reference to an implementation instance."""

    descriptor = RegistryFieldDescriptor

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.factory = kwargs.pop("factory", lambda klass, obj: klass())
        super().__init__(*args, **kwargs)
        if not is_running_migrations():
            logger.debug(f"Initialized RegistryField with factory: {self.factory}")

    def pre_save(self, model_instance: Model, add: bool) -> str | None:
        if self.attname is None:
            raise RuntimeError("Field attname not initialized")
        value = getattr(model_instance, self.attname, None)
        if value:
            try:
                return get_fully_qualified_name(value)
            except (ImportError, AttributeError, TypeError, ValueError) as e:
                if not is_running_migrations():
                    logger.error(f"Failed to get fully qualified name in pre_save: {e}")
                return None
        return None


class MultipleRegistryField(MultipleRegistryClassField):
    """Field that stores references to multiple implementation instances."""

    descriptor = MultipleRegistryFieldDescriptor

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.factory = kwargs.pop("factory", lambda klass, obj: klass())
        super().__init__(*args, **kwargs)
        if not is_running_migrations():
            logger.debug(f"Initialized MultipleRegistryField with factory: {self.factory}")


class HierarchicalRegistryField(RegistryField):
    """Registry field that depends on a parent registry field selection."""

    def __init__(self, *args: Any, parent_field: str | None = None, **kwargs: Any) -> None:
        self.parent_field = parent_field
        self._parent_field_name = parent_field
        super().__init__(*args, **kwargs)

        if self.registry and not hasattr(self.registry, "get_children_for_parent"):
            if not is_running_migrations():
                logger.warning(
                    "Registry %s should inherit from HierarchicalRegistry for field %s",
                    self.registry,
                    self.name if hasattr(self, "name") else "unnamed",
                )

    def contribute_to_class(self, cls: type[Model], name: str, private_only: bool = False) -> None:
        super().contribute_to_class(cls, name, private_only)
        self._parent_field_name = self.parent_field

    def get_parent_value(self, obj: Model | None) -> str | None:
        if not obj or not self._parent_field_name:
            return None
        try:
            parent_value = getattr(obj, self._parent_field_name)
            if parent_value:
                return get_fully_qualified_name(parent_value)
        except AttributeError:
            if not is_running_migrations():
                logger.warning(
                    "Parent field '%s' not found on model %s", self._parent_field_name, obj.__class__.__name__
                )
        return None

    def validate(self, value: Any, model_instance: Model | None) -> None:
        super().validate(value, model_instance)

        if not value or not self._parent_field_name or not model_instance:
            return

        parent_value = self.get_parent_value(model_instance)
        if not parent_value:
            return

        parent_slug = None
        if (
            self.registry is not None
            and isinstance(self.registry, type)
            and issubclass(self.registry, HierarchicalRegistry)
        ):
            parent_registry = self.registry.parent_registry
            if parent_registry is not None:
                for p_slug in parent_registry.implementations:
                    parent_impl = parent_registry.get_implementation_class(p_slug)
                    if get_fully_qualified_name(parent_impl) == parent_value:
                        parent_slug = p_slug
                        break

            if parent_slug:
                child_slug = None
                for c_slug in self.registry.implementations:
                    if self.registry.get_implementation_class(c_slug) == value:
                        child_slug = c_slug
                        break

                if child_slug and not self.registry.validate_parent_child_relationship(parent_slug, child_slug):
                    raise ValidationError(f"{value} is not valid for parent selection {parent_slug}")

    def formfield(self, form_class: Any = None, choices_form_class: Any = None, **kwargs: Any) -> forms.Field | None:
        from .forms import HierarchicalRegistryFormField

        kwargs["parent_field"] = self._parent_field_name
        return super().formfield(form_class=form_class or HierarchicalRegistryFormField, **kwargs)


class MultipleHierarchicalRegistryField(MultipleRegistryField):
    """Multiple selection field with parent dependency."""

    def __init__(self, *args: Any, parent_field: str | None = None, **kwargs: Any) -> None:
        self.parent_field = parent_field
        self._parent_field_name = parent_field
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls: type[Model], name: str, private_only: bool = False) -> None:
        super().contribute_to_class(cls, name, private_only)
        self._parent_field_name = self.parent_field

    def get_parent_value(self, obj: Model | None) -> str | None:
        if not obj or not self._parent_field_name:
            return None
        try:
            parent_value = getattr(obj, self._parent_field_name)
            if parent_value:
                return get_fully_qualified_name(parent_value)
        except AttributeError:
            if not is_running_migrations():
                logger.warning(
                    "Parent field '%s' not found on model %s", self._parent_field_name, obj.__class__.__name__
                )
        return None

    def validate(self, value: Any, model_instance: Model | None) -> None:
        super().validate(value, model_instance)

        if not value or not self._parent_field_name or not model_instance:
            return

        parent_value = self.get_parent_value(model_instance)
        if not parent_value:
            return

        parent_slug = None
        if (
            self.registry is not None
            and isinstance(self.registry, type)
            and issubclass(self.registry, HierarchicalRegistry)
        ):
            parent_registry = self.registry.parent_registry
            if parent_registry is not None:
                for p_slug in parent_registry.implementations:
                    parent_impl = parent_registry.get_implementation_class(p_slug)
                    if get_fully_qualified_name(parent_impl) == parent_value:
                        parent_slug = p_slug
                        break

        if parent_slug and self.registry is not None:
            invalid_values = []
            for v in value if isinstance(value, (list, tuple)) else [value]:
                child_slug = None
                for c_slug in self.registry.implementations:
                    if self.registry.get_implementation_class(c_slug) == v:
                        child_slug = c_slug
                        break

                if (
                    child_slug
                    and isinstance(self.registry, type)
                    and issubclass(self.registry, HierarchicalRegistry)
                    and not self.registry.validate_parent_child_relationship(parent_slug, child_slug)
                ):
                    invalid_values.append(str(v))

            if invalid_values:
                raise ValidationError(
                    f"The following are not valid for parent {parent_slug}: {', '.join(invalid_values)}"
                )


class HierarchicalRegistryFieldDescriptor(RegistryFieldDescriptor):
    """Descriptor that validates parent-child relationships on set."""

    field: HierarchicalRegistryField

    def __init__(self, field: HierarchicalRegistryField) -> None:
        super().__init__(field)

    def __set__(self, obj: Model, original: str | type | None) -> None:
        super().__set__(obj, original)

        if self.field._parent_field_name:
            try:
                if self.field.name is None:
                    raise RuntimeError("Field name not initialized")
                self.field.validate(obj.__dict__.get(self.field.name), obj)  # type: ignore[index]
            except ValidationError:
                if self.field.name is None:
                    raise RuntimeError("Field name not initialized")
                obj.__dict__[self.field.name] = None  # type: ignore[index]
                raise


HierarchicalRegistryField.descriptor = HierarchicalRegistryFieldDescriptor  # type: ignore[assignment]

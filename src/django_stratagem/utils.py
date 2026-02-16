from __future__ import annotations

import importlib
import logging
import re
import sys
import types
from collections.abc import Sequence
from functools import lru_cache
from inspect import isclass
from typing import TYPE_CHECKING, Any

from .exceptions import RegistryAttributeError, RegistryClassError, RegistryNameError

if TYPE_CHECKING:
    from django.db.models import Model


logger = logging.getLogger(__name__)

_migrations_running: bool | None = None


def is_running_migrations() -> bool:
    """Check if Django is currently running migrations."""
    global _migrations_running
    if _migrations_running is None:
        _migrations_running = "migrate" in sys.argv or "makemigrations" in sys.argv
    return _migrations_running


def camel_to_title(text):
    """Convert camel case string to title case.

    Handles consecutive capitals correctly: 'HTTPServer' → 'HTTP Server'.
    """
    # Insert space before a capital letter that is followed by a lowercase letter
    # and preceded by another capital (handles HTTPServer → HTTP Server)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    # Insert space before a capital letter preceded by a lowercase letter
    text = re.sub(r"([a-z\d])([A-Z])", r"\1 \2", text)
    # Capitalize first letter of each word without lowercasing the rest
    return " ".join(word[0].upper() + word[1:] if word else "" for word in text.split(" ")).strip()


@lru_cache(maxsize=256)
def import_by_name(name: str) -> Any:
    """Dynamically load and cache a class by its full path."""
    if "." not in name:
        raise RegistryNameError(name)

    module_path, class_str = name.rsplit(".", 1)
    module = importlib.import_module(module_path)

    try:
        return getattr(module, class_str)
    except AttributeError:
        raise RegistryAttributeError(name, module_path, class_str)


def store_raw_name(obj: Model, field_name: str, original: str | None) -> None:
    """Store the fully qualified name or None after import attempt."""
    try:
        raw = get_fully_qualified_name(original or "")
    except RegistryClassError:
        raw = None
    vars(obj)[f"_registry_fully_qualified_name_{field_name}"] = raw


def get_class(value: str | type | None) -> Any:
    """Get a class from a string reference or return the class itself."""
    if not value:
        return None
    if isinstance(value, str):
        return import_by_name(value)
    if isclass(value):
        return value

    value_type = type(value)
    if value_type.__module__ in ("builtins", "__builtin__"):
        return None
    return value_type


def get_display_string(klass: type, display_attribute: str | None = None) -> str:
    """Get display string for a class, using a specific attribute if provided."""
    if display_attribute and hasattr(klass, display_attribute):
        attr = getattr(klass, display_attribute)
        if attr is None:
            return get_fully_qualified_name(klass)
        if callable(attr):
            return str(attr())
        return str(attr)

    # Default to class name
    return camel_to_title(klass.__name__)


def get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Recursively get object's attribute. May use dot notation."""
    if "." not in attr:
        return getattr(obj, attr, default)
    parts = attr.split(".")
    return get_attr(getattr(obj, parts[0], default), ".".join(parts[1:]), default)


def get_fully_qualified_name(obj: Any) -> str:
    """Returns the fully qualified class name of an object or a class."""
    parts = []
    if isinstance(obj, str):
        return obj
    if not hasattr(obj, "__module__"):
        raise RegistryClassError(obj)
    parts.append(obj.__module__)
    if isclass(obj) or isinstance(obj, types.FunctionType):
        parts.append(obj.__name__)
    else:
        parts.append(obj.__class__.__name__)
    return ".".join(parts)


def stringify(values: Sequence[Any]) -> str:
    """Convert a sequence of values to a comma-separated string."""
    output = []
    for value in values:
        if isinstance(value, str) and value:
            output.append(value)
        else:
            output.append(get_fully_qualified_name(value))
    return ",".join(sorted(output))

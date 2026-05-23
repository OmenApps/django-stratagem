"""Test helpers for projects that depend on django-stratagem registries.

These context managers snapshot and restore the global, mutable registry
state so tests stay isolated without hand-written setup/teardown.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .registry import Registry


@contextmanager
def temporary_implementation(registry: type[Registry], implementation: type[Any]) -> Iterator[type[Any]]:
    """Register ``implementation`` in ``registry`` for the duration of the block.

    The registry's implementation map is snapshotted on enter and fully
    restored on exit (even if the block raises), so registrations made inside
    the block never leak into other tests.
    """
    original = dict(registry.implementations)
    registry.register(implementation)
    try:
        yield implementation
    finally:
        registry.implementations.clear()
        registry.implementations.update(original)
        registry.clear_cache()


_MISSING = object()


@contextmanager
def override_availability(implementation: type[Any], *, available: bool = True) -> Iterator[type[Any]]:
    """Force ``implementation.is_available`` to return ``available`` in the block.

    Restores the implementation's own ``is_available`` (or removes the
    override, falling back to the inherited method) on exit.
    """
    original = implementation.__dict__.get("is_available", _MISSING)
    implementation.is_available = classmethod(lambda cls, context=None: available)
    try:
        yield implementation
    finally:
        if original is _MISSING:
            del implementation.is_available
        else:
            implementation.is_available = original

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

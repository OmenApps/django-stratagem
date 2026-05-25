"""Test helpers for projects that depend on django-stratagem registries.

These context managers snapshot and restore the global, mutable registry
state so tests stay isolated without hand-written setup/teardown.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator, Sequence
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
    # Capture the class's OWN is_available (not an inherited one) so teardown can
    # tell "had its own method" from "inherited it". The lambda closes over the
    # fixed `available` value; classmethod() makes it a valid class attribute.
    original = implementation.__dict__.get("is_available", _MISSING)
    implementation.is_available = classmethod(lambda cls, context=None: available)
    try:
        yield implementation
    finally:
        if original is _MISSING:
            del implementation.is_available
        else:
            implementation.is_available = original


@contextmanager
def isolate_registries() -> Iterator[None]:
    """Snapshot all registry state on enter and restore it on exit.

    Restores the global registry list, each registry's implementations map,
    and the hierarchical parent/child relationships. Use this to wrap a test
    (or a fixture) that defines or mutates registries so nothing leaks.
    """
    from .registry import RegistryRelationship, django_stratagem_registry

    original_list = list(django_stratagem_registry)
    original_relationships = copy.deepcopy(RegistryRelationship._relationships)
    original_implementations = {
        registry: dict(registry.implementations)
        for registry in django_stratagem_registry
        if hasattr(registry, "implementations")
    }
    try:
        yield
    finally:
        django_stratagem_registry.clear()
        django_stratagem_registry.extend(original_list)
        RegistryRelationship._relationships.clear()
        RegistryRelationship._relationships.update(original_relationships)
        for registry, impls in original_implementations.items():
            registry.implementations.clear()
            registry.implementations.update(impls)
            registry.clear_cache()


def assert_registered(registry: type[Registry], slug: str) -> None:
    """Assert ``slug`` is registered in ``registry``."""
    if slug not in registry.implementations:
        registered = ", ".join(sorted(registry.implementations)) or "(none)"
        raise AssertionError(
            f"Expected slug '{slug}' to be registered in {registry.__name__}. Registered: {registered}."
        )


def assert_not_registered(registry: type[Registry], slug: str) -> None:
    """Assert ``slug`` is not registered in ``registry``."""
    if slug in registry.implementations:
        raise AssertionError(f"Expected slug '{slug}' NOT to be registered in {registry.__name__}, but it is.")


def assert_available(implementation: type[Any], context: dict[str, Any] | None = None) -> None:
    """Assert ``implementation.is_available(context)`` is truthy (or has no condition)."""
    is_available = getattr(implementation, "is_available", None)
    available = bool(is_available(context)) if callable(is_available) else True
    if not available:
        raise AssertionError(f"Expected {implementation.__name__} to be available for context {context!r}.")


def assert_not_available(implementation: type[Any], context: dict[str, Any] | None = None) -> None:
    """Assert ``implementation.is_available(context)`` is falsy."""
    is_available = getattr(implementation, "is_available", None)
    available = bool(is_available(context)) if callable(is_available) else True
    if available:
        raise AssertionError(f"Expected {implementation.__name__} to be unavailable for context {context!r}.")


def assert_choices(registry: type[Registry], expected_slugs: Sequence[str]) -> None:
    """Assert the registry's choice slugs equal ``expected_slugs`` in order."""
    actual = [slug for slug, _label in registry.get_choices()]
    if actual != list(expected_slugs):
        raise AssertionError(f"Expected choice slugs {list(expected_slugs)!r} but got {actual!r}.")

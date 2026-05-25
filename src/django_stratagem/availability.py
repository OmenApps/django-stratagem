"""Shared resolution of an implementation's availability and human reason.

Used by both the registry inspector and ``Registry.explain_availability`` so
the "which reason wins" logic lives in exactly one place.
"""

from __future__ import annotations

from typing import Any


def evaluate_availability(impl_class: type[Any] | None, context: dict[str, Any] | None) -> tuple[bool, str]:
    """Return ``(available, reason)`` for an implementation class.

    Prefers ``explain_availability`` for a rich reason, except when the class
    overrides only the sync ``is_available`` (then that override is
    authoritative, matching ``get_available_implementations``). Falls back to
    ``is_available``, then to always-available.
    """
    if impl_class is None:
        return False, "No implementation class"

    own = getattr(impl_class, "__dict__", {})
    overrides_sync_only = "is_available" in own and "explain_availability" not in own

    explain = getattr(impl_class, "explain_availability", None)
    if callable(explain) and not overrides_sync_only:
        available, reason = explain(context)
        return bool(available), reason

    is_available = getattr(impl_class, "is_available", None)
    if callable(is_available):
        available = bool(is_available(context))
        return available, "Available" if available else "Unavailable"

    return True, "Always available"

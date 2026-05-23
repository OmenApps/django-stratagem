"""Read-only introspection helpers for the registry inspector UI."""

from __future__ import annotations

import logging
from typing import Any

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest
from django.template.response import TemplateResponse

from .registry import django_stratagem_registry

logger = logging.getLogger(__name__)

#: Namespaced URL name for the registry inspector view. Use it with
#: ``reverse()`` or ``{% url %}`` to link to the inspector without hardcoding
#: the string, avoiding a fragile app-level ``admin/index.html`` template.
INSPECTOR_URL_NAME = "django_stratagem:registry-inspector"


def build_inspector_rows(context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Build JSON-able rows describing every registry and its implementations.

    Each implementation row includes its availability and a human-readable
    reason. Availability is computed via ``explain_availability`` when present
    (rich reason from the condition), then ``is_available`` (so implementations
    that override it directly are reported accurately), then defaults to always
    available. A failing implementation is logged and reported as unavailable
    rather than crashing the page.
    """
    context = context or {}
    rows: list[dict[str, Any]] = []

    for registry in django_stratagem_registry:
        implementations = []
        sorted_items = sorted(
            registry.implementations.items(),
            key=lambda item: item[1].get("priority", 0),
        )
        for slug, meta in sorted_items:
            impl_class = meta["klass"]

            # Name resolution is independent of availability; a display-name
            # failure must not be misreported as an availability failure.
            try:
                name = registry.get_display_name(impl_class) if impl_class else slug
            except Exception:  # noqa: BLE001 - inspector must not crash on a flaky implementation
                logger.exception("Inspector failed to resolve display name for %s in %s", slug, registry.__name__)
                name = slug

            try:
                # ``is_available`` is the authoritative gate (it is what the
                # registry uses to filter implementations), so it determines
                # availability. ``explain_availability`` only supplies a richer
                # reason, and only when it agrees with the gate.
                is_available = getattr(impl_class, "is_available", None)
                available = bool(is_available(context)) if callable(is_available) else True

                explain = getattr(impl_class, "explain_availability", None)
                if callable(explain):
                    explained_available, explained_reason = explain(context)
                    if explained_available == available:
                        reason = explained_reason
                    else:
                        reason = "Available" if available else "Unavailable"
                else:
                    reason = "Always available" if available else "Unavailable"
            except Exception:  # noqa: BLE001 - inspector must not crash on a flaky implementation
                logger.exception("Inspector failed to evaluate availability for %s in %s", slug, registry.__name__)
                # Keep the raw exception text out of the response to avoid leaking
                # sensitive detail; the full traceback is in the server logs.
                available, reason = False, "Error evaluating availability (see server logs)"

            implementations.append(
                {
                    "slug": slug,
                    "name": name,
                    "description": meta.get("description", ""),
                    "icon": meta.get("icon", ""),
                    "priority": meta.get("priority", 0),
                    "available": available,
                    "reason": reason,
                }
            )

        rows.append(
            {
                "registry": registry.__name__,
                "module": registry.__module__,
                "doc": (registry.__doc__ or "").strip().split("\n")[0],
                "implementations": implementations,
            }
        )

    return rows


@staff_member_required
def registry_inspector(request: HttpRequest) -> TemplateResponse:
    """Render the read-only registry inspector page for staff users."""
    context = {"request": request, "user": getattr(request, "user", None)}
    return TemplateResponse(
        request,
        "django_stratagem/inspector.html",
        {"title": "Registry Inspector", "rows": build_inspector_rows(context)},
    )

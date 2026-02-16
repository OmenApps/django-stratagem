from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.http import JsonResponse
from django.views.generic import View

from ..registry import HierarchicalRegistry, django_stratagem_registry
from ..utils import get_class

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from django.http import HttpRequest


class RegistryChoicesAPIView(View):
    """API endpoint for fetching child choices based on parent selection."""

    def get(self, request: HttpRequest) -> JsonResponse:
        """Get choices for a registry, optionally filtered by parent."""
        registry_name = request.GET.get("registry")
        parent_value = request.GET.get("parent")

        if not registry_name:
            return JsonResponse({"error": "Registry name required"}, status=400)

        # Find registry
        registry = None
        for reg in django_stratagem_registry:
            if reg.__name__ == registry_name:
                registry = reg
                break

        if not registry:
            return JsonResponse({"error": "Registry not found"}, status=404)

        # Build context from request
        user = getattr(request, "user", None)
        context = {
            "request": request,
            "user": user if user is not None and getattr(user, "is_authenticated", False) else None,
        }

        # Get choices
        if parent_value and isinstance(parent_value, str) and issubclass(registry, HierarchicalRegistry):
            # Get parent slug
            parent_slug = self._get_parent_slug(registry, parent_value)
            if parent_slug:
                choices = registry.get_choices_for_parent(parent_slug, context)
            else:
                choices = []
        else:
            # Get all choices for context
            choices = registry.get_choices_for_context(context)

        return JsonResponse(
            {
                "choices": choices,
                "registry": registry_name,
                "parent": parent_value,
            }
        )

    def _get_parent_slug(self, child_registry: HierarchicalRegistry, parent_value: str) -> str | None:
        """Extract parent slug from parent value."""
        if not parent_value:
            return None

        # Check if it's already a slug
        parent_registry = child_registry.parent_registry
        if not parent_registry:
            return None

        # If no dots, assume it's a slug
        if "." not in parent_value:
            if parent_value in parent_registry.implementations:
                return parent_value

        # Try to get class and find matching slug
        try:
            parent_class = get_class(parent_value)
            for slug, impl in parent_registry.get_items():
                if impl == parent_class:
                    return slug
        except (ImportError, ValueError, AttributeError):
            logger.debug("Failed to resolve parent slug from '%s'", parent_value)

        return None


class RegistryHierarchyAPIView(View):
    """API endpoint for fetching registry hierarchy information."""

    def get(self, request: HttpRequest) -> JsonResponse:
        """Get hierarchy map for all registries."""
        hierarchy_data = {}

        for registry in django_stratagem_registry:
            if isinstance(registry, type) and issubclass(registry, HierarchicalRegistry):
                hierarchy_map = registry.get_hierarchy_map()
                if hierarchy_map:
                    hierarchy_data[registry.__name__] = {
                        "parent_registry": (registry.parent_registry.__name__ if registry.parent_registry else None),
                        "hierarchy_map": hierarchy_map,
                    }

        return JsonResponse(
            {
                "hierarchies": hierarchy_data,
            }
        )

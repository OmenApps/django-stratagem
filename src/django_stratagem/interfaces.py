import logging
from typing import Any

from .conditions import Condition
from .registry import Registry

logger = logging.getLogger(__name__)


class Interface:
    """Base class to define an implementation interface and auto-register subclasses."""

    slug: str
    registry: "type[Registry[Interface]] | None" = None
    description: str = ""
    icon: str = ""
    priority: int = 0

    def __init_subclass__(cls) -> None:
        """Auto-register valid subclasses with their specified registry."""
        super().__init_subclass__()
        registry_cls = getattr(cls, "registry", None)
        slug = getattr(cls, "slug", None)
        if not registry_cls or not slug:
            logger.info("Skipping registration of %s: missing registry or slug.", cls.__name__)
            return

        if not isinstance(registry_cls, type) or not hasattr(registry_cls, "register"):
            logger.error("Invalid registry '%s' for implementation %s", registry_cls, cls)
            return

        logger.debug("Registering implementation %s in %s", cls.__name__, registry_cls.__name__)
        registry_cls.register(cls)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} slug={getattr(self, 'slug', None)!r}>"


class HierarchicalInterface(Interface):
    """Interface that can specify parent requirements."""

    # Parent implementation slug this child requires
    parent_slug: str | None = None

    # Multiple parents this child can work with
    parent_slugs: list[str] | None = None

    @classmethod
    def is_valid_for_parent(cls, parent_slug: str) -> bool:
        """Check if this implementation is valid for a given parent."""
        if cls.parent_slug:
            return parent_slug == cls.parent_slug

        if cls.parent_slugs:
            return parent_slug in cls.parent_slugs

        # No parent restrictions
        return True


class ConditionalInterface(Interface):
    """Interface with conditional availability."""

    # Condition for this implementation to be available
    condition: Condition | None = None

    @classmethod
    def is_available(cls, context: dict[str, Any] | None = None) -> bool:
        """Check if this implementation is available in the given context."""
        if not cls.condition:
            return True

        if context is None:
            context = {}

        return cls.condition.is_met(context)

    @classmethod
    def explain_availability(cls, context: dict[str, Any] | None = None) -> tuple[bool, str]:
        """Return ``(is_available, human_readable_reason)`` for the given context.

        Reuses ``Condition.check_with_details`` so the reason describes which
        sub-conditions passed or failed. Intended for the registry inspector
        and debugging tools.
        """
        if not cls.condition:
            return True, "No condition set; always available"
        if context is None:
            context = {}
        return cls.condition.check_with_details(context)

    @classmethod
    async def ais_available(cls, context: dict[str, Any] | None = None) -> bool:
        """Check if this implementation is available in the given context (async variant).

        Delegates to the condition's ``acheck`` so a condition that overrides
        ``acheck`` is evaluated natively rather than in a thread.
        """
        if not cls.condition:
            return True
        if context is None:
            context = {}
        return await cls.condition.acheck(context)

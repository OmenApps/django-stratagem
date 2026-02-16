from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, Generic, TypedDict, TypeVar, cast, overload

from django.core.cache import cache
from django.db.models import Model
from django.utils import timezone
from django.utils.module_loading import autodiscover_modules

from .app_settings import get_cache_timeout
from .exceptions import ImplementationNotFound
from .signals import implementation_registered, implementation_unregistered, registry_reloaded
from .utils import get_class, get_display_string, import_by_name, is_running_migrations

if TYPE_CHECKING:
    from .fields import AbstractRegistryField
    from .interfaces import Interface

logger = logging.getLogger(__name__)

# Global registry index
django_stratagem_registry: list[type[Registry]] = []

TInterface = TypeVar("TInterface", bound="Interface")
TRegistry = TypeVar("TRegistry", bound="Registry")


def skip_during_migrations(func):
    """Decorator to skip method execution during migrations."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_running_migrations():
            # Return empty/default values for common registry methods
            method_name = func.__name__
            if method_name == "get_choices":
                return []
            if method_name == "discover_implementations":
                return None
            if method_name == "get_items":
                return []
            if method_name == "get_available_implementations":
                return {}
            if method_name == "check_health":
                return {"count": 0, "last_updated": None}
            # For other methods, just skip execution
            return None
        return func(*args, **kwargs)

    return wrapper


class ImplementationMeta(TypedDict):
    """Type definition for implementation metadata."""

    klass: type[Any] | None  # Will be type[TInterface] in practice
    description: str
    icon: str
    priority: int


@skip_during_migrations
def discover_registries() -> None:
    """Discover, clear, and reload all registries and send reload signals."""
    import_by_name.cache_clear()
    autodiscover_modules("registry")

    for registry_cls in django_stratagem_registry:
        registry_cls.clear_cache()
        registry_cls.discover_implementations()
        registry_reloaded.send(sender=registry_cls, registry=registry_cls)
        logger.info(
            "Registry '%s' reloaded with %d implementations",
            registry_cls.__name__,
            len(registry_cls.implementations),
        )


@skip_during_migrations
def update_choices_fields() -> None:
    """Set model fields' choices from each registry."""
    from django.apps import apps as django_apps

    for registry_cls in django_stratagem_registry:
        for field_name, model_cls in registry_cls.choices_fields:
            try:
                model = django_apps.get_model(
                    model_cls._meta.app_label,  # noqa  # pyright: ignore[reportAttributeAccessIssue]
                    model_cls._meta.model_name,  # noqa  # pyright: ignore[reportAttributeAccessIssue]
                )
                field = model._meta.get_field(field_name)  # noqa
                field.choices = registry_cls.get_choices()
            except (LookupError, AttributeError) as exc:
                logger.error("Failed to update choices for %s.%s: %s", model_cls, field_name, exc)


class RegistryMeta(type):
    """Metaclass that lets Registry classes support `in`, `iter`, and `len`."""

    def __contains__(cls, item):
        return cast(type[Registry], cls).is_valid(item)

    def __iter__(cls):
        for meta in getattr(cls, "implementations", {}).values():
            yield meta["klass"]

    def __len__(cls):
        return len(getattr(cls, "implementations", {}))

    def __bool__(cls):
        return True  # Registry classes are always truthy, even when empty


class Registry(Generic[TInterface], metaclass=RegistryMeta):
    """Base class to define and manage registries of Interface implementations."""

    choices_fields: list[tuple[str, type[Model]]] = []
    label_attribute: str | None = None
    implementations_module: str
    implementations: dict[str, ImplementationMeta]
    interface_class: type[TInterface] | None = None

    def __init_subclass__(cls) -> None:
        """Initialize concrete subclass registries and append to global index if implementations_module is defined."""
        super().__init_subclass__()
        # Skip abstract/base registry classes without an implementations_module
        if not getattr(cls, "implementations_module", None):
            logger.debug("Skipping registration of abstract registry class: %s", cls.__name__)
            return
        cls.implementations = {}
        cls.choices_fields = []
        django_stratagem_registry.append(cls)
        logger.debug("Registered new registry class: %s", cls.__name__)

    @classmethod
    def get_cache_key(cls, suffix: str) -> str:
        """Construct cache key for this registry."""
        return f"django_stratagem:{cls.__name__}:{suffix}"

    @classmethod
    def validate_implementation(cls, implementation: type[TInterface]) -> None:
        """Validate an implementation before registration.

        Called by ``register()`` before the implementation is stored. Override to
        add custom validation logic. Raise any exception to reject registration.

        The default implementation checks that the implementation has a non-empty
        ``slug`` attribute and, if ``interface_class`` is set, that the
        implementation is a subclass of it.
        """
        slug = getattr(implementation, "slug", None)
        if not slug:
            logger.error("Cannot register implementation without slug: %s", implementation)
            raise ValueError("Implementation must define a non-empty 'slug'")

        if cls.interface_class:
            interface_cls = cls.interface_class
            if isinstance(interface_cls, str):
                interface_cls = import_by_name(interface_cls)
            if not issubclass(implementation, interface_cls):
                raise TypeError(f"Implementation {implementation} must inherit from {interface_cls}")

    @classmethod
    def build_implementation_meta(cls, implementation: type[TInterface]) -> ImplementationMeta:
        """Build the metadata dict for an implementation.

        Called by ``register()`` after validation. Override to add custom metadata
        fields (e.g. ``version``, ``author``, ``registered_at``). Call ``super()``
        to preserve the default keys.

        Returns a dict that will be stored in ``cls.implementations[slug]``.
        """
        return {
            "klass": implementation,
            "description": getattr(implementation, "description", ""),
            "icon": getattr(implementation, "icon", ""),
            "priority": getattr(implementation, "priority", 0),
        }

    @classmethod
    def on_register(cls, slug: str, implementation: type[TInterface], meta: ImplementationMeta) -> None:
        """Hook called after an implementation is stored and cache is cleared, but before the signal.

        Override to perform side effects such as audit logging or metrics collection.
        """

    @classmethod
    def on_unregister(cls, slug: str, meta: ImplementationMeta) -> None:
        """Hook called after an implementation is removed and cache is cleared, but before the signal.

        Override to perform cleanup or audit logging. Receives the popped metadata dict.
        """

    @classmethod
    def register(cls, implementation: type[TInterface]) -> None:
        """Register an Interface implementation and emit signal."""
        cls.validate_implementation(implementation)
        slug = getattr(implementation, "slug", None)
        if not isinstance(slug, str):
            raise TypeError(f"Expected slug to be a string, got {type(slug).__name__}")
        meta = cls.build_implementation_meta(implementation)
        if slug in cls.implementations:
            existing = cls.implementations[slug].get("klass")
            if existing is not implementation:
                logger.warning(
                    "Overwriting slug '%s' in registry '%s': %s -> %s",
                    slug,
                    cls.__name__,
                    existing,
                    implementation,
                )
        cls.implementations[slug] = meta
        cls.clear_cache()
        cls.on_register(slug, implementation, meta)
        implementation_registered.send(sender=cls, registry=cls, implementation=implementation)
        logger.info("Implementation '%s' registered in registry '%s'", slug, cls.__name__)

    @classmethod
    def unregister(cls, slug: str) -> None:
        """Unregister an implementation by its slug and emit signal."""
        if slug not in cls.implementations:
            logger.warning("Attempted to unregister missing slug '%s' from registry '%s'", slug, cls.__name__)
            raise ImplementationNotFound(f"No implementation for slug '{slug}' to unregister")

        meta = cls.implementations.pop(slug)
        cls.clear_cache()
        cls.on_unregister(slug, meta)
        implementation_unregistered.send(sender=cls, registry=cls, slug=slug)
        logger.info("Implementation '%s' unregistered from registry '%s'", slug, cls.__name__)

    @classmethod
    @skip_during_migrations
    def discover_implementations(cls) -> None:
        """Autodiscover modules to load implementations, if configured."""
        module_name = getattr(cls, "implementations_module", None)
        if module_name:
            autodiscover_modules(module_name)
        else:
            logger.debug("No implementations_module defined for %s; skipping autodiscover.", cls.__name__)

        # Then, load any plugin implementations
        from .plugins import PluginLoader

        PluginLoader.load_plugin_implementations(cls)

    @classmethod
    @skip_during_migrations
    def get_choices(cls) -> list[tuple[str, str]]:
        """Return a list of (slug, label) tuples, using cache if available."""
        key = cls.get_cache_key("choices")
        choices = cache.get(key)
        if choices is None:
            choices = []
            for slug, meta in sorted(
                cls.implementations.items(),
                key=lambda item: item[1].get("priority", 0),
            ):
                implementation = cast("type[Interface]", meta["klass"])
                choices.append((slug, cls.get_display_name(implementation)))
            cache.set(key, choices, get_cache_timeout())
            cache.set(
                cls.get_cache_key("last_updated"),
                timezone.now().isoformat(),
                get_cache_timeout(),
            )
            logger.debug("Choices cache populated for %s", cls.__name__)
        return choices

    @classmethod
    def get_display_name(cls, implementation: type[Interface]) -> str:
        """Return a human-readable label for the implementation."""
        return get_display_string(implementation, cls.label_attribute)

    @overload
    @classmethod
    def get(
        cls,
        *,
        slug: str,
        fully_qualified_name: None = None,
    ) -> TInterface: ...

    @overload
    @classmethod
    def get(
        cls,
        *,
        slug: None = None,
        fully_qualified_name: str,
    ) -> TInterface: ...

    @classmethod
    def get(
        cls,
        *,
        slug: str | None = None,
        fully_qualified_name: str | None = None,
    ) -> TInterface:
        """Instantiate and return an implementation by slug or fully qualified class name."""
        if slug:
            meta = cls.implementations.get(slug)
            if not meta:
                logger.error("Requested slug '%s' not found in registry '%s'", slug, cls.__name__)
                raise ImplementationNotFound(f"No implementation exists for slug '{slug}'")
            impl_class = cast("type[TInterface]", meta["klass"])
            return impl_class()

        if fully_qualified_name:
            try:
                impl_cls = cast("type[TInterface]", get_class(fully_qualified_name))
            except (ImportError, AttributeError, ValueError) as exc:
                logger.error("Failed to import '%s': %s", fully_qualified_name, exc)
                raise
            return impl_cls()

        raise ValueError("Either 'slug' or 'fully_qualified_name' must be provided")

    @classmethod
    def get_or_default(
        cls,
        *,
        slug: str | None = None,
        fully_qualified_name: str | None = None,
        default: str | None = None,
    ) -> TInterface | None:
        """Get an implementation by slug or fully qualified name (FQN), falling back to a default.

        Unlike `get()`, this method does not raise `ImplementationNotFound`.
        Returns None if neither the requested implementation nor the default is found.
        """
        try:
            if slug is not None:
                return cls.get(slug=slug)
            elif fully_qualified_name is not None:
                return cls.get(fully_qualified_name=fully_qualified_name)
            else:
                raise ValueError("Either 'slug' or 'fully_qualified_name' must be provided")
        except (ImplementationNotFound, ImportError, AttributeError, ValueError):
            pass

        if default is not None:
            try:
                return cls.get(slug=default)
            except (ImplementationNotFound, ImportError, AttributeError, ValueError):
                pass

        return None

    @classmethod
    def get_class(
        cls,
        *,
        slug: str | None = None,
        fully_qualified_name: str | None = None,
    ) -> type[TInterface]:
        """Return the implementation class without instantiating."""
        if slug:
            meta = cls.implementations.get(slug)
            if not meta:
                logger.error("Requested slug '%s' not found in registry '%s'", slug, cls.__name__)
                raise ImplementationNotFound(f"No implementation exists for slug '{slug}'")
            return cast("type[TInterface]", meta["klass"])

        if fully_qualified_name:
            return cast("type[TInterface]", get_class(fully_qualified_name))

        raise ValueError("Either 'slug' or 'fully_qualified_name' must be provided")

    @classmethod
    def get_implementation_class(cls, slug: str) -> type[TInterface]:
        """Get the implementation class for a given slug.

        Raises ImplementationNotFound if the slug is not registered.
        """
        if slug not in cls.implementations:
            raise ImplementationNotFound(f"No implementation registered for slug '{slug}'")
        return cast("type[TInterface]", cls.implementations[slug]["klass"])

    @classmethod
    def get_implementation_meta(cls, slug: str) -> ImplementationMeta:
        """Get the full metadata dict for an implementation.

        Raises ImplementationNotFound if the slug is not registered.
        """
        if slug not in cls.implementations:
            raise ImplementationNotFound(f"No implementation registered for slug '{slug}'")
        return cls.implementations[slug]

    @classmethod
    @skip_during_migrations
    def get_items(cls) -> list[tuple[str, type[TInterface]]]:
        """Return cached list of (slug, class) pairs."""
        key = cls.get_cache_key("items")
        items = cache.get(key)
        if items is None:
            items = [(slug, cast("type[TInterface]", meta["klass"])) for slug, meta in cls.implementations.items()]
            cache.set(key, items, get_cache_timeout())
            logger.debug("Items cache populated for %s", cls.__name__)
        return items

    @classmethod
    def choices_field(cls, *args: object, **kwargs: object) -> AbstractRegistryField:
        """Factory for a RegistryClassField tied to this registry."""
        from .fields import RegistryClassField

        # This stores the class reference rather than an instance
        field = RegistryClassField(*args, registry=cls, **kwargs)
        return field

    @classmethod
    def instance_field(cls, *args: object, **kwargs: object) -> AbstractRegistryField:
        """Factory for a RegistryField (instance) tied to this registry."""
        from .fields import RegistryField

        # This creates instances of the registered classes
        field = RegistryField(*args, registry=cls, **kwargs)
        return field

    @classmethod
    def is_valid(cls, value: object) -> bool:
        """Validate if value corresponds to a registered implementation."""
        try:
            # Resolve interface_class if it's a string
            interface_cls = None
            if cls.interface_class:
                interface_cls = cls.interface_class
                if isinstance(interface_cls, str):
                    interface_cls = import_by_name(interface_cls)

            if isinstance(value, str):
                if value in cls.implementations:
                    return True
                impl_cls = import_by_name(value)
                if interface_cls:
                    return issubclass(impl_cls, interface_cls)
                return any(impl_cls is meta["klass"] for meta in cls.implementations.values())

            if isinstance(value, type):
                return (not interface_cls or issubclass(value, interface_cls)) and any(
                    value is meta["klass"] for meta in cls.implementations.values()
                )

            # instance check
            if interface_cls and isinstance(value, interface_cls):
                return True
            return any(
                isinstance(value, meta["klass"]) for meta in cls.implementations.values() if meta["klass"] is not None
            )

        except (ImportError, AttributeError, ValueError) as exc:
            logger.debug("Validation check failed for %s: %s", value, exc)
            return False

    @classmethod
    def clear_cache(cls) -> None:
        """Evict this registry's cache entries."""
        cache.delete_many(
            [
                cls.get_cache_key("choices"),
                cls.get_cache_key("items"),
            ]
        )
        logger.debug("Cache cleared for %s", cls.__name__)

    @staticmethod
    def clear_all_cache() -> None:
        """Evict cache for all registries."""
        import_by_name.cache_clear()
        for reg in django_stratagem_registry:
            reg.clear_cache()

    @classmethod
    @skip_during_migrations
    def check_health(cls) -> dict[str, object]:
        """Return basic health metrics for monitoring."""
        return {"count": len(cls.implementations), "last_updated": cache.get(f"{cls.get_cache_key('last_updated')}")}

    @classmethod
    def contains(cls, item: object) -> bool:
        """Check if item is valid for this registry."""
        return cls.is_valid(item)

    @classmethod
    def iter_implementations(cls):
        """Iterate over implementation metadata dicts."""
        return iter(cls.implementations.values())

    @classmethod
    def count_implementations(cls) -> int:
        """Return number of implementations."""
        return len(cls.implementations)

    @classmethod
    def get_available_implementations(cls, context: dict[str, Any] | None = None) -> dict[str, type[TInterface]]:
        """Get all implementations available in the current context."""
        available = {}

        for slug, meta in cls.implementations.items():
            impl_class = meta["klass"]

            # Check if implementation has conditional availability
            is_available_method = getattr(impl_class, "is_available", None)
            if impl_class is not None and callable(is_available_method):
                if not is_available_method(context):
                    continue

            available[slug] = impl_class

        return available

    @classmethod
    def get_choices_for_context(cls, context: dict[str, Any] | None = None) -> list[tuple[str, str]]:
        """Get choices filtered by context."""
        choices = []
        available = cls.get_available_implementations(context)

        for slug, impl_class in sorted(
            available.items(), key=lambda item: cls.implementations[item[0]].get("priority", 0)
        ):
            choices.append((slug, cls.get_display_name(impl_class)))

        return choices

    @classmethod
    def get_for_context(
        cls,
        context: dict[str, Any] | None = None,
        *,
        slug: str | None = None,
        fully_qualified_name: str | None = None,
        fallback: str | None = None,
    ) -> TInterface:
        """Get implementation considering context constraints."""
        # Try to get the requested implementation
        try:
            if slug:
                implementation = cls.get(slug=slug)
            elif fully_qualified_name:
                implementation = cls.get(fully_qualified_name=fully_qualified_name)
            else:
                implementation = None

            if implementation is not None:
                impl_class = type(implementation)

                # Check if it's available in this context
                is_available_method = getattr(impl_class, "is_available", None)
                if is_available_method is not None and callable(is_available_method):
                    if is_available_method(context):
                        return implementation
                    logger.warning("Implementation '%s' not available in current context", slug or fully_qualified_name)
                else:
                    # No is_available method means always available
                    return implementation

        except (ImplementationNotFound, ImportError, AttributeError, ValueError):
            pass

        # Try fallback if provided
        if fallback:
            return cls.get(slug=fallback)

        # Get first available implementation
        available = cls.get_available_implementations(context)
        if available:
            first_slug = next(iter(available))
            return cls.get(slug=first_slug)

        raise ImplementationNotFound("No implementations available in current context")


class HierarchicalRegistry(Registry):
    """Registry that supports parent-child relationships with other registries."""

    implementations_module: str
    parent_registry: type[Registry] | None = None

    # Define which parent implementations this registry provides children for
    parent_slugs: list[str] | None = None

    def __init_subclass__(cls):
        """Initialize concrete subclass registries and append to global index if implementations_module is defined."""
        super().__init_subclass__()
        parent = getattr(cls, "parent_registry", None)
        if parent:
            RegistryRelationship.register_child(parent, cls)

    @classmethod
    def clear_cache(cls) -> None:
        """Evict this registry's cache entries, including hierarchy_map."""
        super().clear_cache()
        cache.delete(cls.get_cache_key("hierarchy_map"))

    @classmethod
    def get_parent_registry(cls) -> type[Registry] | None:
        """Get the parent registry for this hierarchical registry."""
        return cls.parent_registry

    @classmethod
    def get_children_for_parent(
        cls, parent_slug: str, context: dict[str, Any] | None = None
    ) -> dict[str, type[Interface]]:
        """Get child implementations available for a specific parent slug."""
        # Check if this registry handles this parent
        if cls.parent_slugs and parent_slug not in cls.parent_slugs:
            return {}

        # Get all available implementations (considering context)
        if context:
            return cls.get_available_implementations(context)

        return {slug: meta["klass"] for slug, meta in cls.implementations.items() if meta["klass"] is not None}

    @classmethod
    def get_choices_for_parent(cls, parent_slug: str, context: dict[str, Any] | None = None) -> list[tuple[str, str]]:
        """Get choices filtered by parent selection."""
        children = cls.get_children_for_parent(parent_slug, context)

        choices = []
        for slug, impl_class in sorted(
            children.items(), key=lambda item: cls.implementations[item[0]].get("priority", 0)
        ):
            choices.append((slug, cls.get_display_name(impl_class)))

        return choices

    @classmethod
    def validate_parent_child_relationship(cls, parent_slug: str, child_slug: str) -> bool:
        """Validate that a child implementation is valid for a parent."""
        if not cls.parent_slugs:
            # No restrictions, all children valid for all parents
            return child_slug in cls.implementations

        # Check if parent is in allowed list
        if parent_slug not in cls.parent_slugs:
            return False

        return child_slug in cls.implementations

    @classmethod
    def get_hierarchy_map(cls) -> dict[str, list[str]]:
        """Get a map of parent slugs to available child slugs."""
        cache_key = cls.get_cache_key("hierarchy_map")
        hierarchy_map = cache.get(cache_key)

        if hierarchy_map is None:
            hierarchy_map = {}

            if not cls.parent_registry:
                cache.set(cache_key, {}, get_cache_timeout())
                return {}

            # Get all parent implementations
            parent_impls = cls.parent_registry.get_items()

            for parent_slug, _ in parent_impls:
                # Check if this registry handles this parent
                if cls.parent_slugs and parent_slug not in cls.parent_slugs:
                    continue

                # Get children for this parent
                children = cls.get_children_for_parent(parent_slug)
                hierarchy_map[parent_slug] = list(children.keys())

            cache.set(cache_key, hierarchy_map, get_cache_timeout())

        return hierarchy_map


class RegistryRelationship:
    """Tracks parent-child relationships between registries."""

    _relationships: dict[type[Registry], list[type[Registry]]] = {}

    @classmethod
    def register_child(cls, parent_registry: type[Registry], child_registry: type[HierarchicalRegistry]) -> None:
        """Register a parent-child relationship between registries."""
        if parent_registry not in cls._relationships:
            cls._relationships[parent_registry] = []

        if child_registry not in cls._relationships[parent_registry]:
            cls._relationships[parent_registry].append(child_registry)

        # Set parent on child
        child_registry.parent_registry = parent_registry

        logger.info("Registered hierarchical relationship: %s -> %s", parent_registry.__name__, child_registry.__name__)

    @classmethod
    def get_children_registries(
        cls, parent_registry: type[Registry]
    ) -> list[type[Registry]] | list[type[HierarchicalRegistry]]:
        """Get all child registries for a parent."""
        return cls._relationships.get(parent_registry, [])

    @classmethod
    def get_all_descendants(cls, registry: type[Registry]) -> list[type[Registry]]:
        """Recursively get all descendant registries."""
        descendants = []
        children = cls.get_children_registries(registry)

        for child in children:
            descendants.append(child)
            # Recursively get children of children
            descendants.extend(cls.get_all_descendants(child))

        return descendants

    @classmethod
    def clear_relationships(cls) -> None:
        """Clear all registered relationships (mainly for testing)."""
        cls._relationships.clear()


def register(registry_cls: type[Registry]) -> Callable[[type[Any]], type[Any]]:
    """Decorator to explicitly register an Interface subclass to a Registry."""

    def decorator(implementation_cls: type[Interface]) -> type[Interface]:
        registry_cls.register(implementation_cls)
        return implementation_cls

    return decorator

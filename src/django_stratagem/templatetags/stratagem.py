from django import template

from ..registry import django_stratagem_registry

register = template.Library()


@register.simple_tag
def get_implementations(registry, context=None):
    """Get all implementations for a registry, optionally filtered by context.

    Usage:
        {% load stratagem %}
        {% get_implementations my_registry as implementations %}
        {% get_implementations my_registry context as implementations %}
    """
    if context is not None:
        return registry.get_available_implementations(context)
    return {slug: meta["klass"] for slug, meta in registry.implementations.items()}


@register.simple_tag
def get_choices(registry, context=None):
    """Get choices list for a registry.

    Usage:
        {% load stratagem %}
        {% get_choices my_registry as choices %}
    """
    if context is not None:
        return registry.get_choices_for_context(context)
    return registry.get_choices()


@register.simple_tag
def get_registries():
    """Get all registered registries.

    Usage:
        {% load stratagem %}
        {% get_registries as registries %}
    """
    return list(django_stratagem_registry)


@register.filter
def display_name(implementation, registry=None):
    """Get the display name for an implementation.

    Usage:
        {% load stratagem %}
        {{ implementation|display_name }}
        {{ implementation|display_name:my_registry }}
    """
    if registry is not None:
        return registry.get_display_name(implementation)

    # Try to find the registry for this implementation
    for reg in django_stratagem_registry:
        for meta in reg.implementations.values():
            if meta["klass"] is implementation or (
                not isinstance(implementation, type) and isinstance(implementation, meta["klass"])
            ):
                return reg.get_display_name(
                    implementation if isinstance(implementation, type) else type(implementation)
                )

    # Fallback to class name
    if isinstance(implementation, type):
        return implementation.__name__
    return type(implementation).__name__


@register.filter
def registry_icon(implementation):
    """Get the icon for an implementation.

    Usage:
        {% load stratagem %}
        {{ implementation|registry_icon }}
    """
    if isinstance(implementation, type):
        return getattr(implementation, "icon", "")
    return getattr(type(implementation), "icon", "")


@register.filter
def registry_description(implementation):
    """Get the description for an implementation.

    Usage:
        {% load stratagem %}
        {{ implementation|registry_description }}
    """
    if isinstance(implementation, type):
        return getattr(implementation, "description", "")
    return getattr(type(implementation), "description", "")


@register.filter
def is_available(implementation, context=None):
    """Check if an implementation is available in the given context.

    Usage:
        {% load stratagem %}
        {% if implementation|is_available:context %}...{% endif %}
    """
    check_method = getattr(implementation, "is_available", None)
    if check_method and callable(check_method):
        return check_method(context or {})
    return True

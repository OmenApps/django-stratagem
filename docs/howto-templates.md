# How to Use Template Tags and Filters

django-stratagem ships template tags and filters for rendering registry data.

## Loading Template Tags

```html
{% load stratagem %}
```

## Tags

### get_implementations

Get all implementations for a registry, optionally filtered by context.

```html
{% get_implementations my_registry as implementations %}
{% get_implementations my_registry context as implementations %}

{% for slug, impl in implementations.items %}
    <p>{{ slug }}: {{ impl }}</p>
{% endfor %}
```

### get_choices

Get a choices list for a registry.

```html
{% get_choices my_registry as choices %}
{% get_choices my_registry context as choices %}

{% for slug, label in choices %}
    <option value="{{ slug }}">{{ label }}</option>
{% endfor %}
```

### get_registries

Get all registered registries.

```html
{% get_registries as registries %}
{% for registry in registries %}
    <h3>{{ registry.__name__ }}</h3>
{% endfor %}
```

## Filters

### display_name

Get the human-readable display name for an implementation.

```html
{{ implementation|display_name }}
{{ implementation|display_name:my_registry }}
```

### registry_icon

Get the icon for an implementation.

```html
{{ implementation|registry_icon }}
```

### registry_description

Get the description for an implementation.

```html
{{ implementation|registry_description }}
```

### is_available

Check if an implementation is available in a given context.

```html
{% if implementation|is_available:context %}
    Available
{% endif %}
```

## Full Example

A fuller example listing notification channels with their metadata:

```html
{% load stratagem %}

{% get_implementations notification_registry request_context as channels %}

<div class="channels">
{% for slug, impl in channels.items %}
    <div class="channel-card">
        {% if impl|registry_icon %}
            <img src="{{ impl|registry_icon }}" alt="">
        {% endif %}
        <h3>{{ impl|display_name }}</h3>
        <p>{{ impl|registry_description }}</p>
        {% if impl|is_available:request_context %}
            <span class="status available">Available</span>
        {% else %}
            <span class="status unavailable">Unavailable</span>
        {% endif %}
    </div>
{% endfor %}
</div>
```

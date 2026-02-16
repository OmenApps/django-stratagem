# Getting Started

## Installation

Install django-stratagem with pip:

```bash
pip install django-stratagem
```

Add `django_stratagem` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "django_stratagem",
    # ...
]
```

### Requirements

- Python 3.10+
- Django 4.2+

For DRF integration, install the optional extra:

```bash
pip install django-stratagem[drf]
```

## Core Concepts

The main pieces are a **Registry** (holds a set of implementations), an **Interface** (the base class implementations extend), **implementations** (concrete classes with a `slug`), and **auto-discovery** (imports them at startup). You define a registry by subclassing `Registry` and setting `implementations_module` to name the module where implementations live. Each implementation subclasses your `Interface`, sets a unique `slug`, and optionally provides `description`, `icon`, and `priority`. On app startup, django-stratagem calls `autodiscover_modules()` for each registry's `implementations_module`, importing and registering everything automatically.

```{mermaid}
classDiagram
    class Registry {
        implementations_module = "notifications"
        get(slug)
        get_choices()
    }
    class Interface {
        registry = NotificationRegistry
        send(message, recipient)*
    }
    class EmailNotification {
        slug = "email"
        send(message, recipient)
    }
    class SMSNotification {
        slug = "sms"
        send(message, recipient)
    }
    Registry "1" *-- "*" Interface : holds
    Interface <|-- EmailNotification
    Interface <|-- SMSNotification
```

## Your First Registry

### 1. Define the Registry and Interface

Create a registry module in your app:

```python
# myapp/registry.py
from django_stratagem import Registry, Interface

class NotificationRegistry(Registry):
    implementations_module = "notifications"

class NotificationInterface(Interface):
    registry = NotificationRegistry

    def send(self, message: str, recipient: str) -> bool:
        raise NotImplementedError
```

### 2. Create Implementations

Create the implementations module matching `implementations_module`:

```python
# myapp/notifications.py
from myapp.registry import NotificationInterface

class EmailNotification(NotificationInterface):
    slug = "email"
    description = "Send notifications via email"
    priority = 10

    def send(self, message, recipient):
        # send email...
        return True

class SMSNotification(NotificationInterface):
    slug = "sms"
    description = "Send notifications via SMS"
    priority = 20

    def send(self, message, recipient):
        # send SMS...
        return True
```

Implementations are auto-registered when their module is imported. django-stratagem discovers them automatically via `autodiscover_modules("notifications")` on app startup.

### File Layout

```
myapp/
├── __init__.py
├── registry.py           # Registry + Interface
├── notifications.py      # Implementations (matches implementations_module)
├── models.py
└── ...
```

### What happens at startup

When Django starts, django-stratagem finds your registries, imports the implementation modules, and populates model field choices - all before the first request is served.

```{mermaid}
flowchart LR
    A[Django starts] --> B[Discover registries]
    B --> C["Import each registry's implementations_module"]
    C --> D[Classes register themselves via __init_subclass__]
    D --> E[Model field choices are populated]
```

For the full startup lifecycle, including migration safety and plugin loading, see [How Auto-Discovery Works](explanation.md#how-auto-discovery-works).

## Using the Registry

Once registered, you interact with implementations through the registry:

```python
from myapp.registry import NotificationRegistry

# Iterate over all registered implementation classes
for impl_class in NotificationRegistry:
    print(impl_class.slug)

# Get an instance by slug
impl = NotificationRegistry.get(slug="email")
impl.send("Hello!", "user@example.com")

# Get the class without instantiation
cls = NotificationRegistry.get_class(slug="email")

# Safe get with fallback
impl = NotificationRegistry.get_or_default(slug="nonexistent", default="email")

# Get choices for forms (list of (slug, label) tuples)
choices = NotificationRegistry.get_choices()
# [("email", "Email Notification"), ("sms", "SMS Notification")]

# Membership check
"email" in NotificationRegistry  # True

# Count implementations
len(NotificationRegistry)  # 2
```

## Using in Models

django-stratagem provides model fields that store references to registry implementations in the database.

### `choices_field()` - Store a Class Reference

```python
from django.db import models
from myapp.registry import NotificationRegistry

class NotificationConfig(models.Model):
    # Stores the class; accessing the field returns the class
    strategy = NotificationRegistry.choices_field()
```

```python
config = NotificationConfig()
config.strategy = EmailNotification  # Set by class
config.strategy = "email"            # Or by slug
config.save()

config.strategy  # Returns the EmailNotification class
```

### `instance_field()` - Store and Instantiate

```python
class NotificationConfig(models.Model):
    # Stores the class; accessing the field returns an instance
    strategy = NotificationRegistry.instance_field()
```

```python
config = NotificationConfig.objects.get(pk=1)
config.strategy.send("Hello!", "user@example.com")  # Already an instance
```

See [How to Use Model Fields](howto-fields.md) for all field types and options.

## Exposing Options to Users

The model fields above are enough to store a selection, but the real point is giving your users a way to pick one. django-stratagem plugs into forms, the admin, and DRF so the choices show up automatically.

### Forms

Registry model fields produce form dropdowns by default. You can also use `RegistryFormField` directly:

```python
from django_stratagem import RegistryFormField

class NotificationConfigForm(forms.Form):
    strategy = RegistryFormField(registry=NotificationRegistry)
```

The user sees a `<select>` with your registered implementations as options. See [How to Use Forms, Widgets, and the Admin](howto-forms-admin.md) for context-aware filtering and hierarchical fields.

### Admin

One mixin gives you dropdowns and list filters with no extra work:

```python
from django.contrib import admin
from django_stratagem.admin import ContextAwareRegistryAdmin

@admin.register(NotificationConfig)
class NotificationConfigAdmin(ContextAwareRegistryAdmin):
    pass
```

This automatically filters choices based on the logged-in admin's permissions when you're using [conditional availability](howto-conditions.md). See [How to Use Forms, Widgets, and the Admin](howto-forms-admin.md#django-admin) for hierarchical admin support and dashboard views.

### DRF

If you're building an API, install the optional `drf` extra and use `DrfRegistryField`:

```python
from rest_framework import serializers
from django_stratagem.drf.serializers import DrfRegistryField

class NotificationConfigSerializer(serializers.Serializer):
    strategy = DrfRegistryField(registry=NotificationRegistry)
```

Accepts slugs as input, validates against the registry, and serializes back to slugs. See [How to Use DRF Integration](howto-drf.md) for multiple-choice fields and the built-in API views.

## Configuration

Configure django-stratagem via the `DJANGO_STRATAGEM` dict in your Django settings:

```python
# settings.py
DJANGO_STRATAGEM = {
    "CACHE_TIMEOUT": 300,           # Cache TTL in seconds (default: 300)
    "SKIP_DURING_MIGRATIONS": True,  # Skip registry ops during migrations (default: True)
    "ENABLED_PLUGINS": None,         # List of enabled plugin names, or None for all
    "DISABLED_PLUGINS": [],          # List of disabled plugin names
}
```

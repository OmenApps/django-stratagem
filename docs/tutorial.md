# Building a Complete Feature

This tutorial picks up where the [Getting Started](quickstart.md) guide left off. You already have a `NotificationRegistry` with `EmailNotification` and `SMSNotification`. Now you'll add conditional availability, hierarchical sub-registries, a plugin, and signals.

## Prerequisites

You should have the basic notification registry working from the [Getting Started](quickstart.md) guide:

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

## Step 1: Add Conditional Availability

Some notification channels should only be available to certain users. For example, push notifications might require a specific permission.

### Create a conditional implementation

Add a `PushNotification` that requires the `myapp.use_push` permission:

```python
# myapp/notifications.py
from django_stratagem import ConditionalInterface, PermissionCondition
from myapp.registry import NotificationRegistry

class PushNotification(ConditionalInterface):
    registry = NotificationRegistry
    slug = "push"
    description = "Send push notifications"
    priority = 30
    condition = PermissionCondition("myapp.use_push")

    def send(self, message, recipient):
        # send push notification...
        return True
```

`ConditionalInterface` works just like `Interface`, but adds a `condition` attribute that controls when the implementation is available.

### Test with different user contexts

```python
from myapp.registry import NotificationRegistry

# A regular user without the permission
context = {"user": regular_user}
available = NotificationRegistry.get_available_implementations(context)
# {"email": <class EmailNotification>, "sms": <class SMSNotification>}
# push is NOT included

# An admin user with the permission
context = {"user": admin_user}
available = NotificationRegistry.get_available_implementations(context)
# {"email": ..., "sms": ..., "push": <class PushNotification>}
```

You can compose conditions with `&`, `|`, and `~` for more complex rules. See [How to Use Conditional Availability](howto-conditions.md) for all built-in conditions and composition patterns.

## Step 2: Add a Hierarchical Sub-Registry

Suppose each notification channel has sub-options - for email, you might choose HTML or plain text format; for SMS, you might choose a provider. Hierarchical registries model these parent-child relationships.

### Define the child registry

```python
# myapp/registry.py
from django_stratagem import Registry, Interface, HierarchicalRegistry, HierarchicalInterface

class NotificationRegistry(Registry):
    implementations_module = "notifications"

class NotificationInterface(Interface):
    registry = NotificationRegistry

    def send(self, message: str, recipient: str) -> bool:
        raise NotImplementedError

class NotificationFormatRegistry(HierarchicalRegistry):
    implementations_module = "notification_formats"
    parent_registry = NotificationRegistry
```

### Create child implementations

```python
# myapp/notification_formats.py
from django_stratagem import HierarchicalInterface
from myapp.registry import NotificationFormatRegistry

class HTMLEmail(HierarchicalInterface):
    registry = NotificationFormatRegistry
    slug = "html_email"
    description = "Rich HTML email"
    parent_slug = "email"  # Only valid under EmailNotification

class PlainTextEmail(HierarchicalInterface):
    registry = NotificationFormatRegistry
    slug = "plain_text_email"
    description = "Plain text email"
    parent_slug = "email"

class TwilioSMS(HierarchicalInterface):
    registry = NotificationFormatRegistry
    slug = "twilio_sms"
    description = "SMS via Twilio"
    parent_slug = "sms"
```

### Query filtered by parent

```python
from myapp.registry import NotificationFormatRegistry

# Get formats available for email
formats = NotificationFormatRegistry.get_children_for_parent("email")
# {"html_email": <class HTMLEmail>, "plain_text_email": <class PlainTextEmail>}

# Get choices for a form dropdown filtered by parent
choices = NotificationFormatRegistry.get_choices_for_parent("email")
# [("html_email", "HTML Email"), ("plain_text_email", "Plain Text Email")]
```

### Use in a model

```python
# myapp/models.py
from django.db import models
from django_stratagem import HierarchicalRegistryField
from myapp.registry import NotificationRegistry, NotificationFormatRegistry

class NotificationConfig(models.Model):
    channel = NotificationRegistry.choices_field()
    format = HierarchicalRegistryField(
        registry=NotificationFormatRegistry,
        parent_field="channel",
    )
```

The `parent_field` parameter tells the field to validate that the selected format is valid for the selected channel. See [How to Use Hierarchical Registries](howto-hierarchies.md) for more.

## Step 3: Write a Simple Plugin

Plugins let third-party packages add implementations to your registry without modifying your code. We'll create a webhook notification as a plugin.

### Create the implementation

```python
# django_webhook_notifications/notifications.py
from myapp.registry import NotificationInterface

class WebhookNotification(NotificationInterface):
    slug = "webhook"
    description = "Send notifications via webhook"
    priority = 50

    def send(self, message, recipient):
        # POST to webhook URL...
        return True
```

### Create plugin metadata

```python
# django_webhook_notifications/stratagem_plugin.py

__version__ = "1.0.0"

REGISTRY = "NotificationRegistry"

IMPLEMENTATIONS = [
    "django_webhook_notifications.notifications.WebhookNotification",
]
```

### Register the entry point

In the plugin's `pyproject.toml`:

```toml
[project.entry-points."django_stratagem.plugins"]
webhook_notifications = "django_webhook_notifications.stratagem_plugin"
```

Once installed, the webhook option appears in `NotificationRegistry` automatically - in forms, admin, and API responses. See [How to Use the Plugin System](howto-plugins.md) for more on plugin development.

## Step 4: React to Registrations with Signals

django-stratagem emits signals when implementations are registered, unregistered, or when a registry is reloaded. Use them for logging, cache invalidation, or other side effects.

### Log registrations

```python
# myapp/signals.py
from django.dispatch import receiver
from django_stratagem.signals import implementation_registered

@receiver(implementation_registered)
def log_registration(sender, registry, implementation, **kwargs):
    import logging
    logger = logging.getLogger("django_stratagem")
    logger.info(
        "Registered %s in %s",
        implementation.slug,
        registry.__name__,
    )
```

Make sure this module is imported at startup - for example, in your `AppConfig.ready()`:

```python
# myapp/apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = "myapp"

    def ready(self):
        import myapp.signals  # noqa: F401
```

For more signal patterns (cache invalidation, audit trails) and the full list of extension hooks, see [Extension Hooks and Customization Points](hooks.md).

## Step 5: Wire It All Up

Now combine everything into an admin view and a form.

### Admin

```python
# myapp/admin.py
from django.contrib import admin
from django_stratagem.admin import HierarchicalRegistryAdmin
from myapp.models import NotificationConfig

@admin.register(NotificationConfig)
class NotificationConfigAdmin(HierarchicalRegistryAdmin):
    pass
```

`HierarchicalRegistryAdmin` handles both conditional filtering (based on the logged-in admin's permissions) and hierarchical field relationships. See [How to Use Forms, Widgets, and the Admin](howto-forms-admin.md).

### Form

```python
# myapp/forms.py
from django import forms
from django_stratagem import (
    ContextAwareRegistryFormField,
    HierarchicalRegistryFormField,
    RegistryContextMixin,
    HierarchicalFormMixin,
)
from myapp.registry import NotificationRegistry, NotificationFormatRegistry

class NotificationConfigForm(
    RegistryContextMixin,
    HierarchicalFormMixin,
    forms.Form,
):
    channel = ContextAwareRegistryFormField(registry=NotificationRegistry)
    format = HierarchicalRegistryFormField(
        registry=NotificationFormatRegistry,
        parent_field="channel",
    )

# Usage in a view:
form = NotificationConfigForm(
    registry_context={"user": request.user, "request": request},
)
```

### Template

```html
{% load stratagem %}

<h2>Available Notification Channels</h2>
{% get_implementations notification_registry request_context as channels %}
{% for slug, impl in channels.items %}
    <div class="channel">
        <strong>{{ impl|display_name }}</strong>
        <p>{{ impl|registry_description }}</p>
        {% if impl|is_available:request_context %}
            <span class="badge">Available</span>
        {% endif %}
    </div>
{% endfor %}
```

See [How to Use Template Tags and Filters](howto-templates.md) for the full list of tags and filters.

## What's Next

That covers the main intermediate features. The how-to guides go deeper on each topic:

- [How to Use Model Fields](howto-fields.md) - all field types, lookups, factory patterns
- [How to Use Forms, Widgets, and the Admin](howto-forms-admin.md) - form fields, widgets, admin classes
- [How to Use Conditional Availability](howto-conditions.md) - all built-in conditions, composition, custom conditions
- [How to Use Hierarchical Registries](howto-hierarchies.md) - parent-child relationships
- [How to Use DRF Integration](howto-drf.md) - serializer fields and API views
- [How to Use the Plugin System](howto-plugins.md) - writing and using plugins
- [Extension Hooks and Customization Points](hooks.md) - hooks, signals, testing extensions
- [Architecture and Design](explanation.md) - how auto-discovery works, design decisions

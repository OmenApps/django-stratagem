<p align="center">
  <img src="https://raw.githubusercontent.com/OmenApps/django-stratagem/refs/heads/main/docs/_static/django-stratagem.png" alt="django-stratagem logo" width="400">
</p>

# django-stratagem

[![Latest on Django Packages](https://img.shields.io/badge/PyPI-{{ package.slug}}-tags-8c3c26.svg)](https://djangopackages.org/packages/p/django-stratagem/)

Many Django projects reach a point where you want to make the system **configurable** and need a some of the app's behavior to be **swappable**. For instance, if you need to support multiple payment processors and each merchant picks one. Maybe you offer several export formats and users choose CSV, XLSX, or PDF at download time. Maybe different customers get different notification channels depending on their plan.

The usual approach is a mess of nested `if/elif` chains, settings flags, or one-off plugin systems that each work a little differently. django-stratagem replaces all of those with a single pattern: you write each option as a small Python class, and the library auto-discovers it at startup, wires up model fields, populates form and admin dropdowns, and optionally exposes it through DRF.

**How it helps the developer:**

- Add a new option by creating one class in one file. No manual wiring, no migrations.
- Store a user's or tenant's selection in the database with a model field that understands your registry.
- Get dropdowns in forms and the admin automatically - choices stay in sync as you add or remove options.
- Control which options are available to which users using permissions, feature flags, or custom rules.
- Third-party packages can contribute their own options through a plugin entry point.

**What this gives your end users:**

- Admins see a clean dropdown of available options instead of typing class paths or magic strings.
- Options can be enabled, disabled, or restricted per user, role, or tenant without code changes.
- Deploying a new class is enough - no migration needed.

## Example use cases

- **Notification channels** - email, SMS, push, Slack, webhook - let admins pick which channels are active. ([Getting started](docs/quickstart.md))
- **Payment gateways** - Stripe, PayPal, Braintree - store the chosen gateway per merchant in a model field and swap it at runtime.
- **Export/import formats** - CSV, Excel, PDF, JSON - register each format as an option, then offer them as choices in a [form](docs/howto-forms-admin.md) or API endpoint.
- **Authentication backends** - LDAP, SAML, OAuth providers - enable or disable per-tenant with [conditional availability](docs/howto-conditions.md) tied to feature flags or permissions.
- **Pricing / discount strategies** - percentage off, fixed amount, buy-one-get-one - attach the active strategy to a model and let business users pick it in the admin.
- **Report generators** - sales summary, inventory audit, user activity - each report type is a class, and adding a new report is just adding a new module.

## Installation

```bash
pip install django-stratagem
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "django_stratagem",
    # ...
]
```

## Quickstart

### 1. Define a Registry and Interface

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

### 3. Use in Models

```python
# myapp/models.py
from django.db import models
from myapp.registry import NotificationRegistry

class NotificationConfig(models.Model):
    # Stores a reference to the implementation class
    strategy = NotificationRegistry.choices_field()

    # Or store an instance (instantiated on access)
    # strategy = NotificationRegistry.instance_field()
```

### 4. Use in Code

```python
from myapp.registry import NotificationRegistry

# Get all registered implementations
for impl_class in NotificationRegistry:
    print(impl_class.slug)

# Get by slug
impl = NotificationRegistry.get(slug="email")
impl.send("Hello!", "user@example.com")

# Get class without instantiation
cls = NotificationRegistry.get_class(slug="email")

# Safe get with fallback
impl = NotificationRegistry.get_or_default(slug="nonexistent", default="email")

# Get choices for forms
choices = NotificationRegistry.get_choices()
# [("email", "Email Notification"), ("sms", "SMS Notification")]
```

## Features

### Conditional Availability

Use conditions to control when implementations are available:

```python
from django_stratagem import ConditionalInterface, PermissionCondition

class AdminNotification(ConditionalInterface):
    registry = NotificationRegistry
    slug = "admin_only"
    condition = PermissionCondition("myapp.admin_notifications")

    def send(self, message, recipient):
        ...
```

Built-in conditions: `FeatureFlagCondition`, `PermissionCondition`, `SettingCondition`, `CallableCondition`, and several more. Conditions support `&` (AND), `|` (OR), and `~` (NOT) operators.

### Hierarchical Registries

Define parent-child relationships between registries for advanced needs:

```python
from django_stratagem import HierarchicalRegistry, HierarchicalInterface

class CategoryRegistry(Registry):
    implementations_module = "categories"

class SubcategoryRegistry(HierarchicalRegistry):
    implementations_module = "subcategories"
    parent_registry = CategoryRegistry

class MySubcategory(HierarchicalInterface):
    registry = SubcategoryRegistry
    slug = "sub_a"
    parent_slug = "category_a"  # Only valid under category_a
```

### Model Fields

| Field | Description |
|---|---|
| `RegistryClassField` | Stores class reference, returns class on access |
| `RegistryField` | Stores class reference, returns instance on access |
| `MultipleRegistryClassField` | Comma-separated classes |
| `MultipleRegistryField` | Comma-separated instances |
| `HierarchicalRegistryField` | With parent field dependency |

### Django Admin

```python
from django.contrib import admin
from django_stratagem.admin import ContextAwareRegistryAdmin

@admin.register(MyModel)
class MyModelAdmin(ContextAwareRegistryAdmin):
    pass
```

### DRF Integration

Install with DRF support:

```bash
pip install django-stratagem[drf]
```

```python
from django_stratagem.drf.serializers import DrfRegistryField

class MySerializer(serializers.Serializer):
    strategy = DrfRegistryField(registry=NotificationRegistry)
```

### Template Tags

```html
{% load stratagem %}

{% get_implementations my_registry as implementations %}
{% for slug, impl in implementations.items %}
    {{ impl|display_name }} - {{ impl|registry_icon }}
{% endfor %}
```

### Plugin System

External packages can register implementations via entry points:

```toml
# In the plugin's pyproject.toml
[project.entry-points."django_stratagem.plugins"]
my_plugin = "my_plugin.stratagem_plugin"
```

### Management Commands

```bash
# List all registries and implementations
python manage.py list_registries
python manage.py list_registries --format json

# Clear registry caches
python manage.py clear_registries_cache

# Re-initialize registries
python manage.py initialize_registries
```

## Configuration

```python
# settings.py
DJANGO_STRATAGEM = {
    "CACHE_TIMEOUT": 300,            # Cache TTL in seconds (default: 300)
    "SKIP_DURING_MIGRATIONS": True,  # Skip registry ops during migrations (default: True)
    "ENABLED_PLUGINS": None,         # List of enabled plugin names, or None for all
    "DISABLED_PLUGINS": [],          # List of disabled plugin names
}
```

## License

MIT

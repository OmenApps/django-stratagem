# Architecture and Design

This page covers how django-stratagem works internally and why it was designed this way.

## Architecture Overview

django-stratagem uses Python metaclasses and `__init_subclass__` to build a registration system that requires no manual wiring:

1. **Metaclass-based registry** - `RegistryMeta` enables `in`, `iter`, and `len` on Registry classes directly (e.g., `EmailNotification in NotificationRegistry`).
2. **Auto-registration via `__init_subclass__`** - When you define a class that subclasses `Interface` with both `registry` and `slug` set, Python's `__init_subclass__` hook fires and calls `Registry.register()` automatically.
3. **Fully qualified name (FQN) storage** - Model fields store FQNs (e.g., `"myapp.notifications.EmailNotification"`) as plain `CharField` values. This avoids foreign keys, content types, or any schema coupling.
4. **Descriptor-based access** - Each field type has a paired descriptor that handles conversion between the stored string and the Python class or instance.

## The `register()` Decorator

As an alternative to auto-registration via `Interface.__init_subclass__`, you can use the `register()` decorator for explicit registration:

```python
from django_stratagem import register

@register(NotificationRegistry)
class WebhookNotification:
    slug = "webhook"
    description = "Send via webhook"

    def send(self, message, recipient):
        ...
```

Use this when you don't want to subclass `Interface` or when registering third-party classes.

## How Auto-Discovery Works

The following diagram shows the startup lifecycle:

```{mermaid}
flowchart TD
    A[Django starts] --> B[AppConfig.ready]
    B --> C{Running migrations?}
    C -->|Yes| D[Skip all registry ops]
    C -->|No| E[discover_registries]
    E --> F[autodiscover_modules 'registry']
    F --> G[For each registry in django_stratagem_registry]
    G --> H[clear_cache]
    H --> I[discover_implementations]
    I --> J[autodiscover_modules implementations_module]
    J --> K[Interface.__init_subclass__ triggers register]
    K --> L[PluginLoader.load_plugin_implementations]
    L --> M[Send registry_reloaded signal]
    M --> N[update_choices_fields]
    N --> O[Set model field choices from registry]
```

### Step by Step

The same sequence in detail:

1. **Django starts** - `DjangoStratagemAppConfig.ready()` is called.
2. **Migration check** - `is_running_migrations()` checks `sys.argv` for `migrate`/`makemigrations`. If running migrations, all registry operations are skipped to avoid import errors.
3. **`discover_registries()`** - Calls `autodiscover_modules("registry")`, then for each registry class in `django_stratagem_registry`:
   - Clears the cache
   - Calls `discover_implementations()`, which runs `autodiscover_modules(implementations_module)` to import implementation modules
   - When implementation modules are imported, `Interface.__init_subclass__` fires and calls `Registry.register()` for each subclass that has both `registry` and `slug` set
   - `PluginLoader.load_plugin_implementations()` loads any plugin-provided implementations
   - Sends the `registry_reloaded` signal
4. **`update_choices_fields()`** - For each registry, sets the `choices` attribute on any model fields registered via `choices_fields`.

## Migration Safety

The `is_running_migrations()` function in `utils.py` detects migration commands and caches the result for the process lifetime. The `skip_during_migrations` decorator and direct checks in `fields.py` and `apps.py` prevent:

- Auto-discovery from running during migrations
- Choice population from running during migrations
- Class imports in field descriptors from failing during migrations

## Design Decisions

### Why fully qualified names in the database?

Storing FQNs like `"myapp.notifications.EmailNotification"` as plain strings:

- **No schema coupling** - No foreign keys, content types, or extra tables. Adding or removing implementations never requires a migration.
- **Human-readable** - You can read the database value and immediately know what class it refers to.
- **Portable** - Values are self-contained strings that work across environments without needing matching database records.

The trade-off is that renaming or moving a class requires updating stored values. In practice, implementation classes are rarely renamed.

### Why autodiscovery?

Autodiscovery (importing modules matching `implementations_module` from all installed apps) follows the pattern established by Django's admin autodiscovery. It means:

- Adding a new implementation is one file, zero configuration
- No manual registration lists to maintain
- No settings to update

The `register()` decorator provides an opt-out for cases where autodiscovery doesn't fit.

### Why classmethods on Registry?

All registry operations (`get()`, `get_choices()`, `register()`, etc.) are classmethods rather than instance methods. This means you never need to instantiate a registry - you interact with it as a class:

```python
NotificationRegistry.get(slug="email")
NotificationRegistry.get_choices()
"email" in NotificationRegistry
```

A registry is a global, singleton-like container - there's exactly one `NotificationRegistry` for the application, so there's nothing to instantiate.

## Management Commands

Three management commands help you inspect and manage registries at runtime.

### list_registries

List all registered registries and their implementations.

```bash
python manage.py list_registries
python manage.py list_registries --format json
```

Shows: registry name, module, implementation count, slugs, classes, descriptions, priorities, conditions, and parent requirements.

### clear_registries_cache

Clear cache for all registries.

```bash
python manage.py clear_registries_cache
```

### initialize_registries

Re-discover and initialize all registries, then update model field choices.

```bash
python manage.py initialize_registries
python manage.py initialize_registries --force --clear-cache
python manage.py initialize_registries -v 2  # Show health checks
```

Options:
- `--force` - Force initialization even if already initialized
- `--clear-cache` - Clear all caches before initialization

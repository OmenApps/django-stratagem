# Extension Hooks and Customization Points

You can extend django-stratagem in several ways. This page covers hook methods, overridable methods, signals, and patterns for testing your extensions.

## Hook Methods Overview

The `Registry` class provides four hook methods that let you customize the registration lifecycle without replacing `register()` or `unregister()` entirely.

| Hook | Called by | When | Default behavior |
|---|---|---|---|
| `validate_implementation(implementation)` | `register()` | Before storage | Checks slug exists and interface subclass |
| `build_implementation_meta(implementation)` | `register()` | After validation | Returns `{klass, description, icon, priority}` |
| `on_register(slug, implementation, meta)` | `register()` | After storage, before signal | No-op |
| `on_unregister(slug, meta)` | `unregister()` | After removal, before signal | No-op |

All four are classmethods. Override them in your `Registry` subclass and call `super()` to preserve default behavior.

## validate_implementation

Called before an implementation is stored. Raise any exception to reject registration.

```python
from django_stratagem import Registry

class StrictNotificationRegistry(Registry):
    implementations_module = "notifications"

    @classmethod
    def validate_implementation(cls, implementation):
        # Preserve default slug + interface checks
        super().validate_implementation(implementation)

        # Require a send() method
        if not callable(getattr(implementation, "send", None)):
            raise TypeError(
                f"{implementation.__name__} must define a send() method"
            )
```

If `validate_implementation` raises, `register()` stops immediately - the implementation is not stored, `on_register` is not called, and no signal is emitted.

## build_implementation_meta

Called after validation. Returns the metadata dict that will be stored in `registry.implementations[slug]`. Override to add custom metadata fields.

```python
from datetime import datetime
from django_stratagem import Registry

class AuditableRegistry(Registry):
    implementations_module = "strategies"

    @classmethod
    def build_implementation_meta(cls, implementation):
        meta = super().build_implementation_meta(implementation)
        meta["version"] = getattr(implementation, "version", "0.0.0")
        meta["author"] = getattr(implementation, "author", "unknown")
        meta["registered_at"] = datetime.now().isoformat()
        return meta
```

The extra keys are stored alongside the standard `klass`, `description`, `icon`, and `priority` keys. They are available through `get_implementation_meta()` and are passed to `on_register` and `on_unregister`.

## on_register and on_unregister

Called after the implementation is stored (or removed) and cache is cleared, but before the Django signal is emitted. Use these for side effects like audit logging, metrics, or cache warming.

```python
import logging
from django_stratagem import Registry

logger = logging.getLogger(__name__)

class LoggingRegistry(Registry):
    implementations_module = "strategies"

    @classmethod
    def on_register(cls, slug, implementation, meta):
        logger.info(
            "Registered %s (priority=%d) in %s",
            slug, meta.get("priority", 0), cls.__name__,
        )

    @classmethod
    def on_unregister(cls, slug, meta):
        logger.info("Unregistered %s from %s", slug, cls.__name__)
```

## Execution Order

### register()

```
1. validate_implementation(implementation)  -- may raise
2. slug = implementation.slug
3. meta = build_implementation_meta(implementation)
4. implementations[slug] = meta
5. clear_cache()
6. on_register(slug, implementation, meta)
7. implementation_registered signal sent
```

### unregister()

```
1. Check slug exists (raises ImplementationNotFound if missing)
2. meta = implementations.pop(slug)
3. clear_cache()
4. on_unregister(slug, meta)
5. implementation_unregistered signal sent
```

## Overridable Methods

Beyond the four hooks, several Registry methods are designed for overriding:

`get_display_name(implementation)`
: Customize how implementations are labeled in choices, admin, and templates.

```python
class MyRegistry(Registry):
    implementations_module = "strategies"

    @classmethod
    def get_display_name(cls, implementation):
        icon = getattr(implementation, "icon", "")
        name = super().get_display_name(implementation)
        return f"{icon} {name}" if icon else name
```

`get_cache_key(suffix)`
: Customize cache key format (e.g. for multi-tenant isolation).

```python
class TenantRegistry(Registry):
    implementations_module = "strategies"

    @classmethod
    def get_cache_key(cls, suffix):
        from threading import current_thread
        tenant = getattr(current_thread(), "tenant_id", "default")
        return f"django_stratagem:{tenant}:{cls.__name__}:{suffix}"
```

`is_valid(value)`
: Customize what counts as a valid implementation reference.

## When to Use Hooks vs Signals

Use **hooks** when:

- You need to reject or modify registrations (validation, meta enrichment)
- The behavior is specific to one registry subclass
- You need guaranteed ordering relative to storage and cache clearing

Use **signals** when:

- Multiple unrelated listeners need to react to registrations
- The listener is defined outside the registry (e.g. a separate app)
- You want loose coupling between the registry and the reaction

## Signals

django-stratagem emits three Django signals:

### implementation_registered

Sent when an implementation is registered with a registry.

```python
from django.dispatch import receiver
from django_stratagem.signals import implementation_registered

@receiver(implementation_registered)
def on_registered(sender, registry, implementation, **kwargs):
    print(f"{implementation.slug} registered in {registry.__name__}")
```

- `sender` - The registry class
- `registry` - The registry class
- `implementation` - The implementation class

### implementation_unregistered

Sent when an implementation is unregistered.

```python
from django.dispatch import receiver
from django_stratagem.signals import implementation_unregistered

@receiver(implementation_unregistered)
def on_unregistered(sender, registry, slug, **kwargs):
    print(f"{slug} unregistered from {registry.__name__}")
```

- `sender` - The registry class
- `registry` - The registry class
- `slug` - The slug that was unregistered

### registry_reloaded

Sent when a registry is reloaded during `discover_registries()`.

```python
from django.dispatch import receiver
from django_stratagem.signals import registry_reloaded

@receiver(registry_reloaded)
def on_reloaded(sender, registry, **kwargs):
    print(f"{registry.__name__} reloaded")
```

- `sender` - The registry class
- `registry` - The registry class

## Signal Use Cases

### Invalidate External Caches on Registration

```python
from django.dispatch import receiver
from django_stratagem.signals import implementation_registered, implementation_unregistered

@receiver(implementation_registered)
@receiver(implementation_unregistered)
def invalidate_api_cache(sender, **kwargs):
    """Clear API response cache when implementations change."""
    from django.core.cache import cache
    cache.delete(f"api:registry:{sender.__name__}:choices")
```

### Audit Trail on Unregister

```python
from django.dispatch import receiver
from django_stratagem.signals import implementation_unregistered

@receiver(implementation_unregistered)
def log_unregistration(sender, registry, slug, **kwargs):
    from myapp.models import AuditLog
    AuditLog.objects.create(
        action="implementation_unregistered",
        registry=registry.__name__,
        slug=slug,
    )
```

### Warm Caches After Reload

```python
from django.dispatch import receiver
from django_stratagem.signals import registry_reloaded

@receiver(registry_reloaded)
def warm_caches(sender, registry, **kwargs):
    """Pre-populate choices and items caches after reload."""
    registry.get_choices()
    registry.get_items()
```

## Testing Extensions

### Temporary Registries

Create isolated registries in tests to avoid polluting the global state. The conftest `_clean_stratagem_registry` fixture (included by default) restores the global registry list after each test.

```python
from django_stratagem import Registry, Interface

def test_my_custom_validation():
    class TestRegistry(Registry):
        implementations_module = "test_impls"

        @classmethod
        def validate_implementation(cls, implementation):
            super().validate_implementation(implementation)
            if not hasattr(implementation, "process"):
                raise ValueError("Must define process()")

    TestRegistry.implementations = {}

    class Good(Interface):
        slug = "good"
        registry = None  # Don't auto-register

        def process(self):
            pass

    class Bad(Interface):
        slug = "bad"
        registry = None

    TestRegistry.register(Good)
    assert "good" in TestRegistry.implementations

    with pytest.raises(ValueError, match="process"):
        TestRegistry.register(Bad)
```

### Testing Hook Ordering

Verify that hooks run in the expected order relative to signals:

```python
def test_hook_runs_before_signal():
    call_order = []

    class OrderedRegistry(Registry):
        implementations_module = "ordered_impls"

        @classmethod
        def on_register(cls, slug, implementation, meta):
            call_order.append("hook")

    def signal_handler(sender, **kwargs):
        call_order.append("signal")

    from django_stratagem.signals import implementation_registered
    implementation_registered.connect(signal_handler)

    OrderedRegistry.implementations = {}

    class Impl(Interface):
        slug = "test"
        registry = None

    try:
        OrderedRegistry.register(Impl)
        assert call_order == ["hook", "signal"]
    finally:
        implementation_registered.disconnect(signal_handler)
```

### Testing Custom Conditions

```python
from django_stratagem import Condition

class MinItemsCondition(Condition):
    def __init__(self, min_count):
        self.min_count = min_count

    def is_met(self, context):
        return context.get("item_count", 0) >= self.min_count

    def explain(self):
        return f"Requires at least {self.min_count} items"

def test_min_items_condition():
    cond = MinItemsCondition(5)
    assert not cond.is_met({"item_count": 3})
    assert cond.is_met({"item_count": 5})
    assert cond.is_met({"item_count": 10})

def test_condition_composition():
    cond = MinItemsCondition(5) & MinItemsCondition(10)
    assert not cond.is_met({"item_count": 7})
    assert cond.is_met({"item_count": 10})
```

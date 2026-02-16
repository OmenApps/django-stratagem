# How to Use Model Fields

django-stratagem provides model fields for storing references to registry implementations. Each field stores a fully qualified class name (FQN) like `"myapp.notifications.EmailNotification"` as a `CharField` value in the database.

## Field Types Summary

| Field | Stores | Returns on Access |
|---|---|---|
| `RegistryClassField` | Single FQN string | The class itself |
| `RegistryField` | Single FQN string | An instance (via factory) |
| `MultipleRegistryClassField` | Comma-separated FQNs | List of classes |
| `MultipleRegistryField` | Comma-separated FQNs | List of instances |
| `HierarchicalRegistryField` | Single FQN string | Instance with parent validation |
| `MultipleHierarchicalRegistryField` | Comma-separated FQNs | List of instances with parent validation |

## Common Parameters

All registry fields accept these parameters:

`registry`
: The `Registry` subclass this field is tied to. Required.

`import_error`
: Value or callable to use when a stored class can't be imported. If callable, receives `(original_value, exception)`. Default: `None`.

`max_length`
: Maximum CharField length. Default: `200`.

Plus all standard Django `Field` kwargs (`blank`, `null`, `default`, `verbose_name`, etc.).

## RegistryClassField

Stores a reference to an implementation class. Accessing the field returns the class.

```python
from django_stratagem import RegistryClassField

class MyModel(models.Model):
    strategy = RegistryClassField(registry=NotificationRegistry)
```

```python
obj = MyModel()
obj.strategy = EmailNotification       # Set by class
obj.strategy = "email"                  # Set by slug
obj.strategy = "myapp.notifications.EmailNotification"  # Set by FQN
obj.save()

obj.strategy  # Returns <class 'myapp.notifications.EmailNotification'>
```

:::{tip}
The convenience method `Registry.choices_field()` creates a `RegistryClassField` tied to the registry:

```python
strategy = NotificationRegistry.choices_field()
# Equivalent to: RegistryClassField(registry=NotificationRegistry)
```
:::

## RegistryField

Like `RegistryClassField`, but accessing the field returns an *instance* created by the `factory` callable.

```python
from django_stratagem import RegistryField

class MyModel(models.Model):
    strategy = RegistryField(
        registry=NotificationRegistry,
        factory=lambda klass, obj: klass(),  # default
    )
```

`factory`
: A callable `(klass, obj) -> instance` where `klass` is the implementation class and `obj` is the model instance. Default: `lambda klass, obj: klass()`.

```python
obj.strategy.send("Hello!", "user@example.com")  # Already an instance
```

:::{tip}
The convenience method `Registry.instance_field()` creates a `RegistryField`:

```python
strategy = NotificationRegistry.instance_field()
```
:::

## MultipleRegistryClassField

Stores references to multiple implementation classes as comma-separated FQNs.

```python
from django_stratagem import MultipleRegistryClassField

class MyModel(models.Model):
    strategies = MultipleRegistryClassField(registry=NotificationRegistry)
```

```python
obj.strategies = [EmailNotification, SMSNotification]
obj.save()

obj.strategies  # [<class 'EmailNotification'>, <class 'SMSNotification'>]
```

## MultipleRegistryField

Like `MultipleRegistryClassField`, but returns instances.

```python
from django_stratagem import MultipleRegistryField

class MyModel(models.Model):
    strategies = MultipleRegistryField(
        registry=NotificationRegistry,
        factory=lambda klass, obj: klass(),
    )
```

```python
for strategy in obj.strategies:
    strategy.send("Hello!", "user@example.com")
```

## HierarchicalRegistryField

A registry field that depends on a parent registry field selection. Used with `HierarchicalRegistry`.

```python
from django_stratagem import HierarchicalRegistryField

class MyModel(models.Model):
    category = NotificationRegistry.choices_field()
    subcategory = HierarchicalRegistryField(
        registry=SubcategoryRegistry,
        parent_field="category",
    )
```

`parent_field`
: Name of the model field that holds the parent selection. Validation ensures the child selection is valid for the chosen parent.

## MultipleHierarchicalRegistryField

Multiple selection version of `HierarchicalRegistryField`.

```python
from django_stratagem import MultipleHierarchicalRegistryField

class MyModel(models.Model):
    category = NotificationRegistry.choices_field()
    subcategories = MultipleHierarchicalRegistryField(
        registry=SubcategoryRegistry,
        parent_field="category",
    )
```

## Slug Resolution

All field descriptors resolve values using this order:

1. Check if the value is a slug in `registry.implementations`
2. Fall back to importing as a fully qualified name via `import_by_name()`

This means you can set fields using either slugs or FQNs.

## Querying with Lookups

Registry fields register custom lookups that automatically convert classes and instances to their FQN strings for database queries.

```python
# Filter by class
MyModel.objects.filter(strategy=EmailNotification)

# Filter by slug string
MyModel.objects.filter(strategy="email")

# Filter with __in lookup (accepts classes)
MyModel.objects.filter(strategy__in=[EmailNotification, SMSNotification])

# Contains lookup (for multiple fields)
MyModel.objects.filter(strategies__contains=EmailNotification)
```

Supported lookups: `exact`, `iexact`, `contains`, `icontains`, `in`.

## Advanced Factory Patterns

The `factory` parameter on `RegistryField` controls how instances are created when accessing the field. The default is `lambda klass, obj: klass()`, but you can inject model data, dependencies, or configuration.

### Injecting Model Instance Data

```python
class Notification(models.Model):
    channel = RegistryField(
        registry=NotificationRegistry,
        factory=lambda klass, obj: klass(
            sender=obj.sender_email,
            template=obj.template_name,
        ),
    )
    sender_email = models.EmailField()
    template_name = models.CharField(max_length=100)
```

### Dependency Injection

```python
def create_with_dependencies(klass, obj):
    """Inject services from a container."""
    from myapp.services import get_service_container
    container = get_service_container()
    return klass(
        http_client=container.http_client,
        cache=container.cache,
    )

class MyModel(models.Model):
    strategy = RegistryField(
        registry=MyRegistry,
        factory=create_with_dependencies,
    )
```

### Singleton Pattern

```python
_instance_cache = {}

def singleton_factory(klass, obj):
    if klass not in _instance_cache:
        _instance_cache[klass] = klass()
    return _instance_cache[klass]

class MyModel(models.Model):
    strategy = RegistryField(
        registry=MyRegistry,
        factory=singleton_factory,
    )
```

## Validators

### ClassnameValidator

Validates that a string value is a valid, importable Python class name.

```python
from django_stratagem import ClassnameValidator

validator = ClassnameValidator(None)
validator("myapp.notifications.EmailNotification")  # OK
validator("invalid")  # Raises ValidationError
```

### RegistryValidator

Validates that a value is registered in a specific registry.

```python
from django_stratagem import RegistryValidator

validator = RegistryValidator(NotificationRegistry)
validator("email")  # OK if registered
validator("unknown")  # Raises ValidationError
```

Supports both single values and lists. Both validators are automatically added to registry model fields.

## System Checks

django-stratagem registers system checks under the `django_stratagem` tag:

| ID | Level | Description |
|---|---|---|
| `E001` | Error | Registry has invalid `implementations_module` |
| `E002` | Error | Model field has invalid `registry` (not a Registry subclass) |
| `W001` | Warning | Hierarchical registry references parent not in global registry |
| `W002` | Warning | Model field references registry not in global registry |

Run checks with:

```bash
python manage.py check --tag django_stratagem
```

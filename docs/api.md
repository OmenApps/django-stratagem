# API Reference

Full reference for the public API. For narrative documentation and examples, see the [quickstart](quickstart.md) and [how-to guides](howto-fields.md).

## `django_stratagem.registry`

### `Registry`

```python
class Registry(Generic[TInterface], metaclass=RegistryMeta)
```

Base class to define and manage registries of Interface implementations.

**Class Attributes:**

- `implementations_module: str` - Name of the module to autodiscover for implementations.
- `implementations: dict[str, ImplementationMeta]` - Map of slug to implementation metadata. Populated automatically.
- `choices_fields: list[tuple[str, type[Model]]]` - List of (field_name, model_class) tuples for fields whose choices should be updated from this registry.
- `label_attribute: str | None` - Optional attribute name to use for display labels instead of the class name.
- `interface_class: type[TInterface] | None` - Optional interface class to validate implementations against.

**Class Methods:**

- `register(implementation)` - Register an implementation class. Calls hooks and emits `implementation_registered` signal.
- `unregister(slug)` - Unregister by slug. Calls hooks and emits `implementation_unregistered` signal. Raises `ImplementationNotFound` if not found.
- `discover_implementations()` - Autodiscover and load implementations from `implementations_module` and plugins.
- `get(*, slug=None, fully_qualified_name=None) -> TInterface` - Instantiate and return an implementation by slug or fully qualified name (FQN). Raises `ImplementationNotFound`.
- `get_or_default(*, slug=None, fully_qualified_name=None, default=None) -> TInterface | None` - Like `get()` but returns `None` or a default on failure.
- `get_class(*, slug=None, fully_qualified_name=None) -> type[TInterface]` - Return the class without instantiating.
- `get_implementation_class(slug) -> type[TInterface]` - Get implementation class by slug.
- `get_implementation_meta(slug) -> ImplementationMeta` - Get full metadata for an implementation.
- `get_choices() -> list[tuple[str, str]]` - Return cached (slug, label) pairs sorted by priority.
- `get_display_name(implementation) -> str` - Human-readable label for an implementation.
- `get_items() -> list[tuple[str, type[TInterface]]]` - Cached list of (slug, class) pairs.
- `get_available_implementations(context=None) -> dict[str, type[TInterface]]` - Implementations available in context.
- `get_choices_for_context(context=None) -> list[tuple[str, str]]` - Choices filtered by context.
- `get_for_context(context=None, *, slug=None, fully_qualified_name=None, fallback=None) -> TInterface` - Get implementation with context check and fallback.
- `is_valid(value) -> bool` - Check if value (string, class, or instance) is a registered implementation.
- `contains(item) -> bool` - Alias for `is_valid()`.
- `iter_implementations()` - Iterator over implementation metadata dicts.
- `count_implementations() -> int` - Number of implementations.
- `choices_field(*args, **kwargs) -> AbstractRegistryField` - Factory for `RegistryClassField` tied to this registry.
- `instance_field(*args, **kwargs) -> AbstractRegistryField` - Factory for `RegistryField` tied to this registry.
- `clear_cache()` - Evict this registry's cache entries.
- `clear_all_cache()` - Static method. Evict cache for all registries.
- `check_health() -> dict[str, object]` - Basic health metrics (`count`, `last_updated`).
- `get_cache_key(suffix) -> str` - Construct cache key string.

**Extension Hooks:**

Override these classmethods to customize the registration lifecycle. See [Extension Hooks and Customization Points](hooks.md) for examples and patterns.

- `validate_implementation(implementation)` - Called by `register()` before storage. Raise to reject. Default checks slug and interface subclass.
- `build_implementation_meta(implementation) -> dict[str, Any]` - Called by `register()` after validation. Returns metadata dict. Default returns `{klass, description, icon, priority}`. Override to add custom keys.
- `on_register(slug, implementation, meta)` - Called after storage and cache clear, before signal. Default: no-op.
- `on_unregister(slug, meta)` - Called after removal and cache clear, before signal. Default: no-op. Receives the popped metadata dict.

**Metaclass Behavior (`RegistryMeta`):**

- `"slug" in MyRegistry` - Check if slug is valid via `is_valid()`.
- `for impl in MyRegistry` - Iterate over implementation classes.
- `len(MyRegistry)` - Number of implementations.

### `HierarchicalRegistry`

```python
class HierarchicalRegistry(Registry)
```

Registry that supports parent-child relationships.

**Additional Class Attributes:**

- `parent_registry: type[Registry] | None` - The parent registry class.
- `parent_slugs: list[str] | None` - Restrict to specific parent slugs.

**Additional Class Methods:**

- `get_parent_registry() -> type[Registry] | None`
- `get_children_for_parent(parent_slug, context=None) -> dict[str, type[Interface]]`
- `get_choices_for_parent(parent_slug, context=None) -> list[tuple[str, str]]`
- `validate_parent_child_relationship(parent_slug, child_slug) -> bool`
- `get_hierarchy_map() -> dict[str, list[str]]` - Cached map of parent slugs to child slugs.

### `RegistryRelationship`

```python
class RegistryRelationship
```

Manages relationships between parent and child registries.

**Class Methods:**

- `register_child(parent_registry, child_registry)` - Register a parent-child relationship.
- `get_children_registries(parent_registry) -> list[type[Registry]]`
- `get_all_descendants(registry) -> list[type[Registry]]` - Recursive.
- `clear_relationships()` - Clear all relationships.

### `ImplementationMeta`

```python
class ImplementationMeta(TypedDict)
```

- `klass: type[Any] | None` - The implementation class.
- `description: str`
- `icon: str`
- `priority: int`

### Functions

- `discover_registries()` - Re-run auto-discovery for all registries, clearing caches first. Called during app startup; you rarely need to call this directly.
- `update_choices_fields()` - Set model fields' choices from each registry.
- `register(registry_cls) -> Callable` - Decorator for explicit registration.

### Module-Level

- `django_stratagem_registry: list[type[Registry]]` - Global list of all registry classes.

---

## `django_stratagem.interfaces`

### `Interface`

```python
class Interface
```

Base class for implementation interfaces. Auto-registers subclasses that have both `registry` and `slug` set.

**Class Attributes:**

- `slug: str` - Unique identifier within the registry.
- `registry: type[Registry] | None` - Registry to register with.
- `description: str` - Human-readable description. Default: `""`.
- `icon: str` - Icon URL or identifier. Default: `""`.
- `priority: int` - Sort order (lower = higher priority). Default: `0`.

### `HierarchicalInterface`

```python
class HierarchicalInterface(Interface)
```

**Additional Class Attributes:**

- `parent_slug: str | None` - Single parent slug requirement.
- `parent_slugs: list[str] | None` - Multiple parent slug requirements.

**Class Methods:**

- `is_valid_for_parent(parent_slug) -> bool`

### `ConditionalInterface`

```python
class ConditionalInterface(Interface)
```

**Additional Class Attributes:**

- `condition: Condition | None` - Condition for availability.

**Class Methods:**

- `is_available(context=None) -> bool`

---

## `django_stratagem.conditions`

### `Condition`

```python
class Condition(ABC)
```

Abstract base class for conditions. Subclass this and implement `is_met(context)` to create custom conditions.

- `is_met(context: dict) -> bool` - Abstract. Check if condition is met.
- `explain() -> str` - Human-readable description.
- `check_with_details(context) -> tuple[bool, str]` - Result with explanation.
- `__and__(other) -> AllConditions`
- `__or__(other) -> AnyCondition`
- `__invert__() -> NotCondition`

### `CompoundCondition`

```python
class CompoundCondition(Condition)
```

Base class for compound conditions.

- `__init__(conditions: list[Condition])`

### `AllConditions`

```python
class AllConditions(CompoundCondition)
```

All conditions must be met (AND logic).

### `AnyCondition`

```python
class AnyCondition(CompoundCondition)
```

At least one condition must be met (OR logic).

### `NotCondition`

```python
class NotCondition(Condition)
```

Negates a condition.

- `__init__(condition: Condition)`

### `FeatureFlagCondition`

```python
class FeatureFlagCondition(Condition)
```

- `__init__(flag_name: str)` - Checks `settings.FEATURE_FLAGS[flag_name]` or `waffle.flag_is_active()`.

### `PermissionCondition`

```python
class PermissionCondition(Condition)
```

- `__init__(permission: str)` - Checks `user.has_perm(permission)` from `context["user"]`.

### `SettingCondition`

```python
class SettingCondition(Condition)
```

- `__init__(setting_name: str, expected_value: Any)` - Checks `getattr(settings, setting_name) == expected_value`.

### `CallableCondition`

```python
class CallableCondition(Condition)
```

- `__init__(check_func: Callable[[dict], bool])` - Wraps any callable.

### `AuthenticatedCondition`

```python
class AuthenticatedCondition(Condition)
```

No arguments. Checks `context["user"].is_authenticated`. Returns `False` if user is missing or lacks the attribute.

### `StaffCondition`

```python
class StaffCondition(Condition)
```

No arguments. Checks `context["user"].is_staff`. Returns `False` if user is missing or lacks the attribute.

### `SuperuserCondition`

```python
class SuperuserCondition(Condition)
```

No arguments. Checks `context["user"].is_superuser`. Returns `False` if user is missing or lacks the attribute.

### `GroupCondition`

```python
class GroupCondition(Condition)
```

- `__init__(group_name: str)` - Checks `context["user"].groups.filter(name=group_name).exists()`. Returns `False` if user is missing or has no `groups` attribute.

### `TimeWindowCondition`

```python
class TimeWindowCondition(Condition)
```

- `__init__(start_time: datetime.time, end_time: datetime.time, days: list[int] | None = None)` - Checks if current local time is within the window. Handles overnight windows (start > end). `days` uses Python weekday convention (0=Monday, 6=Sunday); `None` means every day.

### `DateRangeCondition`

```python
class DateRangeCondition(Condition)
```

- `__init__(start_date: datetime.date | None = None, end_date: datetime.date | None = None)` - Checks if current local date is within the range (inclusive). `None` means no bound on that side.

### `EnvironmentCondition`

```python
class EnvironmentCondition(Condition)
```

- `__init__(env_var: str, expected_value: str | None = None)` - If `expected_value` is `None`, checks that the env var exists and is non-empty. Otherwise checks for exact string match.

---

## `django_stratagem.fields`

### `AbstractRegistryField`

```python
class AbstractRegistryField(Field)
```

Base class for all registry model fields. Internal type: `CharField`.

- `__init__(*args, import_error=None, max_length=200, registry=None, **kwargs)`
- `contribute_to_class(cls, name, private_only=False)` - Sets up the descriptor.
- `formfield(...)` - Returns `RegistryFormField` or `RegistryMultipleChoiceFormField`. Pass `show_description=True` to use `RegistryDescriptionWidget` automatically.
- `choices` - Property that returns `registry.get_choices()`.

### `RegistryClassField`

```python
class RegistryClassField(AbstractRegistryField)
```

Returns the implementation class on access. Descriptor: `RegistryClassFieldDescriptor`.

### `RegistryField`

```python
class RegistryField(RegistryClassField)
```

Returns an implementation instance on access. Descriptor: `RegistryFieldDescriptor`.

- `__init__(*args, factory=lambda klass, obj: klass(), **kwargs)`

### `MultipleRegistryClassField`

```python
class MultipleRegistryClassField(AbstractRegistryField)
```

Stores comma-separated FQNs. Returns list of classes. Descriptor: `MultipleRegistryClassFieldDescriptor`.

### `MultipleRegistryField`

```python
class MultipleRegistryField(MultipleRegistryClassField)
```

Returns list of instances. Descriptor: `MultipleRegistryFieldDescriptor`.

- `__init__(*args, factory=lambda klass, obj: klass(), **kwargs)`

### `HierarchicalRegistryField`

```python
class HierarchicalRegistryField(RegistryField)
```

- `__init__(*args, parent_field=None, **kwargs)`
- `get_parent_value(obj) -> str | None`
- `validate(value, model_instance)` - Validates parent-child relationship.

### `MultipleHierarchicalRegistryField`

```python
class MultipleHierarchicalRegistryField(MultipleRegistryField)
```

- `__init__(*args, parent_field=None, **kwargs)`

### Descriptors

- `RegistryClassFieldDescriptor` - `__get__` returns class, `__set__` accepts class/slug/FQN.
- `RegistryFieldDescriptor` - `__get__` returns instance via `factory(klass, obj)`.
- `MultipleRegistryClassFieldDescriptor` - `__get__` returns list of classes.
- `MultipleRegistryFieldDescriptor` - `__get__` returns list of instances.
- `HierarchicalRegistryFieldDescriptor` - Adds parent-child validation on `__set__`.

---

## `django_stratagem.forms`

### `RegistryFormField`

```python
class RegistryFormField(ChoiceField)
```

- `__init__(*args, registry, empty_value="", **kwargs)`
- `clean(value) -> type` - Returns the implementation class.

### `RegistryMultipleChoiceFormField`

```python
class RegistryMultipleChoiceFormField(TypedMultipleChoiceField)
```

- `__init__(*args, registry, **kwargs)`
- `coerce(value) -> type | None`

### `ContextAwareRegistryFormField`

```python
class ContextAwareRegistryFormField(RegistryFormField)
```

- `__init__(*args, context=None, **kwargs)`
- `set_context(context)` - Update context and refresh choices.

### `HierarchicalRegistryFormField`

```python
class HierarchicalRegistryFormField(ContextAwareRegistryFormField)
```

- `__init__(*args, parent_field=None, parent_value=None, **kwargs)`
- `set_parent_value(parent_value)` - Update parent and refresh choices.

### `RegistryContextMixin`

```python
class RegistryContextMixin(BaseForm)
```

- `__init__(*args, registry_context=None, **kwargs)` - Passes context to all `ContextAwareRegistryFormField` fields.

### `HierarchicalFormMixin`

```python
class HierarchicalFormMixin(BaseForm)
```

Sets up parent-child relationships and validates them in `clean()`.

---

## `django_stratagem.widgets`

### `RegistryWidget`

```python
class RegistryWidget(forms.Select)
```

- `__init__(attrs=None, choices=(), registry=None)`
- Adds `title`, `data-description`, `data-icon`, `data-priority` attributes to options.

### `RegistryDescriptionWidget`

```python
class RegistryDescriptionWidget(RegistryWidget)
```

- `__init__(attrs=None, choices=(), registry=None, description_attrs=None)`
- Renders the select element plus a `<div>` container that displays the selected option's description.
- `description_attrs` - dict of HTML attributes applied to the container (e.g. `{"class": "alert alert-info"}`).
- Includes `Media.js` referencing `django_stratagem/js/registry_description.js`.
- The container carries `aria-live="polite"` for screen readers.
- Works with HTMX - reinitialises after `htmx:afterSettle`.

### `HierarchicalRegistryWidget`

```python
class HierarchicalRegistryWidget(forms.Select)
```

- `__init__(attrs=None, choices=(), parent_field=None)`
- Adds `data-parent-field` and `data-hierarchical` attributes.

---

## `django_stratagem.admin`

### `RegistryFieldListFilter`

```python
class RegistryFieldListFilter(ChoicesFieldListFilter)
```

Context-aware admin list filter for registry fields. Auto-registered for all `AbstractRegistryField` instances.

### `ContextAwareRegistryAdmin`

```python
class ContextAwareRegistryAdmin(admin.ModelAdmin)
```

Injects request context into registry form fields.

### `RegistryListMixin`

```python
class RegistryListMixin(admin.ModelAdmin)
```

Adds registry fields to `list_display` and `list_filter`.

### `HierarchicalRegistryAdmin`

```python
class HierarchicalRegistryAdmin(ContextAwareRegistryAdmin)
```

Adds hierarchical field support with data attributes for JavaScript.

### `DjangoStratagemAdminSite`

```python
class DjangoStratagemAdminSite(AdminSite)
```

Admin site with registry dashboard at `/admin/registry-dashboard/`.

### `EnhancedDjangoStratagemAdminSite`

```python
class EnhancedDjangoStratagemAdminSite(DjangoStratagemAdminSite)
```

Enhanced dashboard with hierarchy visualization at `/admin/enhanced-registry-dashboard/`.

---

## `django_stratagem.plugins`

### `PluginProtocol`

```python
class PluginProtocol(Protocol)
```

- `name: str`
- `version: str`
- `registry: str`
- `implementations: list[str]`
- `enabled: bool`

### `PluginInfo`

```python
@dataclass
class PluginInfo
```

Concrete implementation of `PluginProtocol`.

### `PluginLoader`

```python
class PluginLoader
```

- `ENTRY_POINT_GROUP = "django_stratagem.plugins"`
- `discover_plugins() -> list[PluginProtocol]`
- `load_plugin_implementations(registry_cls)` - Load plugin implementations for a specific registry.

---

## `django_stratagem.drf.serializers`

### `DrfRegistryField`

```python
class DrfRegistryField(serializers.ChoiceField)
```

- `__init__(registry, representation="slug", **kwargs)`
- `to_representation(value) -> str` - Slug or FQN.
- `to_internal_value(data) -> type` - Returns the implementation class.

### `DrfMultipleRegistryField`

```python
class DrfMultipleRegistryField(serializers.MultipleChoiceField)
```

- `__init__(registry, **kwargs)`
- `to_representation(value) -> list[str]`
- `to_internal_value(data) -> list[type]`

### Aliases

- `DrfStrategyField = DrfRegistryField`
- `DrfMultipleStrategyField = DrfMultipleRegistryField`

---

## `django_stratagem.drf.views`

### `RegistryChoicesAPIView`

```python
class RegistryChoicesAPIView(View)
```

JSON endpoint: `GET ?registry=Name&parent=slug`

### `RegistryHierarchyAPIView`

```python
class RegistryHierarchyAPIView(View)
```

JSON endpoint: `GET` returns hierarchy maps for all hierarchical registries.

---

## `django_stratagem.signals`

```python
implementation_registered = Signal()   # kwargs: registry, implementation
implementation_unregistered = Signal() # kwargs: registry, slug
registry_reloaded = Signal()           # kwargs: registry
```

---

## `django_stratagem.exceptions`

### `ImplementationNotFound`

```python
class ImplementationNotFound(KeyError)
```

### `RegistryNameError`

```python
class RegistryNameError(ValueError)
```

- `__init__(name: str, message: str | None = None)`

### `RegistryClassError`

```python
class RegistryClassError(ValueError)
```

- `__init__(name: str, message: str | None = None)`

### `RegistryImportError`

```python
class RegistryImportError(ImportError)
```

### `RegistryAttributeError`

```python
class RegistryAttributeError(AttributeError)
```

- `__init__(name: str, module_path: str, class_str: str, message: str | None = None)`

---

## `django_stratagem.validators`

### `ClassnameValidator`

```python
@deconstructible
class ClassnameValidator(BaseValidator)
```

Validates that a value is a valid, importable class name.

### `RegistryValidator`

```python
@deconstructible
class RegistryValidator(ClassnameValidator)
```

- `__init__(registry: type[Registry], message: str | None = None)`

Validates that a value is registered in a specific registry. Supports single values and lists.

---

## `django_stratagem.utils`

### `is_running_migrations() -> bool`

Check if Django is running `migrate` or `makemigrations`. Result is cached for the process lifetime.

### `import_by_name(name: str) -> Any`

Dynamically load and cache a class by its dotted path. Raises `RegistryNameError` if no dot in name. Raises `RegistryAttributeError` if attribute not found.

### `get_class(value: str | type | None) -> Any`

Get a class from a string reference, return a class as-is, or return the type of an instance.

### `get_fully_qualified_name(obj: Any) -> str`

Returns the fully qualified name (`module.ClassName`) of a class or instance.

### `get_display_string(klass: type, display_attribute: str | None = None) -> str`

Get a human-readable display string for a class, using `display_attribute` if provided, otherwise converting CamelCase to Title Case.

### `camel_to_title(text: str) -> str`

Convert CamelCase to Title Case. Handles consecutive capitals (e.g., `HTTPServer` -> `HTTP Server`).

### `stringify(values: Sequence[Any]) -> str`

Convert a sequence to a sorted, comma-separated string of FQNs.

### `get_attr(obj, attr, default=None)`

Recursively get an attribute using dot notation.

### `store_raw_name(obj, field_name, original)`

Store the FQN or `None` after an import attempt.

---

## `django_stratagem.app_settings`

```python
PROJECT_STRATAGEM = getattr(settings, "DJANGO_STRATAGEM", {})
PROJECT_SKIP_DURING_MIGRATIONS: bool  # Default: True
PROJECT_CACHE_TIMEOUT: int            # Default: 300 (5 minutes)
```

---

## `django_stratagem.lookups`

Custom lookups registered for `RegistryField`, `RegistryClassField`, `MultipleRegistryClassField`, and `MultipleRegistryField`:

- `RegistryFieldExact` - `exact` lookup with FQN conversion.
- `RegistryFieldIExact` - `iexact` lookup.
- `RegistryFieldContains` - `contains` lookup.
- `RegistryFieldIContains` - `icontains` lookup.
- `RegistryFieldIn` - `in` lookup that converts classes/instances to FQN strings.

---

## `django_stratagem.checks`

### `check_registries(app_configs, **kwargs)`

System check function registered under tag `django_stratagem`.

| ID | Level | Condition |
|---|---|---|
| `E001` | Error | Registry has empty/invalid `implementations_module` |
| `E002` | Error | Model field `registry` is not a Registry subclass |
| `W001` | Warning | Hierarchical registry parent not in global registry |
| `W002` | Warning | Field registry not in global registry |

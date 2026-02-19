# How to Use Forms, Widgets, and the Admin

Registry model fields produce appropriate form fields by default, but you can also use them directly or swap in context-aware and hierarchical variants.

## Form Fields

### RegistryFormField

A `ChoiceField` that presents registry implementations as choices and returns the selected class on clean.

```python
from django_stratagem import RegistryFormField

class MyForm(forms.Form):
    strategy = RegistryFormField(registry=NotificationRegistry)
```

### RegistryMultipleChoiceFormField

A `TypedMultipleChoiceField` for selecting multiple implementations.

```python
from django_stratagem import RegistryMultipleChoiceFormField

class MyForm(forms.Form):
    strategies = RegistryMultipleChoiceFormField(registry=NotificationRegistry)
```

### ContextAwareRegistryFormField

Limits the choices shown based on the current user's permissions, feature flags, or other runtime state (used with `ConditionalInterface`).

```python
from django_stratagem import ContextAwareRegistryFormField

class MyForm(forms.Form):
    strategy = ContextAwareRegistryFormField(
        registry=NotificationRegistry,
        context={"user": request.user, "request": request},
    )
```

Call `field.set_context(new_context)` to update the context and refresh choices.

### HierarchicalRegistryFormField

Shows only child options that are valid for the selected parent.

```python
from django_stratagem import HierarchicalRegistryFormField

class MyForm(forms.Form):
    category = RegistryFormField(registry=CategoryRegistry)
    subcategory = HierarchicalRegistryFormField(
        registry=SubcategoryRegistry,
        parent_field="category",
    )
```

Call `field.set_parent_value(value)` to update the parent and refresh choices.

## Form Mixins

### RegistryContextMixin

Mixin for forms that need to pass context to `ContextAwareRegistryFormField` fields.

```python
from django_stratagem import RegistryContextMixin

class MyForm(RegistryContextMixin, forms.Form):
    strategy = ContextAwareRegistryFormField(registry=NotificationRegistry)

# Usage:
form = MyForm(registry_context={"user": request.user})
```

### HierarchicalFormMixin

Mixin for forms with hierarchical registry fields. Automatically sets up parent-child relationships and validates them on clean.

```python
from django_stratagem import HierarchicalFormMixin

class MyForm(HierarchicalFormMixin, forms.ModelForm):
    class Meta:
        model = MyModel
        fields = ["category", "subcategory"]
```

## Widgets

### RegistryWidget

Enhanced `Select` widget that adds `title` (description), `data-description`, `data-icon`, and `data-priority` attributes to each `<option>` element.

```python
from django_stratagem import RegistryWidget

class MyForm(forms.Form):
    strategy = RegistryFormField(
        registry=NotificationRegistry,
        widget=RegistryWidget(registry=NotificationRegistry),
    )
```

### RegistryDescriptionWidget

Extends `RegistryWidget` to render a companion `<div>` below the `<select>` that shows the description of whichever option is currently selected. The description updates on change via a small bundled JS file - no AJAX calls, no extra views or URL patterns needed.

Each `<option>` already carries a `data-description` attribute (set by `RegistryWidget.create_option`). The JS reads that attribute and writes its text into the container. When no description is available the container is hidden entirely.

```python
from django_stratagem import RegistryDescriptionWidget

class MyForm(forms.Form):
    strategy = RegistryFormField(
        registry=NotificationRegistry,
        widget=RegistryDescriptionWidget(registry=NotificationRegistry),
    )
```

Pass `description_attrs` to control the container's HTML attributes:

```python
RegistryDescriptionWidget(
    registry=NotificationRegistry,
    description_attrs={"class": "alert alert-info", "style": "font-size: 0.9rem;"},
)
```

The container element looks like this in the rendered HTML:

```html
<div id="id_strategy-registry-description"
     class="registry-description-container alert alert-info"
     data-registry-description-for="id_strategy"
     style="font-size: 0.9rem;"
     aria-live="polite"
     aria-atomic="true">
  Selected option's description text here.
</div>
```

If the form is loaded inside an HTMX swap, the JS reinitialises automatically on `htmx:afterSettle`.

#### Using `show_description` on model fields

For model forms you can skip the manual widget assignment. Pass `show_description=True` when overriding `formfield()` and the field will pick `RegistryDescriptionWidget` on its own:

```python
class MyModelForm(forms.ModelForm):
    class Meta:
        model = MyModel
        fields = ["strategy"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override the field to get the description widget
        self.fields["strategy"] = MyModel._meta.get_field("strategy").formfield(
            show_description=True,
        )
```

If you pass an explicit `widget` kwarg alongside `show_description=True`, the explicit widget wins.

### HierarchicalRegistryWidget

A `Select` widget that emits `data-parent-field` and `data-hierarchical` attributes for JavaScript-driven dynamic updates.

```python
from django_stratagem import HierarchicalRegistryWidget

class MyForm(forms.Form):
    subcategory = HierarchicalRegistryFormField(
        registry=SubcategoryRegistry,
        parent_field="category",
        widget=HierarchicalRegistryWidget(parent_field="category"),
    )
```

## Customizing Form Fields

Subclass the built-in form fields to add custom filtering or behavior:

```python
from django_stratagem.forms import RegistryFormField

class FilteredRegistryFormField(RegistryFormField):
    """Only show implementations with priority < 100."""

    def __init__(self, *args, max_priority=100, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_priority = max_priority
        self._filter_choices()

    def _filter_choices(self):
        registry = self.registry
        filtered = [
            (slug, label)
            for slug, label in registry.get_choices()
            if registry.implementations.get(slug, {}).get("priority", 0) < self.max_priority
        ]
        self.choices = filtered
```

### Extending Form Mixins

```python
from django_stratagem.forms import RegistryContextMixin

class TenantRegistryForm(RegistryContextMixin, forms.ModelForm):
    """Automatically inject tenant from request."""

    def __init__(self, *args, request=None, **kwargs):
        context = {"user": request.user, "tenant": request.tenant} if request else {}
        super().__init__(*args, registry_context=context, **kwargs)
```

## Django Admin

### ContextAwareRegistryAdmin

A `ModelAdmin` that injects request context into registry form fields so that conditional implementations are filtered per-user.

```python
from django.contrib import admin
from django_stratagem.admin import ContextAwareRegistryAdmin

@admin.register(MyModel)
class MyModelAdmin(ContextAwareRegistryAdmin):
    pass
```

### HierarchicalRegistryAdmin

Extends `ContextAwareRegistryAdmin` with support for hierarchical registry fields. Adds `data-hierarchical`, `data-registry`, and `data-parent-field` widget attributes for JavaScript integration.

```python
from django_stratagem.admin import HierarchicalRegistryAdmin

@admin.register(MyModel)
class MyModelAdmin(HierarchicalRegistryAdmin):
    pass
```

Includes `Media` that references `admin/js/hierarchical_registry.js`.

### RegistryFieldListFilter

Admin list filter for registry fields. Automatically registered for all `AbstractRegistryField` instances, but can also be used explicitly:

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_filter = (("strategy", RegistryFieldListFilter),)
```

The filter is context-aware and only shows implementations available to the current user.

### RegistryListMixin

Mixin that automatically adds registry fields to `list_display` and `list_filter`.

## Customizing Admin Behavior

### Extending ContextAwareRegistryAdmin

```python
from django_stratagem.admin import ContextAwareRegistryAdmin

class MyModelAdmin(ContextAwareRegistryAdmin):
    def get_registry_context(self, request):
        """Build the context dict passed to conditional form fields."""
        return {
            "user": request.user,
            "request": request,
            "tenant": getattr(request, "tenant", None),
        }
```

### Adding Dashboard Actions

```python
from django_stratagem.admin import DjangoStratagemAdminSite

class CustomAdminSite(DjangoStratagemAdminSite):
    def get_urls(self):
        urls = super().get_urls()
        # Add custom registry management URLs
        return urls
```

## Dashboard Views

### DjangoStratagemAdminSite

An `AdminSite` subclass that adds a registry dashboard at `/admin/registry-dashboard/`. Shows all registries, their implementations, availability status, and conditions.

### EnhancedDjangoStratagemAdminSite

Extended dashboard at `/admin/enhanced-registry-dashboard/` with hierarchy visualization, parent requirements, and relationship information.

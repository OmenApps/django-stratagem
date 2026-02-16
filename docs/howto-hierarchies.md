# How to Use Hierarchical Registries

Define parent-child relationships between registries so that child choices depend on a parent selection.

## Defining Hierarchical Registries

```python
from django_stratagem import Registry, HierarchicalRegistry, Interface, HierarchicalInterface

class CategoryRegistry(Registry):
    implementations_module = "categories"

class SubcategoryRegistry(HierarchicalRegistry):
    implementations_module = "subcategories"
    parent_registry = CategoryRegistry

class Electronics(Interface):
    registry = CategoryRegistry
    slug = "electronics"

class Phones(HierarchicalInterface):
    registry = SubcategoryRegistry
    slug = "phones"
    parent_slug = "electronics"  # Only valid under electronics
```

## HierarchicalInterface

Extends `Interface` with parent validation:

`parent_slug`
: Single parent slug this implementation is valid for.

`parent_slugs`
: List of parent slugs this implementation is valid for.

If neither is set, the implementation is valid for all parents.

```python
class MultiParentChild(HierarchicalInterface):
    registry = SubcategoryRegistry
    slug = "accessories"
    parent_slugs = ["electronics", "clothing"]  # Valid under multiple parents

    @classmethod
    def is_valid_for_parent(cls, parent_slug: str) -> bool:
        # Automatically checks parent_slug / parent_slugs
        ...
```

## Key Methods

```python
# Get the parent registry
SubcategoryRegistry.get_parent_registry()  # CategoryRegistry

# Get children valid for a specific parent
children = SubcategoryRegistry.get_children_for_parent("electronics")
# {"phones": <class Phones>, ...}

# Get choices filtered by parent
choices = SubcategoryRegistry.get_choices_for_parent("electronics")
# [("phones", "Phones"), ...]

# Validate a parent-child relationship
SubcategoryRegistry.validate_parent_child_relationship("electronics", "phones")  # True

# Get the full hierarchy map
hierarchy = SubcategoryRegistry.get_hierarchy_map()
# {"electronics": ["phones", "tablets"], "clothing": ["shirts"]}
```

## RegistryRelationship

Manages the global parent-child relationship graph:

```python
from django_stratagem import RegistryRelationship

# Get child registries for a parent
children = RegistryRelationship.get_children_registries(CategoryRegistry)

# Get all descendants recursively
descendants = RegistryRelationship.get_all_descendants(CategoryRegistry)

# Clear all relationships (useful in tests)
RegistryRelationship.clear_relationships()
```

## Using in Models

Hierarchical registries work with `HierarchicalRegistryField` to enforce parent-child validation at the model level:

```python
from django_stratagem import HierarchicalRegistryField

class MyModel(models.Model):
    category = CategoryRegistry.choices_field()
    subcategory = HierarchicalRegistryField(
        registry=SubcategoryRegistry,
        parent_field="category",
    )
```

See [How to Use Model Fields](howto-fields.md#hierarchicalregistryfield) for details.

## Using in Forms

Use `HierarchicalRegistryFormField` and `HierarchicalFormMixin` to build forms with dependent dropdowns:

```python
from django_stratagem import HierarchicalRegistryFormField, HierarchicalFormMixin

class MyForm(HierarchicalFormMixin, forms.ModelForm):
    class Meta:
        model = MyModel
        fields = ["category", "subcategory"]
```

See [How to Use Forms, Widgets, and the Admin](howto-forms-admin.md) for details.

## Using in the Admin

`HierarchicalRegistryAdmin` handles hierarchical fields automatically with JavaScript-driven dynamic updates:

```python
from django_stratagem.admin import HierarchicalRegistryAdmin

@admin.register(MyModel)
class MyModelAdmin(HierarchicalRegistryAdmin):
    pass
```

See [How to Use Forms, Widgets, and the Admin](howto-forms-admin.md#hierarchicalregistryadmin) for details.

# How to Use DRF Integration

django-stratagem has optional Django REST Framework support for serializing registry choices in API endpoints.

## Installation

Install with DRF support:

```bash
pip install django-stratagem[drf]
```

## DrfRegistryField

A DRF `ChoiceField` for single registry selection. Accepts slugs or fully qualified names (FQNs) as input and returns the implementation class as internal value.

```python
from rest_framework import serializers
from django_stratagem.drf.serializers import DrfRegistryField

class NotificationSerializer(serializers.Serializer):
    strategy = DrfRegistryField(registry=NotificationRegistry)
```

Parameters:

`registry`
: The registry class. Required.

`representation`
: How to serialize values. `"slug"` (default) outputs the slug, otherwise outputs the FQN.

## DrfMultipleRegistryField

A DRF `MultipleChoiceField` for multiple registry selection.

```python
from django_stratagem.drf.serializers import DrfMultipleRegistryField

class NotificationSerializer(serializers.Serializer):
    strategies = DrfMultipleRegistryField(registry=NotificationRegistry)
```

## Backward Compatibility Aliases

- `DrfStrategyField` = `DrfRegistryField`
- `DrfMultipleStrategyField` = `DrfMultipleRegistryField`

## API Views

Two built-in views return registry data as JSON:

### RegistryChoicesAPIView

Returns choices for a registry, optionally filtered by parent.

```
GET /api/registry/choices/?registry=NotificationRegistry
GET /api/registry/choices/?registry=SubcategoryRegistry&parent=electronics
```

Response:

```json
{
    "choices": [["email", "Email Notification"], ["sms", "SMS Notification"]],
    "registry": "NotificationRegistry",
    "parent": null
}
```

### RegistryHierarchyAPIView

Returns hierarchy maps for all hierarchical registries.

```
GET /api/registry/hierarchy/
```

Response:

```json
{
    "hierarchies": {
        "SubcategoryRegistry": {
            "parent_registry": "CategoryRegistry",
            "hierarchy_map": {
                "electronics": ["phones", "tablets"],
                "clothing": ["shirts"]
            }
        }
    }
}
```

## URL Configuration

Include the DRF URLs in your `urlpatterns`:

```python
from django.urls import include, path

urlpatterns = [
    path("stratagem/", include("django_stratagem.drf.urls")),
]
```

This registers:
- `stratagem/api/registry/choices/` - `RegistryChoicesAPIView`
- `stratagem/api/registry/hierarchy/` - `RegistryHierarchyAPIView`

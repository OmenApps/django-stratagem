from django import forms


class RegistryWidget(forms.Select):
    """Enhanced Select widget for registry fields.

    Displays implementation descriptions and icons alongside choice labels.
    """

    def __init__(self, attrs=None, choices=(), registry=None):
        super().__init__(attrs, choices)
        self.registry = registry

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)

        if self.registry and value:
            meta = self.registry.implementations.get(value)
            if meta:
                if meta.get("description"):
                    option["attrs"]["title"] = meta["description"]
                if meta.get("icon"):
                    option["attrs"]["data-icon"] = meta["icon"]
                if meta.get("priority"):
                    option["attrs"]["data-priority"] = str(meta["priority"])

        return option


class HierarchicalRegistryWidget(forms.Select):
    """Widget that can dynamically update based on parent selection."""

    def __init__(self, attrs=None, choices=(), parent_field=None):
        super().__init__(attrs, choices)
        self.parent_field = parent_field

    def render(self, name, value, attrs=None, renderer=None):
        """Render with data attributes for JavaScript enhancement."""
        if attrs is None:
            attrs = {}

        # Add data attributes for JS to hook into
        if self.parent_field:
            attrs["data-parent-field"] = self.parent_field
            attrs["data-hierarchical"] = "true"

        return super().render(name, value, attrs, renderer)

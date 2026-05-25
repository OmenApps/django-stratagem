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
                    option["attrs"]["data-description"] = meta["description"]
                if meta.get("icon"):
                    option["attrs"]["data-icon"] = meta["icon"]
                if meta.get("priority"):
                    option["attrs"]["data-priority"] = str(meta["priority"])

        return option


class RegistryDescriptionWidget(RegistryWidget):
    """Select widget that displays the selected implementation's description.

    Dynamically renders a container below standard widget that shows a description of currently selected option.
    """

    template_name = "django_stratagem/widgets/registry_description_select.html"

    class Media:
        js = ("django_stratagem/js/registry_description.js",)

    def __init__(self, attrs=None, choices=(), registry=None, description_attrs=None):
        super().__init__(attrs, choices, registry=registry)
        self.description_attrs = description_attrs or {}

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["description_attrs"] = self.description_attrs

        # Associate the description container with the <select> so assistive
        # technology announces the description on focus, regardless of whether
        # the aria-live region has fired. The container id mirrors the template:
        # "{select_id}-registry-description". The container's visible content is
        # populated by registry_description.js (on load and on change); this
        # attribute makes that content programmatically associated with the
        # control. aria-describedby is a space-separated token list, so we merge
        # against any pre-existing value (e.g. form help text), collapsing
        # whitespace and avoiding a duplicate id.
        widget_id = context["widget"]["attrs"].get("id")
        if widget_id:
            description_id = f"{widget_id}-registry-description"
            tokens = context["widget"]["attrs"].get("aria-describedby", "").split()
            if description_id not in tokens:
                tokens.append(description_id)
            context["widget"]["attrs"]["aria-describedby"] = " ".join(tokens)
        return context


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

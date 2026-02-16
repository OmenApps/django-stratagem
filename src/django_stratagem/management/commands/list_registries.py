import json
from textwrap import indent

from django.core.management.base import BaseCommand

from django_stratagem.registry import HierarchicalRegistry, RegistryRelationship, django_stratagem_registry


class Command(BaseCommand):
    help = "Lists all registered registry classes with detailed info."

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)",
        )

    def handle(self, *args, **kwargs):
        output_format = kwargs.get("format", "text")

        if not django_stratagem_registry:
            if output_format == "json":
                self.stdout.write(json.dumps({"registries": []}))
            else:
                self.stdout.write(self.style.WARNING("No registries have been registered."))  # type: ignore[attr-defined]
            return

        if output_format == "json":
            self._handle_json()
        else:
            self._handle_text()

    def _get_registry_data(self, registry_cls):
        """Build structured data for a registry."""
        is_hierarchical = isinstance(registry_cls, type) and issubclass(registry_cls, HierarchicalRegistry)
        parent_registry = getattr(registry_cls, "parent_registry", None)
        children = RegistryRelationship.get_children_registries(registry_cls)

        implementations = []
        for slug, meta in registry_cls.implementations.items():
            impl_class = meta["klass"]
            impl_data = {
                "slug": slug,
                "class": impl_class.__name__ if impl_class else None,
                "module": impl_class.__module__ if impl_class else None,
                "description": meta.get("description", ""),
                "icon": meta.get("icon", ""),
                "priority": meta.get("priority", 0),
            }

            # Check for conditional availability
            if impl_class and hasattr(impl_class, "condition") and impl_class.condition is not None:
                impl_data["conditional"] = True
                impl_data["condition_type"] = type(impl_class.condition).__name__
            else:
                impl_data["conditional"] = False

            # Check for parent requirements (hierarchical interfaces)
            parent_slug = getattr(impl_class, "parent_slug", None) if impl_class else None
            parent_slugs = getattr(impl_class, "parent_slugs", None) if impl_class else None
            if parent_slug:
                impl_data["parent_slug"] = parent_slug
            if parent_slugs:
                impl_data["parent_slugs"] = parent_slugs

            implementations.append(impl_data)

        return {
            "name": registry_cls.__name__,
            "module": registry_cls.__module__,
            "doc": (registry_cls.__doc__ or "").strip().split("\n")[0],
            "implementations_module": getattr(registry_cls, "implementations_module", ""),
            "is_hierarchical": is_hierarchical,
            "parent_registry": parent_registry.__name__ if parent_registry else None,
            "children_registries": [c.__name__ for c in children],
            "implementation_count": len(implementations),
            "implementations": implementations,
        }

    def _handle_json(self):
        """Output in JSON format."""
        registries = []
        for registry_cls in django_stratagem_registry:
            registries.append(self._get_registry_data(registry_cls))
        self.stdout.write(json.dumps({"registries": registries}, indent=2))

    def _handle_text(self):
        """Output in human-readable text format."""
        for registry_cls in django_stratagem_registry:
            data = self._get_registry_data(registry_cls)

            # Registry header
            header = f"{data['name']} ({data['module']})"
            if data["is_hierarchical"]:
                header += " [hierarchical]"
            self.stdout.write(self.style.SUCCESS(header))  # type: ignore[attr-defined]

            if data["doc"]:
                self.stdout.write(indent(f"# {data['doc']}", "  "))

            if data["parent_registry"]:
                self.stdout.write(f"  Parent: {data['parent_registry']}")

            if data["children_registries"]:
                self.stdout.write(f"  Children: {', '.join(data['children_registries'])}")

            self.stdout.write(f"  Implementations ({data['implementation_count']}):")

            for impl in data["implementations"]:
                self.stdout.write(indent(f"\nClass: {impl['class']}", "      "))
                self.stdout.write(indent(f"Slug: {impl['slug']}", "          "))
                self.stdout.write(indent(f"Module: {impl['module']}", "          "))

                if impl["description"]:
                    self.stdout.write(indent(f"Description: {impl['description']}", "          "))

                if impl["icon"]:
                    self.stdout.write(indent(f"Icon: {impl['icon']}", "          "))

                if impl["priority"]:
                    self.stdout.write(indent(f"Priority: {impl['priority']}", "          "))

                if impl["conditional"]:
                    self.stdout.write(indent(f"Conditional: {impl['condition_type']}", "          "))

                if impl.get("parent_slug"):
                    self.stdout.write(indent(f"Parent slug: {impl['parent_slug']}", "          "))

                if impl.get("parent_slugs"):
                    self.stdout.write(indent(f"Parent slugs: {', '.join(impl['parent_slugs'])}", "          "))

            self.stdout.write("")

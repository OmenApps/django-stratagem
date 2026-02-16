from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.contrib.admin import AdminSite, ChoicesFieldListFilter, FieldListFilter
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import format_html
from django.utils.translation import gettext as _

from .fields import AbstractRegistryField, HierarchicalRegistryField
from .forms import ContextAwareRegistryFormField, HierarchicalRegistryFormField
from .registry import (
    HierarchicalRegistry,
    RegistryRelationship,
    django_stratagem_registry,
)

if TYPE_CHECKING:
    from django.contrib.admin.views.main import ChangeList


class RegistryFieldListFilter(ChoicesFieldListFilter):
    """Admin list filter for registry fields.

    Usage:

        class MyModelAdmin(admin.ModelAdmin):
            list_filter = (("field_name", RegistryFieldListFilter,),)
    """

    field: AbstractRegistryField

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        self.request = request

    def choices(self, changelist: ChangeList) -> Generator[dict[str, Any]]:
        """Generate choices for the filter based on request context."""
        registry = self.field.registry
        if registry is None:
            return

        # Build context for filtering
        context = {
            "request": self.request,
            "user": self.request.user,
        }

        yield {
            "selected": self.lookup_val is None,
            "query_string": changelist.get_query_string(remove=[self.lookup_kwarg, self.lookup_kwarg_isnull]),
            "display": _("All"),
        }

        # Get context-aware implementations
        available_implementations = registry.get_available_implementations(context)

        # Sort by display name
        sorted_impls = sorted(available_implementations.items(), key=lambda x: registry.get_display_name(x[1]))

        for slug, impl_class in sorted_impls:
            yield {
                "selected": self.lookup_val is not None and slug == self.lookup_val,
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg: slug},  # type: ignore
                    [self.lookup_kwarg_isnull],
                ),
                "display": registry.get_display_name(impl_class),
            }


class ContextAwareRegistryAdmin(admin.ModelAdmin):
    """ModelAdmin that provides context to registry fields."""

    def get_form(self, request, obj=None, change=False, **kwargs):
        """Get form with registry context injected."""
        form = super().get_form(request, obj, change, **kwargs)

        # Create a custom form class that injects context
        class ContextAwareForm(form):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                # Build context
                context = {
                    "request": request,
                    "user": request.user,
                    "obj": obj,
                    "change": change,
                }

                # Update registry fields with context
                for field_name, field in self.fields.items():
                    registry = getattr(field, "registry", None)
                    if registry and hasattr(registry, "get_choices_for_context"):
                        field.choices = registry.get_choices_for_context(context)

        return ContextAwareForm

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Customize form field for registry fields."""
        if isinstance(db_field, AbstractRegistryField):
            # Build context for the field
            context = {
                "request": request,
                "user": request.user if request else None,
            }

            # Use context-aware form field
            kwargs["form_class"] = ContextAwareRegistryFormField
            kwargs["context"] = context

        return super().formfield_for_dbfield(db_field, request, **kwargs)


class RegistryListMixin(admin.ModelAdmin):
    """Mixin to add registry fields to the admin list view."""

    def get_list_display(self, request):  # type: ignore[override]
        # append registry field display names
        return [*super().get_list_display(request), *(f.name for f in self.model._meta.get_fields())]

    def get_list_filter(self, request):  # type: ignore[override]
        # add registry fields to filters
        return [
            *super().get_list_filter(request),
            *(f.name for f in self.model._meta.fields if isinstance(f, AbstractRegistryField)),
        ]


class HierarchicalRegistryAdmin(ContextAwareRegistryAdmin):
    """Admin that handles hierarchical registry fields with dynamic updates."""

    class Media:
        js = ("admin/js/hierarchical_registry.js",)

    def get_form(self, request, obj=None, change=False, **kwargs):
        """Get form with hierarchical field support."""
        form = super().get_form(request, obj, change, **kwargs)

        # Wrap the form to add hierarchical support
        class HierarchicalAdminForm(form):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._setup_hierarchical_fields()

            def _setup_hierarchical_fields(self):
                """Configure hierarchical fields with parent relationships."""
                for field_name, field in self.fields.items():
                    if isinstance(field, HierarchicalRegistryFormField):
                        # Add widget attributes for JS
                        widget_attrs = getattr(field.widget, "attrs", None)
                        if widget_attrs is not None:
                            widget_attrs["data-hierarchical"] = "true"
                            if hasattr(field, "registry") and field.registry:
                                widget_attrs["data-registry"] = field.registry.__name__

                            if field.parent_field:
                                widget_attrs["data-parent-field"] = field.parent_field

                                # Set initial parent value if editing
                                if self.instance and hasattr(self.instance, field.parent_field):
                                    parent_value = getattr(self.instance, field.parent_field)
                                    if parent_value:
                                        field.set_parent_value(parent_value)

        return HierarchicalAdminForm

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """Customize form field for hierarchical registry fields."""
        if isinstance(db_field, HierarchicalRegistryField):
            # Add context for hierarchical field filtering
            context = {
                "request": request,
                "user": request.user if request else None,
            }
            kwargs["form_class"] = HierarchicalRegistryFormField
            kwargs["context"] = context
        return super().formfield_for_choice_field(db_field, request, **kwargs)


class DjangoStratagemAdminSite(AdminSite):
    """Admin view to display all registries and their implementations."""

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("registry-dashboard/", self.admin_view(self.registry_dashboard), name="registry-dashboard"),
        ]
        return custom + urls

    def registry_dashboard(self, request):
        # Build context for checking availability
        context = {
            "request": request,
            "user": request.user if request else None,
        }

        rows = []
        for reg in django_stratagem_registry:
            impls = []
            for slug, impl in reg.get_items():
                # Check availability
                is_available = True
                availability_reason = ""

                if hasattr(impl, "is_available"):
                    is_available = impl.is_available(context)
                    if not is_available and hasattr(impl, "condition"):
                        availability_reason = "Condition not met"

                icon = getattr(impl, "icon", "")
                impls.append(
                    {
                        "slug": slug,
                        "name": reg.get_display_name(impl),
                        "icon": format_html('<img src="{}" width="16" height="16"/>', icon) if icon else "",
                        "description": getattr(impl, "description", ""),
                        "is_available": is_available,
                        "availability_reason": availability_reason,
                        "condition": str(getattr(impl, "condition", None)) if hasattr(impl, "condition") else "",
                    }
                )
            rows.append(
                {
                    "registry": reg.__name__,
                    "implementations": impls,
                    "description": getattr(reg, "description", ""),
                }
            )

        return TemplateResponse(
            request,
            "admin/registries_dashboard.html",
            {
                "rows": rows,
                "title": "Registry Dashboard",
            },
        )


class EnhancedDjangoStratagemAdminSite(DjangoStratagemAdminSite):
    """Admin site with hierarchy visualization."""

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "enhanced-registry-dashboard/",
                self.admin_view(self.registry_dashboard),
                name="enhanced-registry-dashboard",
            ),
        ]
        return custom + urls

    def registry_dashboard(self, request):
        """Enhanced dashboard showing registry hierarchies."""
        context = {
            "request": request,
            "user": request.user if request is not None else None,
        }

        # Get relationships
        relationships = RegistryRelationship._relationships

        rows = []
        processed_registries = set()

        # Process parent registries first
        for reg in django_stratagem_registry:
            if reg in processed_registries:
                continue

            # Check if this is a parent registry
            children = RegistryRelationship.get_children_registries(reg)

            registry_info = self._get_registry_info(reg, context)
            registry_info["children"] = []

            # Add child registries
            for child in children:
                child_info = self._get_registry_info(child, context)
                registry_info["children"].append(child_info)
                processed_registries.add(child)

            rows.append(registry_info)
            processed_registries.add(reg)

        # Add any remaining registries (not in hierarchies)
        for reg in django_stratagem_registry:
            if reg not in processed_registries:
                rows.append(self._get_registry_info(reg, context))

        return TemplateResponse(
            request,
            "admin/registries_dashboard_hierarchical.html",
            {
                "rows": rows,
                "title": "Registry Dashboard",
                "relationships": relationships,
            },
        )

    def _get_registry_info(self, registry, context):
        """Get registry information for display."""
        impls = []
        for slug, impl in registry.get_items():
            is_available = True
            availability_reason = ""
            parent_requirements = []

            # Check availability
            if hasattr(impl, "is_available"):
                is_available = impl.is_available(context)
                if not is_available and hasattr(impl, "condition"):
                    availability_reason = "Condition not met"

            # Check parent requirements for hierarchical interfaces
            if hasattr(impl, "parent_slug") and impl.parent_slug:
                parent_requirements = [impl.parent_slug]
            elif hasattr(impl, "parent_slugs") and impl.parent_slugs:
                parent_requirements = impl.parent_slugs

            icon = getattr(impl, "icon", "")
            impls.append(
                {
                    "slug": slug,
                    "name": registry.get_display_name(impl),
                    "icon": format_html('<img src="{}" width="16" height="16"/>', icon) if icon else "",
                    "description": getattr(impl, "description", ""),
                    "is_available": is_available,
                    "availability_reason": availability_reason,
                    "parent_requirements": parent_requirements,
                }
            )

        return {
            "registry": registry.__name__,
            "implementations": impls,
            "description": getattr(registry, "description", ""),
            "is_hierarchical": isinstance(registry, type) and issubclass(registry, HierarchicalRegistry),
            "parent_registry": (
                registry.parent_registry.__name__
                if hasattr(registry, "parent_registry") and registry.parent_registry
                else None
            ),
        }


# Register the filter for all registry fields
FieldListFilter.register(lambda f: isinstance(f, AbstractRegistryField), RegistryFieldListFilter, take_priority=True)

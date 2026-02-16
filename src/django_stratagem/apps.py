from django.apps import AppConfig

from .utils import is_running_migrations


class DjangoStratagemAppConfig(AppConfig):
    """Configuration for the django_stratagem app."""

    default_auto_field = "django.db.models.BigAutoField"  # type: ignore[assignment]
    name = "django_stratagem"
    verbose_name = "Django Stratagem"

    def ready(self) -> None:
        """Automatically discover and register all registries, and update choices fields."""

        # Skip initialization during migrations
        if is_running_migrations():
            return

        # Import admin to register filters, and checks to register system checks
        from django_stratagem import admin, checks  # noqa: F401

        # Discover registries and update fields (no DB access needed)
        from .registry import discover_registries, update_choices_fields

        discover_registries()
        update_choices_fields()

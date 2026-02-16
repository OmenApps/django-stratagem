import logging

from django.core.management.base import BaseCommand

from django_stratagem import utils as stratagem_utils
from django_stratagem.registry import discover_registries, django_stratagem_registry, update_choices_fields

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Initialize all django_stratagem registries and update field choices"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force registry initialization even if already initialized",
        )
        parser.add_argument(
            "--clear-cache",
            action="store_true",
            help="Clear all registry caches before initialization",
        )

    def handle(self, *args, **options):
        self.stdout.write("Initializing django_stratagem registries...")

        if options["clear_cache"]:
            self.stdout.write("Clearing registry caches...")
            from django_stratagem.registry import Registry

            Registry.clear_all_cache()
            self.stdout.write(self.style.SUCCESS("Registry caches cleared"))  # type: ignore[attr-defined]

        # When --force is used, temporarily override migration detection
        force = options["force"]
        original_migrations_running = None
        if force:
            original_migrations_running = stratagem_utils._migrations_running
            stratagem_utils._migrations_running = False
        elif stratagem_utils.is_running_migrations():
            self.stderr.write(
                self.style.WARNING(  # type: ignore[attr-defined]
                    "Migration context detected. Use --force to override."
                )
            )

        try:
            # Discover and initialize registries
            discover_registries()
            self.stdout.write(self.style.SUCCESS("Registries discovered"))  # type: ignore[attr-defined]

            # Update model field choices
            update_choices_fields()
            self.stdout.write(self.style.SUCCESS("Field choices updated"))  # type: ignore[attr-defined]
        finally:
            if force:
                stratagem_utils._migrations_running = original_migrations_running

        # Report on initialized registries
        self.stdout.write("\nInitialized registries:")
        for registry_cls in django_stratagem_registry:
            impl_count = len(registry_cls.implementations)
            self.stdout.write(f"  - {registry_cls.__name__}: {self.style.SUCCESS(f'{impl_count} implementations')}")  # type: ignore[attr-defined]

            # Show health check if verbose
            if options["verbosity"] >= 2:
                health = registry_cls.check_health()
                self.stdout.write(f"    Health: {health}")

        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully initialized {len(django_stratagem_registry)} registries"))  # type: ignore[attr-defined]

from django.core.management.base import BaseCommand

from django_stratagem.registry import Registry


class Command(BaseCommand):
    help = "Clears cache for all registries."

    def handle(self, *args, **options):
        Registry.clear_all_cache()
        self.stdout.write(self.style.SUCCESS("All registry caches cleared."))  # type: ignore[attr-defined]

from django.apps import AppConfig


class PlatformCoreConfig(AppConfig):
    name = "platform_core"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import platform_core.signals  # noqa: F401

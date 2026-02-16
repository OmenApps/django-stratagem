from django.apps import AppConfig


class BillingAppConfig(AppConfig):
    name = "billing"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import billing.signals  # noqa: F401

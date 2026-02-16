from django.apps import AppConfig


class ComplianceCanadaConfig(AppConfig):
    name = "django_compliance_canada"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Import the implementations module so classes auto-register with ComplianceRegistry.
        # In a real installable package, you would use entry points instead:
        #
        #   [project.entry-points."django_stratagem.plugins"]
        #   compliance_canada = "django_compliance_canada.stratagem_plugin"
        #
        # For this example we import directly since the package is local.
        import django_compliance_canada.compliance_reports  # noqa: F401

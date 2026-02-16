# django_compliance_canada/stratagem_plugin.py
#
# Plugin metadata for django-stratagem's plugin system.
# In a real installable package, you would register this via entry points
# in pyproject.toml:
#
#   [project.entry-points."django_stratagem.plugins"]
#   compliance_canada = "django_compliance_canada.stratagem_plugin"

__version__ = "1.0.0"

REGISTRY = "ComplianceRegistry"

IMPLEMENTATIONS = [
    "django_compliance_canada.compliance_reports.CanadianOhsCompliance",
]

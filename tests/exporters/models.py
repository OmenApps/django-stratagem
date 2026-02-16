from django.db import models

from tests.exporters.registry import ExporterRegistry


class ExportConfig(models.Model):
    exporter_type = ExporterRegistry.choices_field(max_length=100)

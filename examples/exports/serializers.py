"""A DRF serializer exposing the export-format registry as a choice field."""

from rest_framework import serializers

from django_stratagem.drf.serializers import DrfRegistryField

from .registry import ExportFormatRegistry


class ExportRequestSerializer(serializers.Serializer):
    """Validates an export request: which format, and the row count."""

    format = DrfRegistryField(registry=ExportFormatRegistry)
    row_count = serializers.IntegerField(min_value=0, default=0)

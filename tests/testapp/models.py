"""Test models for registry field persistence."""

from django.db import models

from django_stratagem.fields import (
    MultipleRegistryClassField,
    MultipleRegistryField,
    RegistryClassField,
    RegistryField,
)
from tests.registries_fixtures import TestStrategyRegistry


class RegistryFieldTestModel(models.Model):
    """Test model for django_stratagem field tests.

    This model is used to test database persistence, lookups, and
    field behavior with actual database operations.
    """

    name = models.CharField(max_length=100, default="Test")

    # Single value fields
    single_instance = RegistryField(
        registry=TestStrategyRegistry,
        blank=True,
        null=True,
        help_text="Single implementation instance field",
    )
    single_class = RegistryClassField(
        registry=TestStrategyRegistry,
        blank=True,
        null=True,
        help_text="Single implementation class field",
    )

    # Multiple value fields
    multiple_instances = MultipleRegistryField(
        registry=TestStrategyRegistry,
        blank=True,
        help_text="Multiple implementation instances field",
    )
    multiple_classes = MultipleRegistryClassField(
        registry=TestStrategyRegistry,
        blank=True,
        help_text="Multiple implementation classes field",
    )

    class Meta:
        app_label = "testapp"
        verbose_name = "Registry Field Test Model"
        verbose_name_plural = "Registry Field Test Models"

    def __str__(self) -> str:
        return f"RegistryFieldTestModel({self.pk}): {self.name}"

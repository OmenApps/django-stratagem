"""A Merchant model that stores its chosen payment gateway."""

from django.db import models

from django_stratagem.fields import RegistryClassField

from .registry import PaymentGatewayRegistry


class Merchant(models.Model):
    """A merchant with one selected payment gateway."""

    name = models.CharField(max_length=100)
    gateway = RegistryClassField(
        registry=PaymentGatewayRegistry,
        blank=True,
        null=True,
        help_text="The payment gateway this merchant uses",
    )

    class Meta:
        app_label = "examples_payments"

    def __str__(self) -> str:
        return self.name

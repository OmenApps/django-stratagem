# onboarding/forms.py
from django import forms

from django_stratagem import (
    ContextAwareRegistryFormField,
    RegistryContextMixin,
    RegistryWidget,
)
from onboarding.registry import OnboardingRegistry


class OnboardingPreferenceForm(RegistryContextMixin, forms.Form):
    workflow = ContextAwareRegistryFormField(
        registry=OnboardingRegistry,
        widget=RegistryWidget(registry=OnboardingRegistry),
    )

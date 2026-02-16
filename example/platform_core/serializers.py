# platform_core/serializers.py
from compliance.registry import ComplianceRegistry
from onboarding.registry import OnboardingRegistry
from rest_framework import serializers

from django_stratagem.drf.serializers import DrfMultipleRegistryField, DrfRegistryField


class FirmConfigSerializer(serializers.Serializer):
    compliance_strategy = DrfRegistryField(registry=ComplianceRegistry)
    onboarding_workflows = DrfMultipleRegistryField(registry=OnboardingRegistry)

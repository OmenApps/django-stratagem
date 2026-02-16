# platform_core/models.py
from compliance.registry import ComplianceRegistry
from django.contrib.auth.models import User
from django.db import models
from onboarding.registry import OnboardingRegistry


class Firm(models.Model):
    """A construction management firm that subscribes to the platform."""

    name = models.CharField(max_length=200)
    region = models.CharField(
        max_length=50,
        choices=[
            ("us", "United States"),
            ("uk", "United Kingdom"),
            ("au", "Australia"),
        ],
    )
    plan = models.CharField(
        max_length=20,
        choices=[
            ("starter", "Starter"),
            ("professional", "Professional"),
            ("enterprise", "Enterprise"),
        ],
    )

    # Stores the class; accessing the field returns the class
    compliance_strategy = ComplianceRegistry.choices_field(blank=True, default="")

    # Stores the class; accessing the field returns an instance with region injected
    compliance_handler = ComplianceRegistry.instance_field(
        blank=True,
        default="",
        factory=lambda klass, obj: klass(region=obj.region),
    )

    def __str__(self):
        return self.name


class Subcontractor(models.Model):
    """A subcontractor company managed by a firm."""

    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name="subcontractors")
    name = models.CharField(max_length=200)
    trade = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.trade})"


class Employee(models.Model):
    """An employee of a firm who uses the platform."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name="employees")
    role = models.CharField(
        max_length=30,
        choices=[
            ("admin", "Firm Administrator"),
            ("manager", "Project Manager"),
            ("coordinator", "Safety Coordinator"),
        ],
    )
    onboarding_preference = OnboardingRegistry.choices_field(blank=True, default="")

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"


class SubcontractorEmployee(models.Model):
    """A user who works for a subcontractor company."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subcontractor = models.ForeignKey(Subcontractor, on_delete=models.CASCADE, related_name="employees")
    role = models.CharField(
        max_length=30,
        choices=[
            ("foreman", "Foreman"),
            ("worker", "Field Worker"),
            ("safety_officer", "Safety Officer"),
        ],
    )

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"

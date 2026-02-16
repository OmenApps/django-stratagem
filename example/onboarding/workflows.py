# onboarding/workflows.py
from django_stratagem import ConditionalInterface, PermissionCondition
from onboarding.conditions import PlanCondition
from onboarding.registry import OnboardingInterface, OnboardingRegistry


class StandardOnboarding(OnboardingInterface):
    slug = "standard"
    description = "Basic document collection and verification"
    priority = 10

    def run_workflow(self, subcontractor):
        return ["collect_documents", "verify_insurance", "approve"]

    def get_steps(self):
        return ["Document upload", "Insurance check", "Approval"]


class GuidedOnboarding(ConditionalInterface):
    registry = OnboardingRegistry
    slug = "guided"
    description = "Step-by-step guided onboarding with checklists"
    priority = 20
    condition = PlanCondition(["professional", "enterprise"])

    def run_workflow(self, subcontractor):
        return ["orientation", "collect_documents", "site_visit", "verify_insurance", "training", "approve"]

    def get_steps(self):
        return ["Orientation session", "Document upload", "Site visit", "Insurance check", "Safety training", "Approval"]


class EnterpriseOnboarding(ConditionalInterface):
    registry = OnboardingRegistry
    slug = "enterprise"
    description = "White-glove onboarding with dedicated coordinator"
    priority = 30
    condition = PlanCondition(["enterprise"]) & PermissionCondition("onboarding.use_enterprise")

    def run_workflow(self, subcontractor):
        return ["assign_coordinator", "orientation", "collect_documents", "background_check",
                "site_visit", "verify_insurance", "training", "compliance_audit", "approve"]

    def get_steps(self):
        return ["Coordinator assignment", "Orientation", "Documents", "Background check",
                "Site visit", "Insurance", "Training", "Compliance audit", "Approval"]

# onboarding/registry.py
from django_stratagem import Interface, Registry


class OnboardingRegistry(Registry):
    implementations_module = "workflows"


class OnboardingInterface(Interface):
    registry = OnboardingRegistry

    def run_workflow(self, subcontractor):
        """Execute the onboarding workflow for a subcontractor."""
        raise NotImplementedError

    def get_steps(self):
        """Return the list of steps in this workflow."""
        raise NotImplementedError

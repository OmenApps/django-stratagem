# compliance/registry.py
import logging
from datetime import datetime

from django_stratagem import Interface, Registry

logger = logging.getLogger("compliance.audit")


class ComplianceRegistry(Registry):
    implementations_module = "compliance_reports"

    @classmethod
    def validate_implementation(cls, implementation):
        """Require that every compliance implementation defines the expected methods."""
        super().validate_implementation(implementation)

        if not callable(getattr(implementation, "generate_report", None)):
            raise TypeError(
                f"{implementation.__name__} must define a generate_report() method"
            )

        if not callable(getattr(implementation, "get_requirements", None)):
            raise TypeError(
                f"{implementation.__name__} must define a get_requirements() method"
            )

    @classmethod
    def build_implementation_meta(cls, implementation):
        """Record audit metadata alongside each registered implementation."""
        meta = super().build_implementation_meta(implementation)
        meta["certification_body"] = getattr(implementation, "certification_body", "unknown")
        meta["last_audit"] = getattr(implementation, "last_audit", None)
        meta["registered_at"] = datetime.now().isoformat()
        return meta

    @classmethod
    def on_register(cls, slug, implementation, meta):
        logger.info(
            "Registered compliance implementation: %s (body=%s, priority=%d)",
            slug,
            meta.get("certification_body", "unknown"),
            meta.get("priority", 0),
        )

    @classmethod
    def on_unregister(cls, slug, meta):
        logger.warning(
            "Unregistered compliance implementation: %s (was certified by %s)",
            slug,
            meta.get("certification_body", "unknown"),
        )


class ComplianceInterface(Interface):
    registry = ComplianceRegistry

    def __init__(self, **kwargs):
        self.region = kwargs.get("region")

    def generate_report(self, subcontractor, period):
        """Generate a compliance report for the given subcontractor and period."""
        raise NotImplementedError

    def get_requirements(self):
        """Return a list of compliance requirements."""
        raise NotImplementedError


class InspectionScheduleRegistry(Registry):
    implementations_module = "inspection_schedules"


class InspectionScheduleInterface(Interface):
    registry = InspectionScheduleRegistry

    def get_next_inspection(self, subcontractor):
        """Return the next scheduled inspection date."""
        raise NotImplementedError

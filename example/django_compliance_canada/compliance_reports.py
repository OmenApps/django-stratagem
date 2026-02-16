# django_compliance_canada/compliance_reports.py
from compliance.registry import ComplianceInterface


class CanadianOhsCompliance(ComplianceInterface):
    slug = "canadian_ohs"
    description = "Canadian OHS compliance reporting"
    icon = "ca-flag"
    priority = 40
    certification_body = "CCOHS"
    last_audit = "2026-01-10"

    def generate_report(self, subcontractor, period):
        return {
            "standard": "Canada OHS Regulations",
            "subcontractor": subcontractor.name,
            "period": str(period),
            "sections": ["workplace_hazards", "whmis", "joint_committee"],
        }

    def get_requirements(self):
        return ["WHMIS training", "Joint health and safety committee", "Workplace inspection reports"]

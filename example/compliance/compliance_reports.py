# compliance/compliance_reports.py
from compliance.registry import ComplianceInterface


class OshaCompliance(ComplianceInterface):
    slug = "osha"
    description = "U.S. OSHA safety reporting"
    icon = "us-flag"
    priority = 10
    certification_body = "OSHA"
    last_audit = "2025-12-15"

    def generate_report(self, subcontractor, period):
        return {
            "standard": "OSHA 29 CFR 1926",
            "subcontractor": subcontractor.name,
            "period": str(period),
            "sections": ["fall_protection", "scaffolding", "electrical"],
        }

    def get_requirements(self):
        return ["OSHA 10-hour card", "Site-specific safety plan", "Weekly toolbox talks"]


class HseCompliance(ComplianceInterface):
    slug = "hse"
    description = "UK Health and Safety Executive reporting"
    icon = "uk-flag"
    priority = 20
    certification_body = "HSE"
    last_audit = "2025-11-20"

    def generate_report(self, subcontractor, period):
        return {
            "standard": "HSE CDM 2015",
            "subcontractor": subcontractor.name,
            "period": str(period),
            "sections": ["risk_assessment", "method_statement", "coshh"],
        }

    def get_requirements(self):
        return ["CSCS card", "RAMS documentation", "COSHH assessments"]


class SafeWorkCompliance(ComplianceInterface):
    slug = "safework"
    description = "SafeWork Australia reporting"
    icon = "au-flag"
    priority = 30
    certification_body = "SafeWork Australia"
    last_audit = "2025-10-05"

    def generate_report(self, subcontractor, period):
        return {
            "standard": "WHS Act 2011",
            "subcontractor": subcontractor.name,
            "period": str(period),
            "sections": ["swms", "risk_register", "incident_log"],
        }

    def get_requirements(self):
        return ["White Card", "SWMS for high-risk work", "Safety data sheets"]

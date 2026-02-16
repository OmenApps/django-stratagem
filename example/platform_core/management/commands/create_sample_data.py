"""Management command to create sample data for the construction management example."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create sample firms, subcontractors, employees, and billing configs"

    def handle(self, *args, **options):
        from billing.models import BillingConfig

        from platform_core.models import Employee, Firm, Subcontractor, SubcontractorEmployee

        # Create superuser
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin")
            self.stdout.write(self.style.SUCCESS("Created superuser: admin / admin"))

        # Create firms
        firms_data = [
            {
                "name": "Apex Construction",
                "region": "us",
                "plan": "professional",
                "compliance": "osha",
                "billing_model": "time_and_materials",
                "invoicing": "hourly",
            },
            {
                "name": "Sterling Builders",
                "region": "uk",
                "plan": "enterprise",
                "compliance": "hse",
                "billing_model": "fixed_price",
                "invoicing": "milestone",
            },
            {
                "name": "Pacific Works",
                "region": "au",
                "plan": "starter",
                "compliance": "safework",
                "billing_model": "cost_plus",
                "invoicing": "open_book",
            },
        ]

        subcontractors_data = {
            "Apex Construction": [
                ("Summit Electrical", "Electrical"),
                ("Ironclad Welding", "Steel Fabrication"),
                ("ProPlumb Solutions", "Plumbing"),
            ],
            "Sterling Builders": [
                ("Thames Roofing", "Roofing"),
                ("Albion Masonry", "Masonry"),
            ],
            "Pacific Works": [
                ("Southern Cross HVAC", "HVAC"),
                ("Outback Excavation", "Earthworks"),
                ("Reef Concrete", "Concrete"),
            ],
        }

        for fd in firms_data:
            if Firm.objects.filter(name=fd["name"]).exists():
                firm = Firm.objects.get(name=fd["name"])
                self.stdout.write(f"Firm already exists: {firm.name}")
            else:
                firm = Firm(
                    name=fd["name"],
                    region=fd["region"],
                    plan=fd["plan"],
                )
                firm.compliance_strategy = fd["compliance"]
                firm.compliance_handler = fd["compliance"]
                firm.save()
                self.stdout.write(self.style.SUCCESS(f"Created firm: {firm.name}"))

            # Create subcontractors
            for sub_name, trade in subcontractors_data.get(fd["name"], []):
                _, sub_created = Subcontractor.objects.get_or_create(
                    firm=firm,
                    name=sub_name,
                    defaults={"trade": trade, "is_active": True},
                )
                if sub_created:
                    self.stdout.write(f"  Created subcontractor: {sub_name}")

            # Create billing config
            if not BillingConfig.objects.filter(firm=firm).exists():
                bc = BillingConfig(firm=firm)
                bc.billing_model = fd["billing_model"]
                bc.invoicing_strategy = fd["invoicing"]
                bc.save()

        # Create firm_user - employee of Apex Construction
        apex = Firm.objects.get(name="Apex Construction")
        if not User.objects.filter(username="firm_user").exists():
            firm_user = User.objects.create_user(
                username="firm_user",
                password="firm_user",
                first_name="Apex",
                last_name="Manager",
                email="firm_user@example.com",
                is_staff=True,
            )
            employee = Employee(user=firm_user, firm=apex, role="admin")
            employee.onboarding_preference = "guided"
            employee.save()
            self.stdout.write(self.style.SUCCESS("Created firm employee: firm_user / firm_user"))

        # Create subcontractor_user - employee of Summit Electrical (subcontractor under Apex)
        summit = Subcontractor.objects.get(name="Summit Electrical")
        if not User.objects.filter(username="subcontractor_user").exists():
            sub_user = User.objects.create_user(
                username="subcontractor_user",
                password="subcontractor_user",
                first_name="Summit",
                last_name="Foreman",
                email="subcontractor_user@example.com",
                is_staff=True,
            )
            SubcontractorEmployee.objects.create(user=sub_user, subcontractor=summit, role="foreman")
            self.stdout.write(self.style.SUCCESS("Created subcontractor employee: subcontractor_user / subcontractor_user"))

        self.stdout.write(self.style.SUCCESS("Sample data created successfully!"))

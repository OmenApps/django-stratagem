# Construction Management Platform

This tutorial builds a multi-tenant construction management platform using django-stratagem. It covers nearly every feature of the library - not as a feature demo, but because each one solves a real problem the scenario demands.

:::{tip}
A complete, runnable version of this project lives in `example/` at the repository root. You can clone the repo, run `uv run python example/manage.py migrate && uv run python example/manage.py create_sample_data`, and start exploring immediately. The code blocks below are excerpts from the example files - each one references the corresponding `example/` path.

The seed command creates three demo accounts:

| Username | Password | Role |
|---|---|---|
| `admin` | `admin` | Superuser - full admin access |
| `firm_user` | `firm_user` | Employee of Apex Construction (US, professional plan) |
| `subcontractor_user` | `subcontractor_user` | Employee of Summit Electrical (subcontractor under Apex) |
:::

## What you'll build

A white-label SaaS platform where **construction management firms** subscribe to manage their **subcontractor** companies. Different firms operate in different regions, subscribe to different plans, and need different compliance rules, onboarding workflows, billing models, and scheduling strategies.

By the end you'll have four Django apps (`platform_core`, `compliance`, `onboarding`, `billing`) wired together with registries, conditional availability, hierarchical relationships, admin integration, templates, an API layer, signals, hooks, and a third-party plugin.

### Prerequisites

You should have completed the [Getting Started](quickstart.md) guide and be comfortable with Django models, apps, and class-based views.

## 1. The Data Model

Start with the core models. No registries yet - just plain Django.

```python
# platform_core/models.py
from django.contrib.auth.models import User
from django.db import models


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
```

The relationships form a B2B2B chain:

```{mermaid}
erDiagram
    Platform ||--o{ Firm : hosts
    Firm ||--o{ Subcontractor : manages
    Firm ||--o{ Employee : employs
    Employee }o--|| User : "has account"
    Subcontractor ||--o{ SubcontractorEmployee : employs
    SubcontractorEmployee }o--|| User : "has account"
```

The problem appears immediately: a US firm must file OSHA compliance reports, a UK firm follows HSE rules, and an Australian firm uses SafeWork standards. You could add `if/elif` branches everywhere, but that scatters business logic across the codebase and makes adding a new region painful.

## 2. Compliance Reporting

This is exactly what registries solve. Define a `ComplianceRegistry`, create an interface, and write one class per compliance standard.

### Define the registry and interface

```python
# compliance/registry.py
from django_stratagem import Registry, Interface


class ComplianceRegistry(Registry):
    implementations_module = "compliance_reports"


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
```

`implementations_module = "compliance_reports"` tells django-stratagem to look for a `compliance_reports.py` module in every installed app during autodiscovery. The `__init__` method accepts `**kwargs` so the factory pattern in section 3 can inject `region`.

### Create implementations

```python
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
```

Each class sets a unique `slug`, a human-readable `description`, and implements the interface methods. When Django starts, autodiscovery imports this module and the classes register themselves automatically.

```{mermaid}
flowchart LR
    A[Django starts] --> B[discover_registries]
    B --> C["Import compliance_reports modules"]
    C --> D["OshaCompliance, HseCompliance, SafeWorkCompliance register via __init_subclass__"]
    D --> E[Model field choices updated]
```

### Use the registry

```python
from compliance.registry import ComplianceRegistry

# List everything registered
for impl_class in ComplianceRegistry:
    print(f"{impl_class.slug}: {impl_class.description}")

# Get by slug
osha = ComplianceRegistry.get(slug="osha")
report = osha.generate_report(subcontractor, "2026-Q1")

# Get the class without instantiating
osha_class = ComplianceRegistry.get_class(slug="osha")

# Safe fallback
handler = ComplianceRegistry.get_or_default(slug="unknown", default="osha")

# Choices for a form
choices = ComplianceRegistry.get_choices()
# [("osha", "Osha Compliance"), ("hse", "Hse Compliance"), ("safework", "Safe Work Compliance")]
```

:::{tip}
Adding a fourth compliance standard (say, EU regulations) is one file with one class. No changes to existing code, no migration, no settings update.
:::

See [How Auto-Discovery Works](explanation.md#how-auto-discovery-works) for the full startup lifecycle.

## 3. Storing Firm Configuration

Firms need to persist their compliance choice in the database so the platform knows which standard to apply.

### Add a registry field to the model

```python
# platform_core/models.py
from django.db import models
from compliance.registry import ComplianceRegistry


class Firm(models.Model):
    name = models.CharField(max_length=200)
    region = models.CharField(max_length=50)
    plan = models.CharField(max_length=20)

    # Stores the class; accessing the field returns the class
    compliance_strategy = ComplianceRegistry.choices_field()
```

`choices_field()` creates a `RegistryClassField` - a `CharField` that stores the fully qualified class name but returns the class on access:

```python
firm = Firm.objects.create(name="Apex Construction", region="us", plan="professional")
firm.compliance_strategy = "osha"  # Set by slug
firm.save()

firm.compliance_strategy  # Returns <class 'OshaCompliance'>
firm.compliance_strategy.get_requirements()
# ["OSHA 10-hour card", "Site-specific safety plan", "Weekly toolbox talks"]
```

### Factory pattern for automatic instantiation

If you want accessing the field to return a ready-to-use *instance* instead of the class, use `instance_field()` with a factory that injects the firm's data:

```python
# platform_core/models.py
class Firm(models.Model):
    # ...
    compliance_handler = ComplianceRegistry.instance_field(
        factory=lambda klass, obj: klass(region=obj.region),
    )
```

Now `firm.compliance_handler` returns an instance with the firm's region already injected. See [Advanced Factory Patterns](howto-fields.md#advanced-factory-patterns) for dependency injection and singleton patterns.

### Query with lookups

Registry fields support custom lookups that convert classes and slugs to the stored FQN string automatically:

```python
from compliance.compliance_reports import OshaCompliance, HseCompliance

# Filter by class
us_firms = Firm.objects.filter(compliance_strategy=OshaCompliance)

# Filter by slug
us_firms = Firm.objects.filter(compliance_strategy="osha")

# Filter with __in
north_atlantic = Firm.objects.filter(compliance_strategy__in=[OshaCompliance, HseCompliance])
```

:::{tip}
You can assign by class, by slug, or by fully qualified name. The field handles resolution in all three cases. See [Slug Resolution](howto-fields.md#slug-resolution) for the resolution order.
:::

See [How to Use Model Fields](howto-fields.md) for all field types and lookup details.

## 4. Controlling Who Sees What

Not every firm should see every onboarding workflow. Starter-plan firms get the basic workflow. Professional firms unlock guided onboarding. Enterprise firms - if the user also has the right permission - get a white-glove enterprise workflow.

### Define the onboarding registry

```python
# onboarding/registry.py
from django_stratagem import Registry, Interface


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
```

### Write a custom condition

The built-in conditions cover permissions and feature flags, but you need one that checks the firm's subscription plan. Subclass `Condition` and implement `is_met`:

```python
# onboarding/conditions.py
from django_stratagem import Condition


class PlanCondition(Condition):
    """Check that the firm's plan is in the allowed list."""

    def __init__(self, allowed_plans):
        self.allowed_plans = allowed_plans

    def is_met(self, context):
        firm = context.get("firm")
        if not firm:
            return False
        return firm.plan in self.allowed_plans

    def explain(self):
        return f"Firm plan must be one of: {', '.join(self.allowed_plans)}"
```

### Create conditional implementations

```python
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
```

`StandardOnboarding` uses plain `Interface` - it is always available. `GuidedOnboarding` and `EnterpriseOnboarding` use `ConditionalInterface` with composed conditions. The `&` operator means both sides must pass.

### Filter by context

```python
from onboarding.registry import OnboardingRegistry

# Build context from the request
context = {
    "user": request.user,
    "firm": request.user.employee.firm,
    "request": request,
}

# Starter firm - only sees standard
available = OnboardingRegistry.get_available_implementations(context)
# {"standard": <class StandardOnboarding>}

# Enterprise firm with permission - sees all three
available = OnboardingRegistry.get_available_implementations(context)
# {"standard": ..., "guided": ..., "enterprise": ...}

# Get choices for a form dropdown, filtered by context
choices = OnboardingRegistry.get_choices_for_context(context)
```

The decision flow looks like this:

```{mermaid}
flowchart TD
    A[Request arrives] --> B{Authenticated?}
    B -->|No| C[StandardOnboarding only]
    B -->|Yes| D{Firm plan?}
    D -->|Starter| C
    D -->|Professional| E[Standard + Guided]
    D -->|Enterprise| F{Has permission?}
    F -->|No| E
    F -->|Yes| G[Standard + Guided + Enterprise]
```

:::{tip}
Conditions compose with `&` (AND), `|` (OR), and `~` (NOT). You can build arbitrarily complex rules from simple, testable building blocks. Each condition's `explain()` method returns a human-readable description for debugging.
:::

See [How to Use Conditional Availability](howto-conditions.md) for all built-in conditions and composition patterns.

## 5. Hierarchical Billing

Billing has a two-level structure: firms first pick a **billing model** (time-and-materials, fixed-price, or cost-plus), then choose an **invoicing strategy** that only makes sense under that model. You wouldn't offer milestone invoicing to a time-and-materials firm.

### Define the parent registry

```python
# billing/registry.py
from django_stratagem import Registry, Interface, HierarchicalRegistry, HierarchicalInterface


class BillingModelRegistry(Registry):
    implementations_module = "billing_models"


class BillingModelInterface(Interface):
    registry = BillingModelRegistry

    def calculate_total(self, line_items):
        raise NotImplementedError


class InvoicingStrategyRegistry(HierarchicalRegistry):
    implementations_module = "invoicing_strategies"
    parent_registry = BillingModelRegistry


class InvoicingStrategyInterface(HierarchicalInterface):
    registry = InvoicingStrategyRegistry

    def generate_invoice(self, firm, period):
        raise NotImplementedError
```

`HierarchicalRegistry` links `InvoicingStrategyRegistry` to `BillingModelRegistry` as its parent. `HierarchicalInterface` adds the `parent_slug` attribute.

### Create parent implementations

```python
# billing/billing_models.py
from billing.registry import BillingModelInterface


class TimeAndMaterials(BillingModelInterface):
    slug = "time_and_materials"
    description = "Bill for actual hours and materials used"
    priority = 10

    def calculate_total(self, line_items):
        return sum(item["hours"] * item["rate"] + item.get("materials", 0) for item in line_items)


class FixedPrice(BillingModelInterface):
    slug = "fixed_price"
    description = "Bill a pre-agreed fixed amount per milestone"
    priority = 20

    def calculate_total(self, line_items):
        return sum(item["amount"] for item in line_items)


class CostPlus(BillingModelInterface):
    slug = "cost_plus"
    description = "Bill actual costs plus a percentage markup"
    priority = 30

    def calculate_total(self, line_items):
        base = sum(item["cost"] for item in line_items)
        markup = sum(item["cost"] * item.get("markup_pct", 0.15) for item in line_items)
        return base + markup
```

### Create child implementations

Each invoicing strategy declares which billing model it belongs to via `parent_slug`:

```python
# billing/invoicing_strategies.py
from billing.registry import InvoicingStrategyInterface


class HourlyInvoicing(InvoicingStrategyInterface):
    slug = "hourly"
    description = "Invoice per hour worked"
    parent_slug = "time_and_materials"

    def generate_invoice(self, firm, period):
        return {"type": "hourly", "firm": firm.name, "period": str(period)}


class WeeklyInvoicing(InvoicingStrategyInterface):
    slug = "weekly"
    description = "Weekly consolidated invoice"
    parent_slug = "time_and_materials"

    def generate_invoice(self, firm, period):
        return {"type": "weekly", "firm": firm.name, "period": str(period)}


class MilestoneInvoicing(InvoicingStrategyInterface):
    slug = "milestone"
    description = "Invoice on milestone completion"
    parent_slug = "fixed_price"

    def generate_invoice(self, firm, period):
        return {"type": "milestone", "firm": firm.name, "period": str(period)}


class CompletionInvoicing(InvoicingStrategyInterface):
    slug = "completion"
    description = "Invoice on project completion"
    parent_slug = "fixed_price"

    def generate_invoice(self, firm, period):
        return {"type": "completion", "firm": firm.name, "period": str(period)}


class OpenBookInvoicing(InvoicingStrategyInterface):
    slug = "open_book"
    description = "Transparent cost breakdown with markup"
    parent_slug = "cost_plus"

    def generate_invoice(self, firm, period):
        return {"type": "open_book", "firm": firm.name, "period": str(period)}


class MonthlyReconciliation(InvoicingStrategyInterface):
    slug = "monthly_reconciliation"
    description = "Monthly cost reconciliation and settlement"
    parent_slug = "cost_plus"

    def generate_invoice(self, firm, period):
        return {"type": "monthly_reconciliation", "firm": firm.name, "period": str(period)}
```

The hierarchy:

```{mermaid}
graph TD
    BM[BillingModelRegistry]
    TM["TimeAndMaterials"]
    FP["FixedPrice"]
    CP["CostPlus"]
    BM --- TM
    BM --- FP
    BM --- CP
    TM --> HI["HourlyInvoicing"]
    TM --> WI["WeeklyInvoicing"]
    FP --> MI["MilestoneInvoicing"]
    FP --> CI["CompletionInvoicing"]
    CP --> OB["OpenBookInvoicing"]
    CP --> MR["MonthlyReconciliation"]
```

### Store in a model with parent validation

```python
# billing/models.py
from django.db import models
from django_stratagem import HierarchicalRegistryField
from billing.registry import BillingModelRegistry, InvoicingStrategyRegistry
from platform_core.models import Firm


class BillingConfig(models.Model):
    firm = models.OneToOneField(Firm, on_delete=models.CASCADE, related_name="billing_config")
    billing_model = BillingModelRegistry.choices_field()
    invoicing_strategy = HierarchicalRegistryField(
        registry=InvoicingStrategyRegistry,
        parent_field="billing_model",
    )

    def __str__(self):
        return f"Billing config for {self.firm.name}"
```

`parent_field="billing_model"` tells the field to validate that the selected invoicing strategy is valid for the chosen billing model.

### Query the hierarchy

```python
from billing.registry import InvoicingStrategyRegistry

# Get strategies valid for time-and-materials
children = InvoicingStrategyRegistry.get_children_for_parent("time_and_materials")
# {"hourly": <class HourlyInvoicing>, "weekly": <class WeeklyInvoicing>}

# Choices for a filtered dropdown
choices = InvoicingStrategyRegistry.get_choices_for_parent("time_and_materials")
# [("hourly", "Hourly Invoicing"), ("weekly", "Weekly Invoicing")]

# Full hierarchy map
hierarchy = InvoicingStrategyRegistry.get_hierarchy_map()
# {
#     "time_and_materials": ["hourly", "weekly"],
#     "fixed_price": ["milestone", "completion"],
#     "cost_plus": ["open_book", "monthly_reconciliation"],
# }

# Validate a specific relationship
InvoicingStrategyRegistry.validate_parent_child_relationship("fixed_price", "milestone")  # True
InvoicingStrategyRegistry.validate_parent_child_relationship("fixed_price", "hourly")  # False
```

:::{tip}
A child implementation can belong to multiple parents by using `parent_slugs` (a list) instead of `parent_slug`. For example, a "FlatFeeInvoicing" strategy could work under both `fixed_price` and `cost_plus`.
:::

See [How to Use Hierarchical Registries](howto-hierarchies.md) for more on parent-child relationships and `RegistryRelationship`.

## 6. Forms and Admin

Platform admins need to configure firms in the Django admin. Employees of each firm need self-serve forms to adjust their own settings.

### Admin for firm configuration

```python
# platform_core/admin.py
from django.contrib import admin
from django_stratagem.admin import ContextAwareRegistryAdmin
from platform_core.models import Firm


@admin.register(Firm)
class FirmAdmin(ContextAwareRegistryAdmin):
    list_display = ["name", "region", "plan", "compliance_strategy"]
    list_filter = ["region", "plan"]
```

`ContextAwareRegistryAdmin` injects the logged-in admin's context into registry form fields. If you're using conditional implementations, the dropdown only shows options the current user is allowed to see.

### Admin for billing with hierarchical fields

```python
# billing/admin.py
from django.contrib import admin
from django_stratagem.admin import HierarchicalRegistryAdmin
from billing.models import BillingConfig


@admin.register(BillingConfig)
class BillingConfigAdmin(HierarchicalRegistryAdmin):
    list_display = ["firm", "billing_model", "invoicing_strategy"]
```

`HierarchicalRegistryAdmin` extends `ContextAwareRegistryAdmin` with JavaScript-driven dynamic updates. When the admin selects a billing model, the invoicing strategy dropdown filters to show only valid children.

### List filter for registry fields

Registry fields automatically get admin list filters. You can also add them explicitly:

```python
from django_stratagem.admin import RegistryFieldListFilter

@admin.register(Firm)
class FirmAdmin(ContextAwareRegistryAdmin):
    list_display = ["name", "region", "plan", "compliance_strategy"]
    list_filter = [
        "region",
        "plan",
        ("compliance_strategy", RegistryFieldListFilter),
    ]
```

The filter is context-aware and only shows implementations available to the current admin user.

### Self-serve form for employees

Employees might configure their own notification or onboarding preferences through a form:

```python
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
```

`RegistryContextMixin` handles passing context to the form fields. `RegistryWidget` enhances the `<select>` with `title` (description), `data-icon`, and `data-priority` attributes on each option.

Use it in a view:

```python
# onboarding/views.py
from django.shortcuts import render
from onboarding.forms import OnboardingPreferenceForm


def onboarding_settings(request):
    context = {
        "user": request.user,
        "firm": request.user.employee.firm,
        "request": request,
    }
    form = OnboardingPreferenceForm(
        data=request.POST or None,
        registry_context=context,
    )
    if request.method == "POST" and form.is_valid():
        selected_workflow = form.cleaned_data["workflow"]
        # selected_workflow is the implementation class
        # ...
    return render(request, "onboarding/settings.html", {"form": form})
```

### Hierarchical form with dependent dropdowns

For billing configuration, use `HierarchicalFormMixin` to wire up parent-child field dependencies:

```python
# billing/forms.py
from django import forms
from django_stratagem import (
    HierarchicalFormMixin,
    HierarchicalRegistryFormField,
    RegistryFormField,
)
from billing.registry import BillingModelRegistry, InvoicingStrategyRegistry


class BillingConfigForm(HierarchicalFormMixin, forms.Form):
    billing_model = RegistryFormField(registry=BillingModelRegistry)
    invoicing_strategy = HierarchicalRegistryFormField(
        registry=InvoicingStrategyRegistry,
        parent_field="billing_model",
    )
```

:::{tip}
`HierarchicalFormMixin` validates that the selected child is valid for the selected parent during `clean()`. You don't need to write that validation yourself.
:::

See [How to Use Forms, Widgets, and the Admin](howto-forms-admin.md) for all form fields, widgets, and admin classes.

## 7. Templates

The subcontractor dashboard needs to display available compliance options and onboarding workflows. django-stratagem ships template tags and filters for this.

### Subcontractor dashboard

```html
<!-- templates/dashboard/subcontractor.html -->
{% load stratagem %}

<h2>Compliance Standards</h2>
{% get_implementations compliance_registry as standards %}
{% for slug, impl in standards.items %}
    <div class="card">
        {% if impl|registry_icon %}
            <span class="icon">{{ impl|registry_icon }}</span>
        {% endif %}
        <h3>{{ impl|display_name }}</h3>
        <p>{{ impl|registry_description }}</p>
    </div>
{% endfor %}

<h2>Available Onboarding Workflows</h2>
{% get_implementations onboarding_registry request_context as workflows %}
{% for slug, impl in workflows.items %}
    <div class="card">
        <h3>{{ impl|display_name }}</h3>
        <p>{{ impl|registry_description }}</p>
        {% if impl|is_available:request_context %}
            <span class="badge available">Available for your plan</span>
        {% else %}
            <span class="badge locked">Upgrade to unlock</span>
        {% endif %}
    </div>
{% endfor %}
```

### Build the template context in your view

```python
# platform_core/views.py
from django.shortcuts import render
from compliance.registry import ComplianceRegistry
from onboarding.registry import OnboardingRegistry


def subcontractor_dashboard(request):
    context = {
        "user": request.user,
        "firm": request.user.employee.firm,
        "request": request,
    }
    return render(request, "dashboard/subcontractor.html", {
        "compliance_registry": ComplianceRegistry,
        "onboarding_registry": OnboardingRegistry,
        "request_context": context,
    })
```

### Choices in a dropdown

The `get_choices` tag generates `(slug, label)` tuples suitable for `<select>` options:

```html
{% load stratagem %}

{% get_choices compliance_registry as compliance_choices %}
<select name="compliance">
    {% for slug, label in compliance_choices %}
        <option value="{{ slug }}">{{ label }}</option>
    {% endfor %}
</select>
```

:::{tip}
Pass a context dict to `get_implementations` or `get_choices` to get context-filtered results. Without a context, you get all registered implementations regardless of conditions.
:::

See [How to Use Template Tags and Filters](howto-templates.md) for the full list of tags and filters.

## 8. API Layer

The platform needs an API for mobile apps and third-party integrations. django-stratagem provides DRF serializer fields for custom endpoints and built-in views for dynamic choice loading.

### DRF serializer fields

Use `DrfRegistryField` in your serializers to accept and validate registry slugs:

```python
# platform_core/serializers.py
from rest_framework import serializers
from django_stratagem.drf.serializers import DrfRegistryField, DrfMultipleRegistryField
from compliance.registry import ComplianceRegistry
from onboarding.registry import OnboardingRegistry


class FirmConfigSerializer(serializers.Serializer):
    compliance_strategy = DrfRegistryField(registry=ComplianceRegistry)
    onboarding_workflows = DrfMultipleRegistryField(registry=OnboardingRegistry)
```

`DrfRegistryField` accepts slugs or FQNs as input, validates against the registry, and serializes back to slugs by default. `DrfMultipleRegistryField` works the same way for multiple selections.

```python
# Input
data = {
    "compliance_strategy": "osha",
    "onboarding_workflows": ["standard", "guided"],
}

serializer = FirmConfigSerializer(data=data)
serializer.is_valid(raise_exception=True)
serializer.validated_data["compliance_strategy"]
# <class 'OshaCompliance'>
```

### Built-in API views

django-stratagem includes two views for dynamic choice loading - useful for JavaScript-driven dependent dropdowns:

**`RegistryChoicesAPIView`** returns choices for a registry, optionally filtered by parent:

```
GET /stratagem/api/registry/choices/?registry=ComplianceRegistry
```

```json
{
    "choices": [["osha", "Osha Compliance"], ["hse", "Hse Compliance"], ["safework", "Safe Work Compliance"]],
    "registry": "ComplianceRegistry",
    "parent": null
}
```

**`RegistryHierarchyAPIView`** returns hierarchy maps for hierarchical registries:

```
GET /stratagem/api/registry/hierarchy/
```

```json
{
    "hierarchies": {
        "InvoicingStrategyRegistry": {
            "parent_registry": "BillingModelRegistry",
            "hierarchy_map": {
                "time_and_materials": ["hourly", "weekly"],
                "fixed_price": ["milestone", "completion"],
                "cost_plus": ["open_book", "monthly_reconciliation"]
            }
        }
    }
}
```

### URL configuration

Include the DRF URLs in your project:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    # ...
    path("stratagem/", include("django_stratagem.drf.urls")),
]
```

This registers:
- `stratagem/api/registry/choices/` - `RegistryChoicesAPIView`
- `stratagem/api/registry/hierarchy/` - `RegistryHierarchyAPIView`

:::{tip}
The API views are plain Django `View` subclasses returning `JsonResponse` - they don't require DRF to be installed. The DRF serializer fields (`DrfRegistryField`, `DrfMultipleRegistryField`) do require `djangorestframework`.
:::

See [How to Use DRF Integration](howto-drf.md) for the full API reference.

## 9. Time-Based and Feature Flag Conditions

Safety inspections are a core part of construction management. Different scheduling strategies apply depending on the time of day, the season, whether a feature is in beta, or the user's role.

### Define the inspection schedule registry

```python
# compliance/registry.py (continued)
from django_stratagem import Registry, Interface


class InspectionScheduleRegistry(Registry):
    implementations_module = "inspection_schedules"


class InspectionScheduleInterface(Interface):
    registry = InspectionScheduleRegistry

    def get_next_inspection(self, subcontractor):
        """Return the next scheduled inspection date."""
        raise NotImplementedError
```

### Time-constrained implementations

```python
# compliance/inspection_schedules.py
from datetime import date, time

from django_stratagem import (
    ConditionalInterface,
    DateRangeCondition,
    FeatureFlagCondition,
    GroupCondition,
    TimeWindowCondition,
)
from compliance.registry import InspectionScheduleInterface, InspectionScheduleRegistry


class StandardSchedule(InspectionScheduleInterface):
    slug = "standard"
    description = "Regular inspection schedule - available any time"
    priority = 10

    def get_next_inspection(self, subcontractor):
        # ... standard scheduling logic
        pass


class BusinessHoursSchedule(ConditionalInterface):
    registry = InspectionScheduleRegistry
    slug = "business_hours"
    description = "Inspections during business hours only (Mon-Fri, 9am-5pm)"
    priority = 20
    condition = TimeWindowCondition(time(9, 0), time(17, 0), days=[0, 1, 2, 3, 4])

    def get_next_inspection(self, subcontractor):
        # ... only schedule during business hours
        pass


class SummerBlitzSchedule(ConditionalInterface):
    registry = InspectionScheduleRegistry
    slug = "summer_blitz"
    description = "Accelerated summer inspection campaign (Jun-Aug)"
    priority = 30
    condition = DateRangeCondition(date(2026, 6, 1), date(2026, 8, 31))

    def get_next_inspection(self, subcontractor):
        # ... more frequent inspections during peak season
        pass


class SmartSchedule(ConditionalInterface):
    registry = InspectionScheduleRegistry
    slug = "smart_schedule"
    description = "AI-powered risk-based scheduling (beta)"
    priority = 40
    condition = FeatureFlagCondition("smart_scheduling_beta")

    def get_next_inspection(self, subcontractor):
        # ... ML-based scheduling
        pass


class ManagerSchedule(ConditionalInterface):
    registry = InspectionScheduleRegistry
    slug = "manager_only"
    description = "Manager-defined custom schedule"
    priority = 50
    condition = GroupCondition("project_managers")

    def get_next_inspection(self, subcontractor):
        # ... custom schedule set by project manager
        pass
```

### Composing multiple conditions

For a strategy that's only available during summer business hours, compose conditions:

```python
class SummerBusinessHoursSchedule(ConditionalInterface):
    registry = InspectionScheduleRegistry
    slug = "summer_business_hours"
    description = "Business hours inspections during summer peak"
    priority = 35
    condition = (
        TimeWindowCondition(time(9, 0), time(17, 0), days=[0, 1, 2, 3, 4])
        & DateRangeCondition(date(2026, 6, 1), date(2026, 8, 31))
    )

    def get_next_inspection(self, subcontractor):
        pass
```

### Checking conditions at runtime

```python
from compliance.registry import InspectionScheduleRegistry

context = {"user": request.user, "request": request}

# Only strategies whose conditions pass right now
available = InspectionScheduleRegistry.get_available_implementations(context)

# Get with fallback if preferred strategy is unavailable
schedule = InspectionScheduleRegistry.get_for_context(
    context,
    slug="summer_blitz",
    fallback="standard",
)
```

:::{tip}
`TimeWindowCondition` handles overnight windows (e.g., `time(22, 0)` to `time(6, 0)`) and day-of-week filtering using Python weekday convention (0=Monday, 6=Sunday). `DateRangeCondition` supports open-ended ranges by passing `None` for either bound.
:::

See [How to Use Conditional Availability](howto-conditions.md) for the full list of built-in conditions.

## 10. Extension Hooks

Construction compliance is a regulated domain. You need strict validation on what gets registered, audit metadata on every implementation, and a log trail when registrations change.

### Strict interface enforcement

Override `validate_implementation` to require that every compliance implementation defines the expected methods:

```python
# compliance/registry.py
from django_stratagem import Registry, Interface


class ComplianceRegistry(Registry):
    implementations_module = "compliance_reports"

    @classmethod
    def validate_implementation(cls, implementation):
        # Preserve default slug + interface checks
        super().validate_implementation(implementation)

        # Require generate_report method
        if not callable(getattr(implementation, "generate_report", None)):
            raise TypeError(
                f"{implementation.__name__} must define a generate_report() method"
            )

        # Require get_requirements method
        if not callable(getattr(implementation, "get_requirements", None)):
            raise TypeError(
                f"{implementation.__name__} must define a get_requirements() method"
            )
```

If `validate_implementation` raises, registration stops immediately - the class is not stored, `on_register` is not called, and no signal fires.

### Audit metadata

Override `build_implementation_meta` to record extra information alongside each registered implementation:

```python
# compliance/registry.py (continued)
from datetime import datetime


class ComplianceRegistry(Registry):
    implementations_module = "compliance_reports"

    @classmethod
    def validate_implementation(cls, implementation):
        super().validate_implementation(implementation)
        if not callable(getattr(implementation, "generate_report", None)):
            raise TypeError(f"{implementation.__name__} must define generate_report()")
        if not callable(getattr(implementation, "get_requirements", None)):
            raise TypeError(f"{implementation.__name__} must define get_requirements()")

    @classmethod
    def build_implementation_meta(cls, implementation):
        meta = super().build_implementation_meta(implementation)
        meta["certification_body"] = getattr(implementation, "certification_body", "unknown")
        meta["last_audit"] = getattr(implementation, "last_audit", None)
        meta["registered_at"] = datetime.now().isoformat()
        return meta
```

Now implementations can declare audit-relevant attributes (already added in section 2):

```python
# compliance/compliance_reports.py
class OshaCompliance(ComplianceInterface):
    slug = "osha"
    description = "U.S. OSHA safety reporting"
    certification_body = "OSHA"
    last_audit = "2025-12-15"
    # ...
```

Access the extra metadata:

```python
meta = ComplianceRegistry.get_implementation_meta("osha")
meta["certification_body"]  # "OSHA"
meta["registered_at"]       # "2026-01-15T10:30:00.123456"
```

### Audit trail on registration changes

Override `on_register` and `on_unregister` for logging:

```python
# compliance/registry.py (continued)
import logging

logger = logging.getLogger("compliance.audit")


class ComplianceRegistry(Registry):
    implementations_module = "compliance_reports"

    # ... validate_implementation and build_implementation_meta from above ...

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
```

### Execution order

The hooks run in a specific order:

```
register():
  1. validate_implementation(implementation)  - may raise, stopping everything
  2. meta = build_implementation_meta(implementation)
  3. implementations[slug] = meta
  4. clear_cache()
  5. on_register(slug, implementation, meta)
  6. implementation_registered signal sent

unregister():
  1. meta = implementations.pop(slug)
  2. clear_cache()
  3. on_unregister(slug, meta)
  4. implementation_unregistered signal sent
```

:::{tip}
Hooks are for logic specific to one registry subclass. Use signals (next section) when multiple unrelated parts of the system need to react to registration changes.
:::

See [Extension Hooks and Customization Points](hooks.md) for the full hook reference and testing patterns.

## 11. Signals

Different apps need to react when registrations change. The billing app might need to invalidate cached pricing when a billing model is added. The platform might need to notify firms. Signals provide the loose coupling for this.

### Cross-app cache invalidation

```python
# billing/signals.py
from django.dispatch import receiver
from django_stratagem.signals import implementation_registered, implementation_unregistered


@receiver(implementation_registered)
@receiver(implementation_unregistered)
def invalidate_billing_cache(sender, **kwargs):
    """Clear billing caches when any billing registry changes."""
    from billing.registry import BillingModelRegistry, InvoicingStrategyRegistry

    if sender in (BillingModelRegistry, InvoicingStrategyRegistry):
        from django.core.cache import cache
        cache.delete("billing:choices")
        cache.delete("billing:hierarchy_map")
```

### Notify firms on new compliance options

```python
# platform_core/signals.py
import logging

from django.dispatch import receiver
from django_stratagem.signals import implementation_registered

logger = logging.getLogger("platform_core")


@receiver(implementation_registered)
def notify_firms_of_new_option(sender, registry, implementation, **kwargs):
    """Log when a new compliance option becomes available."""
    from compliance.registry import ComplianceRegistry

    if registry is ComplianceRegistry:
        logger.info(
            "New compliance option available: %s - %s",
            implementation.slug,
            implementation.description,
        )
```

### Warm caches after reload

```python
# platform_core/signals.py (continued)
from django.dispatch import receiver
from django_stratagem.signals import registry_reloaded


@receiver(registry_reloaded)
def warm_caches(sender, registry, **kwargs):
    """Pre-populate caches after a registry reload."""
    registry.get_choices()
    registry.get_items()
```

### Connect signals at startup

Make sure the signal handlers are imported in your `AppConfig.ready()`:

```python
# billing/apps.py
from django.apps import AppConfig


class BillingConfig(AppConfig):
    name = "billing"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import billing.signals  # noqa: F401
```

:::{tip}
Use hooks when the behavior belongs to a specific registry subclass. Use signals when the listener lives in a different app or when multiple listeners need to react independently.
:::

See [Extension Hooks and Customization Points](hooks.md#signals) for more signal patterns and the complete signal reference.

## 12. Plugins

A partner company builds a Canadian compliance module. They should be able to ship it as a separate package that plugs into your `ComplianceRegistry` without touching your code.

### The plugin package

The plugin is a normal Python package with an implementation and a metadata module:

```python
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
```

### Plugin metadata

```python
# django_compliance_canada/stratagem_plugin.py

__version__ = "1.0.0"

REGISTRY = "ComplianceRegistry"

IMPLEMENTATIONS = [
    "django_compliance_canada.compliance_reports.CanadianOhsCompliance",
]
```

### Register the entry point

In the plugin's `pyproject.toml`:

```toml
[project.entry-points."django_stratagem.plugins"]
compliance_canada = "django_compliance_canada.stratagem_plugin"
```

Once installed, `CanadianOhsCompliance` appears in `ComplianceRegistry` alongside the built-in options - in forms, admin dropdowns, and API responses.

### Controlling plugins

Platform operators can enable or disable plugins in settings:

```python
# settings.py
DJANGO_STRATAGEM = {
    # Allow only specific plugins (None means allow all)
    "ENABLED_PLUGINS": ["compliance_canada"],

    # Or block specific plugins while allowing everything else
    "DISABLED_PLUGINS": ["unwanted_plugin"],
}
```

:::{tip}
The plugin entry point key (`compliance_canada`) is the name used in `ENABLED_PLUGINS` and `DISABLED_PLUGINS`. Choose a clear, unique name for your plugin.
:::

See [How to Use the Plugin System](howto-plugins.md) for the full plugin development guide.

## 13. Putting It All Together

You now have four apps using nearly every feature of django-stratagem. Here's the full picture.

### Architecture overview

```{mermaid}
graph TD
    subgraph platform_core
        Firm
        Subcontractor
        Employee
        SubcontractorEmployee
    end

    subgraph compliance
        CR[ComplianceRegistry]
        OSHA[OshaCompliance]
        HSE[HseCompliance]
        SW[SafeWorkCompliance]
        ISR[InspectionScheduleRegistry]
    end

    subgraph onboarding
        OR[OnboardingRegistry]
        Std[StandardOnboarding]
        Guided[GuidedOnboarding]
        Ent[EnterpriseOnboarding]
    end

    subgraph billing
        BMR[BillingModelRegistry]
        IStraR[InvoicingStrategyRegistry]
    end

    subgraph plugin["django-compliance-canada"]
        CAN[CanadianOhsCompliance]
    end

    Firm -->|"compliance_strategy"| CR
    Employee -->|"onboarding_preference"| OR
    Firm -->|"billing_model"| BMR
    BMR -->|"parent"| IStraR
    CAN -.->|"plugin"| CR
```

### Management commands

Inspect and manage your registries from the command line:

```bash
# List all registries and their implementations
python manage.py list_registries

# JSON output for scripting
python manage.py list_registries --format json

# Clear all registry caches
python manage.py clear_registries_cache

# Re-discover and initialize all registries
python manage.py initialize_registries

# Force re-initialization with cache clearing
python manage.py initialize_registries --force --clear-cache

# Verbose output with health checks
python manage.py initialize_registries -v 2
```

### Feature summary

| Section | Feature | Where it's used |
|---|---|---|
| 2 | Registry, Interface, autodiscovery | ComplianceRegistry - regional safety standards |
| 3 | Model fields, factory, lookups | Firm stores compliance choice in DB |
| 4 | ConditionalInterface, custom Condition | OnboardingRegistry - plan-based access |
| 5 | HierarchicalRegistry, HierarchicalInterface | Billing model to invoicing strategy hierarchy |
| 6 | Form fields, mixins, admin, widgets, list filters | Admin configures firms; employees self-serve |
| 7 | Template tags and filters | Subcontractor dashboard |
| 8 | DRF fields, API views | Mobile app and third-party integrations |
| 9 | TimeWindow, DateRange, FeatureFlag, Group conditions | Inspection scheduling with constraints |
| 10 | validate_implementation, build_implementation_meta, on_register, on_unregister | Audit trail and strict enforcement |
| 11 | Signals | Cross-app cache invalidation and notifications |
| 12 | Plugin entry points | Third-party Canadian compliance module |

### Where to go next

The how-to guides cover each feature in depth:

- [How to Use Model Fields](howto-fields.md) - all field types, lookups, factory patterns
- [How to Use Forms, Widgets, and the Admin](howto-forms-admin.md) - form fields, widgets, admin classes
- [How to Use Conditional Availability](howto-conditions.md) - all built-in conditions, composition, custom conditions
- [How to Use Hierarchical Registries](howto-hierarchies.md) - parent-child relationships
- [How to Use Template Tags and Filters](howto-templates.md) - tags and filters
- [How to Use DRF Integration](howto-drf.md) - serializer fields and API views
- [How to Use the Plugin System](howto-plugins.md) - writing and using plugins
- [Extension Hooks and Customization Points](hooks.md) - hooks, signals, testing
- [Architecture and Design](explanation.md) - how auto-discovery works, design decisions

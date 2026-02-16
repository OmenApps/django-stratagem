# platform_core/views.py
from billing.registry import BillingModelRegistry, InvoicingStrategyRegistry
from compliance.registry import ComplianceRegistry, InspectionScheduleRegistry
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from onboarding.registry import OnboardingRegistry


@login_required
def subcontractor_dashboard(request):
    user = request.user
    role = None
    firm = None
    subcontractor = None
    registry_context = {}
    billing_config = None
    selected_onboarding_slug = None

    if hasattr(user, "employee"):
        role = "employee"
        firm = user.employee.firm
        registry_context = {
            "user": user,
            "firm": firm,
            "request": request,
        }
        selected = user.employee.onboarding_preference
        if selected:
            selected_onboarding_slug = selected.slug
        if hasattr(firm, "billing_config"):
            billing_config = firm.billing_config
    elif hasattr(user, "subcontractoremployee"):
        role = "subcontractor"
        subcontractor = user.subcontractoremployee.subcontractor
        firm = subcontractor.firm
        registry_context = {
            "user": user,
            "firm": firm,
            "request": request,
        }
        if hasattr(firm, "billing_config"):
            billing_config = firm.billing_config

    # Build invoicing strategies grouped by billing model for the template
    selected_billing_slug = None
    selected_invoicing_slug = None
    invoicing_children = {}
    if billing_config:
        bm = billing_config.billing_model
        if bm:
            selected_billing_slug = bm.slug
        inv = billing_config.invoicing_strategy
        if inv:
            selected_invoicing_slug = inv.slug
        invoicing_children = InvoicingStrategyRegistry.get_children_for_parent(selected_billing_slug)

    # Build inspection schedule data with condition details
    inspection_schedules = []
    for slug, meta in sorted(
        InspectionScheduleRegistry.implementations.items(),
        key=lambda item: item[1].get("priority", 0),
    ):
        impl_class = meta["klass"]
        condition = getattr(impl_class, "condition", None)
        if condition:
            available, detail = condition.check_with_details(registry_context)
            explanation = condition.explain()
        else:
            available = True
            detail = "No condition - always available"
            explanation = "Always available"
        inspection_schedules.append({
            "slug": slug,
            "name": meta.get("description", impl_class.__name__),
            "available": available,
            "detail": detail,
            "explanation": explanation,
            "priority": meta.get("priority", 0),
        })

    return render(request, "dashboard/subcontractor.html", {
        "compliance_registry": ComplianceRegistry,
        "onboarding_registry": OnboardingRegistry,
        "billing_model_registry": BillingModelRegistry,
        "request_context": registry_context,
        "role": role,
        "firm": firm,
        "subcontractor": subcontractor,
        "selected_onboarding_slug": selected_onboarding_slug,
        "billing_config": billing_config,
        "selected_billing_slug": selected_billing_slug,
        "selected_invoicing_slug": selected_invoicing_slug,
        "invoicing_children": invoicing_children,
        "inspection_schedules": inspection_schedules,
    })

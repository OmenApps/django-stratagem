# onboarding/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from onboarding.forms import OnboardingPreferenceForm


@login_required
def onboarding_settings(request):
    employee = getattr(request.user, "employee", None)
    firm = employee.firm if employee else None
    context = {}
    initial = {}

    if employee:
        context = {
            "user": request.user,
            "firm": firm,
            "request": request,
        }
        current = employee.onboarding_preference
        if current:
            initial = {"workflow": current.slug}

    form = OnboardingPreferenceForm(
        data=request.POST or None,
        initial=initial,
        registry_context=context,
    )

    if request.method == "POST" and form.is_valid():
        if employee:
            employee.onboarding_preference = form.cleaned_data["workflow"]
            employee.save(update_fields=["onboarding_preference"])
        return redirect("onboarding-settings")

    return render(request, "onboarding/settings.html", {"form": form, "firm": firm})

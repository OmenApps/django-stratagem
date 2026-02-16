# How to Use Conditional Availability

Implementations can be conditionally available based on permissions, feature flags, settings, or arbitrary callables.

## ConditionalInterface

Subclass `ConditionalInterface` instead of `Interface` and set the `condition` class attribute:

```python
from django_stratagem import ConditionalInterface, PermissionCondition

class AdminNotification(ConditionalInterface):
    registry = NotificationRegistry
    slug = "admin_only"
    description = "Admin-only notification channel"
    condition = PermissionCondition("myapp.admin_notifications")

    def send(self, message, recipient):
        ...
```

The `is_available(context)` classmethod checks whether the implementation's conditions are satisfied:

```python
context = {"user": request.user, "request": request}
AdminNotification.is_available(context)  # True/False
```

## Condition Base Class

All conditions extend `Condition` and implement `is_met(context) -> bool`:

```python
from django_stratagem import Condition

class MyCondition(Condition):
    def is_met(self, context: dict) -> bool:
        return context.get("some_key") == "some_value"

    def explain(self) -> str:
        return "MyCondition(some_key=some_value)"
```

Additional methods:

- `explain() -> str` - Human-readable description
- `check_with_details(context) -> tuple[bool, str]` - Returns result with explanation (useful for debugging)

## Built-in Conditions

### PermissionCondition

Checks `user.has_perm()` against a Django permission string.

```python
PermissionCondition("myapp.can_send_sms")
```

The `context` dict must include a `"user"` key with an authenticated user.

### FeatureFlagCondition

Checks a feature flag. Supports `settings.FEATURE_FLAGS` dict or django-waffle.

```python
FeatureFlagCondition("enable_push_notifications")
```

With waffle, the `context` dict must include a `"request"` key.

### SettingCondition

Checks if a Django setting matches an expected value.

```python
SettingCondition("DEBUG", True)
SettingCondition("NOTIFICATION_BACKEND", "production")
```

### CallableCondition

Wraps any `(context) -> bool` callable.

```python
CallableCondition(lambda ctx: ctx.get("user") and ctx["user"].is_staff)
```

### AuthenticatedCondition

Checks that the user in context is authenticated. Works safely with `AnonymousUser`, mock users, or missing user keys.

```python
AuthenticatedCondition()
```

The `context` dict must include a `"user"` key.

### StaffCondition

Checks that the user is a staff member (`is_staff`).

```python
StaffCondition()
```

### SuperuserCondition

Checks that the user is a superuser (`is_superuser`).

```python
SuperuserCondition()
```

### GroupCondition

Checks that the user belongs to a specific Django auth group.

```python
GroupCondition("editors")
```

Calls `user.groups.filter(name=...).exists()` internally.

### TimeWindowCondition

Checks if the current local time falls within a window. Handles overnight windows (e.g. 22:00-06:00) and optional day-of-week filtering using Python weekday convention (0=Monday, 6=Sunday).

```python
from datetime import time

# Business hours, weekdays only
TimeWindowCondition(time(9, 0), time(17, 0), days=[0, 1, 2, 3, 4])

# Overnight maintenance window, every day
TimeWindowCondition(time(2, 0), time(5, 0))
```

### DateRangeCondition

Checks if the current local date is within a range (inclusive on both ends). Either bound can be `None` for an open-ended range.

```python
from datetime import date

# Available only during Q1 2026
DateRangeCondition(date(2026, 1, 1), date(2026, 3, 31))

# Available from launch date onward
DateRangeCondition(start_date=date(2026, 6, 1))

# Available until sunset date
DateRangeCondition(end_date=date(2026, 12, 31))
```

### EnvironmentCondition

Checks an environment variable. If `expected_value` is not provided, checks that the variable exists and is non-empty. If provided, checks for an exact string match.

```python
# Just check that it's set
EnvironmentCondition("FEATURE_X_ENABLED")

# Check exact value
EnvironmentCondition("DEPLOY_ENV", "production")
```

## Composing Conditions

Conditions support `&` (AND), `|` (OR), and `~` (NOT) operators:

```python
from django_stratagem import PermissionCondition, FeatureFlagCondition

# Must have permission AND feature flag enabled
condition = PermissionCondition("myapp.send") & FeatureFlagCondition("notifications_v2")

# Either permission OR staff status
condition = PermissionCondition("myapp.send") | CallableCondition(lambda ctx: ctx.get("user", None) and ctx["user"].is_staff)

# NOT a condition
condition = ~SettingCondition("MAINTENANCE_MODE", True)
```

Compound conditions can also be created directly:

```python
from django_stratagem import AllConditions, AnyCondition, NotCondition

AllConditions([cond1, cond2, cond3])  # All must pass
AnyCondition([cond1, cond2, cond3])   # At least one must pass
NotCondition(cond1)                    # Must fail
```

## Context-Aware Registry Methods

Registries containing `ConditionalInterface` subclasses have extra methods that filter by a `context` dict:

```python
context = {"user": request.user, "request": request}

# Get only available implementations
available = NotificationRegistry.get_available_implementations(context)
# {"email": <class EmailNotification>, ...}

# Get choices filtered by context
choices = NotificationRegistry.get_choices_for_context(context)
# [("email", "Email Notification"), ...]

# Get implementation with context check and fallback
impl = NotificationRegistry.get_for_context(
    context,
    slug="admin_only",
    fallback="email",
)
```

## Writing Custom Conditions

### Database-Backed Conditions

Check a database value, like whether a tenant's plan includes a feature:

```python
from django_stratagem import Condition

class TenantPlanCondition(Condition):
    def __init__(self, required_plan):
        self.required_plan = required_plan

    def is_met(self, context):
        tenant = context.get("tenant")
        if not tenant:
            return False
        # Assumes tenant has a .plan attribute
        return tenant.plan in self.required_plan

    def explain(self):
        return f"Tenant plan must be one of: {self.required_plan}"
```

Usage:

```python
class PremiumExport(ConditionalInterface):
    registry = ExportRegistry
    slug = "premium_export"
    condition = TenantPlanCondition(["business", "enterprise"])
```

### Combining Custom and Built-in Conditions

Conditions compose with `&`, `|`, and `~`:

```python
from django_stratagem import PermissionCondition, FeatureFlagCondition

class EnterpriseExport(ConditionalInterface):
    registry = ExportRegistry
    slug = "enterprise_export"
    condition = (
        TenantPlanCondition(["enterprise"])
        & PermissionCondition("exports.use_enterprise")
        & FeatureFlagCondition("enterprise_exports_enabled")
    )
```

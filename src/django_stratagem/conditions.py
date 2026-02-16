import datetime
import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class Condition(ABC):
    """Base class for implementation conditions."""

    @abstractmethod
    def is_met(self, context: dict[str, Any]) -> bool:
        """Check if the condition is met given the context."""

    def explain(self) -> str:
        """Return a human-readable description of this condition."""
        return f"{type(self).__name__}"

    def check_with_details(self, context: dict[str, Any]) -> tuple[bool, str]:
        """Check the condition and return (result, explanation).

        Useful for debugging why a condition passed or failed.
        """
        result = self.is_met(context)
        status = "passed" if result else "failed"
        explanation = f"{self.explain()} -> {status}"
        logger.debug("Condition check: %s", explanation)
        return result, explanation

    def __and__(self, other: "Condition") -> "CompoundCondition":
        """Combine conditions with AND logic."""
        return AllConditions([self, other])

    def __or__(self, other: "Condition") -> "CompoundCondition":
        """Combine conditions with OR logic."""
        return AnyCondition([self, other])

    def __invert__(self) -> "NotCondition":
        """Negate the condition."""
        return NotCondition(self)


class CompoundCondition(Condition):
    """Base class for compound conditions."""

    def __init__(self, conditions: list[Condition]):
        self.conditions = conditions

    def is_met(self, context: dict[str, Any]) -> bool:
        """Check if the compound condition is met."""
        raise NotImplementedError("Subclasses must implement this method.")


class AllConditions(CompoundCondition):
    """All conditions must be met."""

    def is_met(self, context: dict[str, Any]) -> bool:
        return all(cond.is_met(context) for cond in self.conditions)

    def explain(self) -> str:
        parts = " AND ".join(c.explain() for c in self.conditions)
        return f"({parts})"

    def check_with_details(self, context: dict[str, Any]) -> tuple[bool, str]:
        details = []
        all_met = True
        for cond in self.conditions:
            result, detail = cond.check_with_details(context)
            details.append(detail)
            if not result:
                all_met = False
        explanation = f"AllConditions({'passed' if all_met else 'failed'}): [{', '.join(details)}]"
        logger.debug("Condition check: %s", explanation)
        return all_met, explanation


class AnyCondition(CompoundCondition):
    """At least one condition must be met."""

    def is_met(self, context: dict[str, Any]) -> bool:
        return any(cond.is_met(context) for cond in self.conditions)

    def explain(self) -> str:
        parts = " OR ".join(c.explain() for c in self.conditions)
        return f"({parts})"

    def check_with_details(self, context: dict[str, Any]) -> tuple[bool, str]:
        details = []
        any_met = False
        for cond in self.conditions:
            result, detail = cond.check_with_details(context)
            details.append(detail)
            if result:
                any_met = True
        explanation = f"AnyCondition({'passed' if any_met else 'failed'}): [{', '.join(details)}]"
        logger.debug("Condition check: %s", explanation)
        return any_met, explanation


class NotCondition(Condition):
    """Negates a condition."""

    def __init__(self, condition: Condition):
        self.condition = condition

    def is_met(self, context: dict[str, Any]) -> bool:
        return not self.condition.is_met(context)

    def explain(self) -> str:
        return f"NOT({self.condition.explain()})"

    def check_with_details(self, context: dict[str, Any]) -> tuple[bool, str]:
        inner_result, inner_detail = self.condition.check_with_details(context)
        result = not inner_result
        explanation = f"NotCondition({'passed' if result else 'failed'}): [{inner_detail}]"
        logger.debug("Condition check: %s", explanation)
        return result, explanation


class FeatureFlagCondition(Condition):
    """Check if a feature flag is enabled."""

    def __init__(self, flag_name: str):
        self.flag_name = flag_name

    def explain(self) -> str:
        return f"FeatureFlag({self.flag_name})"

    def is_met(self, context: dict[str, Any]) -> bool:
        # Check django-waffle or similar feature flag system
        if hasattr(settings, "FEATURE_FLAGS"):
            return settings.FEATURE_FLAGS.get(self.flag_name, False)

        # Or use a feature flag service
        try:
            from waffle import flag_is_active  # type: ignore[import-untyped]

            request = context.get("request")
            if request:
                return flag_is_active(request, self.flag_name)
        except ImportError:
            pass

        return False


class PermissionCondition(Condition):
    """Check if user has specific permission."""

    def __init__(self, permission: str):
        self.permission = permission

    def explain(self) -> str:
        return f"Permission({self.permission})"

    def is_met(self, context: dict[str, Any]) -> bool:
        from django.contrib.auth.models import AnonymousUser

        user = context.get("user")
        if not user or isinstance(user, AnonymousUser):
            return False
        return user.has_perm(self.permission)


class SettingCondition(Condition):
    """Check if a Django setting matches a value."""

    def __init__(self, setting_name: str, expected_value: Any):
        self.setting_name = setting_name
        self.expected_value = expected_value

    def explain(self) -> str:
        return f"Setting({self.setting_name}={self.expected_value!r})"

    def is_met(self, context: dict[str, Any]) -> bool:
        actual_value = getattr(settings, self.setting_name, None)
        return actual_value == self.expected_value


class CallableCondition(Condition):
    """Use a custom callable for condition checking."""

    def __init__(self, check_func: Callable[[dict[str, Any]], bool]):
        self.check_func = check_func

    def explain(self) -> str:
        name = getattr(self.check_func, "__name__", repr(self.check_func))
        return f"Callable({name})"

    def is_met(self, context: dict[str, Any]) -> bool:
        return self.check_func(context)


# --- Auth conditions ---


class AuthenticatedCondition(Condition):
    """Check if the user is authenticated."""

    def explain(self) -> str:
        return "Authenticated"

    def is_met(self, context: dict[str, Any]) -> bool:
        user = context.get("user")
        if user is None:
            return False
        return getattr(user, "is_authenticated", False)


class StaffCondition(Condition):
    """Check if the user is a staff member."""

    def explain(self) -> str:
        return "Staff"

    def is_met(self, context: dict[str, Any]) -> bool:
        user = context.get("user")
        if user is None:
            return False
        return getattr(user, "is_staff", False)


class SuperuserCondition(Condition):
    """Check if the user is a superuser."""

    def explain(self) -> str:
        return "Superuser"

    def is_met(self, context: dict[str, Any]) -> bool:
        user = context.get("user")
        if user is None:
            return False
        return getattr(user, "is_superuser", False)


class GroupCondition(Condition):
    """Check if the user belongs to a specific group."""

    def __init__(self, group_name: str):
        self.group_name = group_name

    def explain(self) -> str:
        return f"Group({self.group_name})"

    def is_met(self, context: dict[str, Any]) -> bool:
        user = context.get("user")
        if user is None:
            return False
        groups = getattr(user, "groups", None)
        if groups is None:
            return False
        return groups.filter(name=self.group_name).exists()


# --- Time conditions ---


class TimeWindowCondition(Condition):
    """Check if the current local time is within a time window.

    Handles overnight windows (e.g., start=22:00, end=06:00).
    ``days`` uses Python weekday convention (0=Monday, 6=Sunday).
    Pass ``None`` for ``days`` to allow every day.
    """

    def __init__(
        self,
        start_time: datetime.time,
        end_time: datetime.time,
        days: list[int] | None = None,
    ):
        self.start_time = start_time
        self.end_time = end_time
        self.days = days

    def explain(self) -> str:
        days_str = f", days={self.days}" if self.days is not None else ""
        return f"TimeWindow({self.start_time}-{self.end_time}{days_str})"

    def is_met(self, context: dict[str, Any]) -> bool:
        now = timezone.localtime()
        if self.days is not None and now.weekday() not in self.days:
            return False
        current_time = now.time()
        if self.start_time <= self.end_time:
            return self.start_time <= current_time <= self.end_time
        # Overnight window (e.g. 22:00 - 06:00)
        return current_time >= self.start_time or current_time <= self.end_time


class DateRangeCondition(Condition):
    """Check if the current local date is within a date range (inclusive).

    Either bound can be ``None`` for an open-ended range.
    """

    def __init__(
        self,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
    ):
        self.start_date = start_date
        self.end_date = end_date

    def explain(self) -> str:
        start = str(self.start_date) if self.start_date else "*"
        end = str(self.end_date) if self.end_date else "*"
        return f"DateRange({start} to {end})"

    def is_met(self, context: dict[str, Any]) -> bool:
        today = timezone.localdate()
        if self.start_date is not None and today < self.start_date:
            return False
        if self.end_date is not None and today > self.end_date:
            return False
        return True


# --- Environment conditions ---


class EnvironmentCondition(Condition):
    """Check an environment variable.

    If ``expected_value`` is ``None``, checks that the variable exists and is
    non-empty. Otherwise checks for an exact string match.
    """

    def __init__(self, env_var: str, expected_value: str | None = None):
        self.env_var = env_var
        self.expected_value = expected_value

    def explain(self) -> str:
        if self.expected_value is not None:
            return f"Environment({self.env_var}={self.expected_value!r})"
        return f"Environment({self.env_var})"

    def is_met(self, context: dict[str, Any]) -> bool:
        value = os.environ.get(self.env_var)
        if self.expected_value is not None:
            return value == self.expected_value
        return bool(value)

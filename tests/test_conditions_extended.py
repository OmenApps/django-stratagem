"""Extended tests for django_stratagem conditions module.

Covers FeatureFlagCondition, SettingCondition, CompoundCondition base class,
and the new Auth, Time, and Environment conditions.
"""

from __future__ import annotations

import datetime
import os
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from django_stratagem.conditions import (
    AllConditions,
    AnyCondition,
    AuthenticatedCondition,
    CallableCondition,
    CompoundCondition,
    DateRangeCondition,
    EnvironmentCondition,
    FeatureFlagCondition,
    GroupCondition,
    NotCondition,
    PermissionCondition,
    SettingCondition,
    StaffCondition,
    SuperuserCondition,
    TimeWindowCondition,
)


class TestFeatureFlagCondition:
    """Tests for FeatureFlagCondition."""

    @override_settings(FEATURE_FLAGS={"my_flag": True})
    def test_flag_enabled_returns_true(self):
        condition = FeatureFlagCondition("my_flag")
        assert condition.is_met({}) is True

    @override_settings(FEATURE_FLAGS={"my_flag": False})
    def test_flag_disabled_returns_false(self):
        condition = FeatureFlagCondition("my_flag")
        assert condition.is_met({}) is False

    @override_settings(FEATURE_FLAGS={"other_flag": True})
    def test_missing_flag_returns_false(self):
        condition = FeatureFlagCondition("my_flag")
        assert condition.is_met({}) is False

    def test_no_feature_flags_setting_no_waffle_returns_false(self):
        # Without FEATURE_FLAGS setting and without waffle installed
        condition = FeatureFlagCondition("my_flag")
        assert condition.is_met({}) is False


class TestSettingCondition:
    """Tests for SettingCondition."""

    @override_settings(MY_SETTING="expected_value")
    def test_setting_matches_returns_true(self):
        condition = SettingCondition("MY_SETTING", "expected_value")
        assert condition.is_met({}) is True

    @override_settings(MY_SETTING="other_value")
    def test_setting_differs_returns_false(self):
        condition = SettingCondition("MY_SETTING", "expected_value")
        assert condition.is_met({}) is False

    def test_setting_not_defined_returns_false(self):
        condition = SettingCondition("NONEXISTENT_SETTING_12345", "any_value")
        assert condition.is_met({}) is False


class TestCompoundConditionBase:
    """Tests for CompoundCondition base class."""

    def test_direct_is_met_raises_not_implemented(self):
        cond = CallableCondition(lambda ctx: True)
        compound = CompoundCondition([cond])
        with pytest.raises(NotImplementedError):
            compound.is_met({})


# --- Auth condition tests ---


class TestAuthenticatedCondition:
    """Tests for AuthenticatedCondition."""

    def test_authenticated_user_returns_true(self):
        user = type("User", (), {"is_authenticated": True})()
        condition = AuthenticatedCondition()
        assert condition.is_met({"user": user}) is True

    def test_unauthenticated_user_returns_false(self):
        user = type("User", (), {"is_authenticated": False})()
        condition = AuthenticatedCondition()
        assert condition.is_met({"user": user}) is False

    def test_no_user_in_context_returns_false(self):
        condition = AuthenticatedCondition()
        assert condition.is_met({}) is False

    def test_none_user_returns_false(self):
        condition = AuthenticatedCondition()
        assert condition.is_met({"user": None}) is False

    def test_user_without_is_authenticated_returns_false(self):
        user = type("User", (), {})()
        condition = AuthenticatedCondition()
        assert condition.is_met({"user": user}) is False

    def test_explain(self):
        condition = AuthenticatedCondition()
        assert condition.explain() == "Authenticated"


class TestStaffCondition:
    """Tests for StaffCondition."""

    def test_staff_user_returns_true(self):
        user = type("User", (), {"is_staff": True})()
        condition = StaffCondition()
        assert condition.is_met({"user": user}) is True

    def test_non_staff_user_returns_false(self):
        user = type("User", (), {"is_staff": False})()
        condition = StaffCondition()
        assert condition.is_met({"user": user}) is False

    def test_no_user_in_context_returns_false(self):
        condition = StaffCondition()
        assert condition.is_met({}) is False

    def test_none_user_returns_false(self):
        condition = StaffCondition()
        assert condition.is_met({"user": None}) is False

    def test_user_without_is_staff_returns_false(self):
        user = type("User", (), {})()
        condition = StaffCondition()
        assert condition.is_met({"user": user}) is False

    def test_explain(self):
        condition = StaffCondition()
        assert condition.explain() == "Staff"


class TestSuperuserCondition:
    """Tests for SuperuserCondition."""

    def test_superuser_returns_true(self):
        user = type("User", (), {"is_superuser": True})()
        condition = SuperuserCondition()
        assert condition.is_met({"user": user}) is True

    def test_non_superuser_returns_false(self):
        user = type("User", (), {"is_superuser": False})()
        condition = SuperuserCondition()
        assert condition.is_met({"user": user}) is False

    def test_no_user_in_context_returns_false(self):
        condition = SuperuserCondition()
        assert condition.is_met({}) is False

    def test_none_user_returns_false(self):
        condition = SuperuserCondition()
        assert condition.is_met({"user": None}) is False

    def test_user_without_is_superuser_returns_false(self):
        user = type("User", (), {})()
        condition = SuperuserCondition()
        assert condition.is_met({"user": user}) is False

    def test_explain(self):
        condition = SuperuserCondition()
        assert condition.explain() == "Superuser"


class TestGroupCondition:
    """Tests for GroupCondition."""

    def test_user_in_group_returns_true(self):
        groups = MagicMock()
        groups.filter.return_value.exists.return_value = True
        user = type("User", (), {"groups": groups})()
        condition = GroupCondition("editors")
        assert condition.is_met({"user": user}) is True
        groups.filter.assert_called_once_with(name="editors")

    def test_user_not_in_group_returns_false(self):
        groups = MagicMock()
        groups.filter.return_value.exists.return_value = False
        user = type("User", (), {"groups": groups})()
        condition = GroupCondition("editors")
        assert condition.is_met({"user": user}) is False

    def test_no_user_in_context_returns_false(self):
        condition = GroupCondition("editors")
        assert condition.is_met({}) is False

    def test_none_user_returns_false(self):
        condition = GroupCondition("editors")
        assert condition.is_met({"user": None}) is False

    def test_user_without_groups_attr_returns_false(self):
        user = type("User", (), {})()
        condition = GroupCondition("editors")
        assert condition.is_met({"user": user}) is False

    def test_explain(self):
        condition = GroupCondition("editors")
        assert condition.explain() == "Group(editors)"


# --- Time condition tests ---


def _make_datetime(year, month, day, hour, minute):
    """Helper to create a timezone-aware datetime."""
    from django.utils import timezone as tz

    return tz.make_aware(datetime.datetime(year, month, day, hour, minute))


class TestTimeWindowCondition:
    """Tests for TimeWindowCondition."""

    def test_within_normal_window(self):
        condition = TimeWindowCondition(datetime.time(9, 0), datetime.time(17, 0))
        now = _make_datetime(2026, 1, 5, 12, 0)  # Monday noon
        with patch("django_stratagem.conditions.timezone.localtime", return_value=now):
            assert condition.is_met({}) is True

    def test_outside_normal_window(self):
        condition = TimeWindowCondition(datetime.time(9, 0), datetime.time(17, 0))
        now = _make_datetime(2026, 1, 5, 20, 0)  # Monday 8pm
        with patch("django_stratagem.conditions.timezone.localtime", return_value=now):
            assert condition.is_met({}) is False

    def test_at_start_boundary(self):
        condition = TimeWindowCondition(datetime.time(9, 0), datetime.time(17, 0))
        now = _make_datetime(2026, 1, 5, 9, 0)
        with patch("django_stratagem.conditions.timezone.localtime", return_value=now):
            assert condition.is_met({}) is True

    def test_at_end_boundary(self):
        condition = TimeWindowCondition(datetime.time(9, 0), datetime.time(17, 0))
        now = _make_datetime(2026, 1, 5, 17, 0)
        with patch("django_stratagem.conditions.timezone.localtime", return_value=now):
            assert condition.is_met({}) is True

    def test_overnight_window_evening(self):
        condition = TimeWindowCondition(datetime.time(22, 0), datetime.time(6, 0))
        now = _make_datetime(2026, 1, 5, 23, 0)  # 11pm
        with patch("django_stratagem.conditions.timezone.localtime", return_value=now):
            assert condition.is_met({}) is True

    def test_overnight_window_morning(self):
        condition = TimeWindowCondition(datetime.time(22, 0), datetime.time(6, 0))
        now = _make_datetime(2026, 1, 6, 5, 0)  # 5am
        with patch("django_stratagem.conditions.timezone.localtime", return_value=now):
            assert condition.is_met({}) is True

    def test_overnight_window_outside(self):
        condition = TimeWindowCondition(datetime.time(22, 0), datetime.time(6, 0))
        now = _make_datetime(2026, 1, 5, 12, 0)  # noon
        with patch("django_stratagem.conditions.timezone.localtime", return_value=now):
            assert condition.is_met({}) is False

    def test_day_filter_matching(self):
        condition = TimeWindowCondition(datetime.time(9, 0), datetime.time(17, 0), days=[0, 1, 2, 3, 4])
        now = _make_datetime(2026, 1, 5, 12, 0)  # Monday
        with patch("django_stratagem.conditions.timezone.localtime", return_value=now):
            assert condition.is_met({}) is True

    def test_day_filter_not_matching(self):
        condition = TimeWindowCondition(datetime.time(9, 0), datetime.time(17, 0), days=[0, 1, 2, 3, 4])
        now = _make_datetime(2026, 1, 3, 12, 0)  # Saturday
        with patch("django_stratagem.conditions.timezone.localtime", return_value=now):
            assert condition.is_met({}) is False

    def test_no_day_filter_allows_any_day(self):
        condition = TimeWindowCondition(datetime.time(9, 0), datetime.time(17, 0))
        now = _make_datetime(2026, 1, 4, 12, 0)  # Sunday
        with patch("django_stratagem.conditions.timezone.localtime", return_value=now):
            assert condition.is_met({}) is True

    def test_explain_without_days(self):
        condition = TimeWindowCondition(datetime.time(9, 0), datetime.time(17, 0))
        assert condition.explain() == "TimeWindow(09:00:00-17:00:00)"

    def test_explain_with_days(self):
        condition = TimeWindowCondition(datetime.time(9, 0), datetime.time(17, 0), days=[0, 1])
        assert condition.explain() == "TimeWindow(09:00:00-17:00:00, days=[0, 1])"


class TestDateRangeCondition:
    """Tests for DateRangeCondition."""

    def test_within_range(self):
        condition = DateRangeCondition(datetime.date(2026, 1, 1), datetime.date(2026, 12, 31))
        with patch("django_stratagem.conditions.timezone.localdate", return_value=datetime.date(2026, 6, 15)):
            assert condition.is_met({}) is True

    def test_before_range(self):
        condition = DateRangeCondition(datetime.date(2026, 6, 1), datetime.date(2026, 12, 31))
        with patch("django_stratagem.conditions.timezone.localdate", return_value=datetime.date(2026, 1, 1)):
            assert condition.is_met({}) is False

    def test_after_range(self):
        condition = DateRangeCondition(datetime.date(2026, 1, 1), datetime.date(2026, 6, 30))
        with patch("django_stratagem.conditions.timezone.localdate", return_value=datetime.date(2026, 12, 1)):
            assert condition.is_met({}) is False

    def test_at_start_boundary(self):
        condition = DateRangeCondition(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))
        with patch("django_stratagem.conditions.timezone.localdate", return_value=datetime.date(2026, 3, 1)):
            assert condition.is_met({}) is True

    def test_at_end_boundary(self):
        condition = DateRangeCondition(datetime.date(2026, 3, 1), datetime.date(2026, 3, 31))
        with patch("django_stratagem.conditions.timezone.localdate", return_value=datetime.date(2026, 3, 31)):
            assert condition.is_met({}) is True

    def test_open_start(self):
        condition = DateRangeCondition(end_date=datetime.date(2026, 12, 31))
        with patch("django_stratagem.conditions.timezone.localdate", return_value=datetime.date(2020, 1, 1)):
            assert condition.is_met({}) is True

    def test_open_end(self):
        condition = DateRangeCondition(start_date=datetime.date(2026, 1, 1))
        with patch("django_stratagem.conditions.timezone.localdate", return_value=datetime.date(2030, 12, 31)):
            assert condition.is_met({}) is True

    def test_fully_open(self):
        condition = DateRangeCondition()
        with patch("django_stratagem.conditions.timezone.localdate", return_value=datetime.date(2026, 6, 15)):
            assert condition.is_met({}) is True

    def test_explain_with_both_dates(self):
        condition = DateRangeCondition(datetime.date(2026, 1, 1), datetime.date(2026, 12, 31))
        assert condition.explain() == "DateRange(2026-01-01 to 2026-12-31)"

    def test_explain_open_start(self):
        condition = DateRangeCondition(end_date=datetime.date(2026, 12, 31))
        assert condition.explain() == "DateRange(* to 2026-12-31)"

    def test_explain_open_end(self):
        condition = DateRangeCondition(start_date=datetime.date(2026, 1, 1))
        assert condition.explain() == "DateRange(2026-01-01 to *)"


# --- Environment condition tests ---


class TestEnvironmentCondition:
    """Tests for EnvironmentCondition."""

    def test_env_var_exists_and_nonempty(self):
        condition = EnvironmentCondition("MY_VAR")
        with patch.dict(os.environ, {"MY_VAR": "some_value"}):
            assert condition.is_met({}) is True

    def test_env_var_missing(self):
        condition = EnvironmentCondition("MY_VAR")
        env = os.environ.copy()
        env.pop("MY_VAR", None)
        with patch.dict(os.environ, env, clear=True):
            assert condition.is_met({}) is False

    def test_env_var_empty_string(self):
        condition = EnvironmentCondition("MY_VAR")
        with patch.dict(os.environ, {"MY_VAR": ""}):
            assert condition.is_met({}) is False

    def test_exact_match_success(self):
        condition = EnvironmentCondition("MY_VAR", "production")
        with patch.dict(os.environ, {"MY_VAR": "production"}):
            assert condition.is_met({}) is True

    def test_exact_match_failure(self):
        condition = EnvironmentCondition("MY_VAR", "production")
        with patch.dict(os.environ, {"MY_VAR": "staging"}):
            assert condition.is_met({}) is False

    def test_exact_match_missing_var(self):
        condition = EnvironmentCondition("MY_VAR", "production")
        env = os.environ.copy()
        env.pop("MY_VAR", None)
        with patch.dict(os.environ, env, clear=True):
            assert condition.is_met({}) is False

    def test_explain_without_expected(self):
        condition = EnvironmentCondition("MY_VAR")
        assert condition.explain() == "Environment(MY_VAR)"

    def test_explain_with_expected(self):
        condition = EnvironmentCondition("MY_VAR", "production")
        assert condition.explain() == "Environment(MY_VAR='production')"


# --- Composition tests ---


class TestNewConditionComposition:
    """Verify that new conditions compose with &, |, ~ operators."""

    def test_and_composition(self):
        condition = AuthenticatedCondition() & StaffCondition()
        user = type("User", (), {"is_authenticated": True, "is_staff": True})()
        assert condition.is_met({"user": user}) is True

    def test_and_composition_partial(self):
        condition = AuthenticatedCondition() & StaffCondition()
        user = type("User", (), {"is_authenticated": True, "is_staff": False})()
        assert condition.is_met({"user": user}) is False

    def test_or_composition(self):
        condition = StaffCondition() | SuperuserCondition()
        user = type("User", (), {"is_staff": False, "is_superuser": True})()
        assert condition.is_met({"user": user}) is True

    def test_or_composition_neither(self):
        condition = StaffCondition() | SuperuserCondition()
        user = type("User", (), {"is_staff": False, "is_superuser": False})()
        assert condition.is_met({"user": user}) is False

    def test_not_composition(self):
        condition = ~SuperuserCondition()
        user = type("User", (), {"is_superuser": False})()
        assert condition.is_met({"user": user}) is True

    def test_not_composition_negated(self):
        condition = ~SuperuserCondition()
        user = type("User", (), {"is_superuser": True})()
        assert condition.is_met({"user": user}) is False

    def test_complex_composition(self):
        condition = AuthenticatedCondition() & (StaffCondition() | SuperuserCondition())
        user = type("User", (), {"is_authenticated": True, "is_staff": False, "is_superuser": True})()
        assert condition.is_met({"user": user}) is True

    def test_mixed_old_and_new_conditions(self):
        condition = AuthenticatedCondition() & PermissionCondition("myapp.view")
        user = MagicMock()
        user.is_authenticated = True
        user.has_perm.return_value = True
        assert condition.is_met({"user": user}) is True


# --- check_with_details() tests ---


class TestCheckWithDetails:
    """Tests for check_with_details() on base and compound conditions."""

    def test_base_condition_passed(self):
        """CallableCondition.check_with_details returns (True, '...passed')."""
        cond = CallableCondition(lambda ctx: True)
        result, explanation = cond.check_with_details({})
        assert result is True
        assert "passed" in explanation

    def test_base_condition_failed(self):
        """CallableCondition.check_with_details returns (False, '...failed')."""
        cond = CallableCondition(lambda ctx: False)
        result, explanation = cond.check_with_details({})
        assert result is False
        assert "failed" in explanation

    def test_all_conditions_all_pass(self):
        """AllConditions.check_with_details aggregates sub-results when all pass."""
        cond1 = CallableCondition(lambda ctx: True)
        cond2 = CallableCondition(lambda ctx: True)
        compound = AllConditions([cond1, cond2])
        result, explanation = compound.check_with_details({})
        assert result is True
        assert "AllConditions(passed)" in explanation

    def test_all_conditions_one_fails(self):
        """AllConditions.check_with_details reports failure when one sub-condition fails."""
        cond1 = CallableCondition(lambda ctx: True)
        cond2 = CallableCondition(lambda ctx: False)
        compound = AllConditions([cond1, cond2])
        result, explanation = compound.check_with_details({})
        assert result is False
        assert "AllConditions(failed)" in explanation

    def test_any_condition_one_passes(self):
        """AnyCondition.check_with_details reports passed when one sub-condition passes."""
        cond1 = CallableCondition(lambda ctx: False)
        cond2 = CallableCondition(lambda ctx: True)
        compound = AnyCondition([cond1, cond2])
        result, explanation = compound.check_with_details({})
        assert result is True
        assert "AnyCondition(passed)" in explanation

    def test_any_condition_none_pass(self):
        """AnyCondition.check_with_details reports failure when none pass."""
        cond1 = CallableCondition(lambda ctx: False)
        cond2 = CallableCondition(lambda ctx: False)
        compound = AnyCondition([cond1, cond2])
        result, explanation = compound.check_with_details({})
        assert result is False
        assert "AnyCondition(failed)" in explanation

    def test_not_condition_inverts(self):
        """NotCondition.check_with_details inverts the inner result."""
        inner = CallableCondition(lambda ctx: True)
        not_cond = NotCondition(inner)
        result, explanation = not_cond.check_with_details({})
        assert result is False
        assert "NotCondition(failed)" in explanation

        inner_false = CallableCondition(lambda ctx: False)
        not_cond2 = NotCondition(inner_false)
        result2, explanation2 = not_cond2.check_with_details({})
        assert result2 is True
        assert "NotCondition(passed)" in explanation2


# --- explain() gap tests ---


class TestExplainMethods:
    """Tests for explain() on condition types not yet covered."""

    @override_settings(FEATURE_FLAGS={"beta": True})
    def test_feature_flag_explain(self):
        """FeatureFlagCondition.explain returns 'FeatureFlag(flag_name)'."""
        cond = FeatureFlagCondition("beta")
        assert cond.explain() == "FeatureFlag(beta)"

    def test_permission_explain(self):
        """PermissionCondition.explain returns 'Permission(perm)'."""
        cond = PermissionCondition("app.can_edit")
        assert cond.explain() == "Permission(app.can_edit)"

    @override_settings(MY_SETTING="hello")
    def test_setting_explain(self):
        """SettingCondition.explain returns 'Setting(name='value')'."""
        cond = SettingCondition("MY_SETTING", "hello")
        assert cond.explain() == "Setting(MY_SETTING='hello')"

    def test_callable_explain_named_function(self):
        """CallableCondition.explain uses __name__ for named functions."""

        def my_check(ctx):
            return True

        cond = CallableCondition(my_check)
        assert cond.explain() == "Callable(my_check)"

    def test_callable_explain_lambda(self):
        """CallableCondition.explain uses repr() fallback for lambdas."""
        cond = CallableCondition(lambda ctx: True)
        explanation = cond.explain()
        assert explanation.startswith("Callable(")
        assert "lambda" in explanation

    def test_compound_explain(self):
        """AllConditions, AnyCondition, NotCondition explain() produce correct strings."""
        cond_a = CallableCondition(lambda ctx: True)
        cond_b = PermissionCondition("app.view")

        all_cond = AllConditions([cond_a, cond_b])
        all_explain = all_cond.explain()
        assert "AND" in all_explain
        assert "Permission(app.view)" in all_explain

        any_cond = AnyCondition([cond_a, cond_b])
        any_explain = any_cond.explain()
        assert "OR" in any_explain
        assert "Permission(app.view)" in any_explain

        not_cond = NotCondition(cond_b)
        not_explain = not_cond.explain()
        assert not_explain == "NOT(Permission(app.view))"

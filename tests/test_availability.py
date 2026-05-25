"""Tests for the shared availability evaluation helper."""

from __future__ import annotations


def test_no_availability_method_is_always_available():
    from django_stratagem.availability import evaluate_availability

    class Plain:
        pass

    available, reason = evaluate_availability(Plain, {})
    assert available is True
    assert reason == "Always available"


def test_none_class_is_unavailable():
    from django_stratagem.availability import evaluate_availability

    available, reason = evaluate_availability(None, {})
    assert available is False


def test_uses_explain_availability_reason():
    from django_stratagem.availability import evaluate_availability
    from django_stratagem.conditions import SettingCondition
    from django_stratagem.interfaces import ConditionalInterface

    class Gated(ConditionalInterface):
        slug = "gated_eval"
        condition = SettingCondition("DOES_NOT_EXIST", expected_value=True)

    available, reason = evaluate_availability(Gated, {})
    assert available is False
    assert "failed" in reason.lower() or "->" in reason


def test_sync_only_override_is_authoritative():
    from django_stratagem.availability import evaluate_availability
    from django_stratagem.interfaces import ConditionalInterface

    # Overrides only the sync is_available (no explain_availability override):
    # that override must win even though the (unset) condition would say True.
    class SyncGated(ConditionalInterface):
        slug = "sync_gated"

        @classmethod
        def is_available(cls, context=None):
            return False

    available, _reason = evaluate_availability(SyncGated, {})
    assert available is False

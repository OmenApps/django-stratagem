"""Tests for the shipped pytest plugin."""

from __future__ import annotations


def test_stratagem_isolation_fixture_is_available(stratagem_isolation, test_strategy_registry):
    """Verify the pytest11 plugin loads and exposes the ``stratagem_isolation`` fixture.

    If the plugin failed to register via its entry point, pytest would error
    with "fixture 'stratagem_isolation' not found" before this body runs, so
    successfully requesting it and registering inside it is the assertion. The
    fixture's actual teardown (state restoration) is exercised against the
    underlying mechanism in
    ``test_isolate_registries_restores_global_list_and_implementations``.
    """
    from django_stratagem.interfaces import Interface

    class TempIsoStrategy(Interface):
        slug = "iso_temp"

    test_strategy_registry.register(TempIsoStrategy)
    assert "iso_temp" in test_strategy_registry.implementations

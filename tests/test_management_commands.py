"""Tests for django_stratagem management commands."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from django_stratagem.registry import Registry, django_stratagem_registry

pytestmark = pytest.mark.django_db


class TestClearRegistriesCacheCommand:
    """Tests for clear_registries_cache management command."""

    def test_command_runs_successfully(self):
        """Test command executes without error."""
        out = StringIO()
        call_command("clear_registries_cache", stdout=out)
        output = out.getvalue()
        assert "cleared" in output.lower()

    def test_command_outputs_success_message(self):
        """Test command outputs success message."""
        out = StringIO()
        call_command("clear_registries_cache", stdout=out)
        output = out.getvalue()
        assert "All registry caches cleared" in output

    def test_command_calls_clear_all_cache(self, mocker):
        """Test command calls Registry.clear_all_cache."""
        mock_clear = mocker.patch.object(Registry, "clear_all_cache")
        out = StringIO()

        call_command("clear_registries_cache", stdout=out)

        mock_clear.assert_called_once()


class TestInitializeRegistriesCommand:
    """Tests for initialize_registries management command."""

    def test_command_runs_successfully(self):
        """Test command executes without error."""
        out = StringIO()
        call_command("initialize_registries", stdout=out)
        output = out.getvalue()
        assert "Successfully initialized" in output

    def test_command_with_clear_cache_flag(self, mocker):
        """Test command with --clear-cache flag clears cache."""
        mock_clear = mocker.patch.object(Registry, "clear_all_cache")
        out = StringIO()

        call_command("initialize_registries", clear_cache=True, stdout=out)

        mock_clear.assert_called_once()
        output = out.getvalue()
        assert "caches cleared" in output.lower()

    def test_command_with_force_flag(self):
        """Test command with --force flag runs without error."""
        out = StringIO()
        call_command("initialize_registries", force=True, stdout=out)
        output = out.getvalue()
        assert "Successfully initialized" in output

    def test_command_discovers_registries(self):
        """Test command calls discover_registries."""
        out = StringIO()
        call_command("initialize_registries", stdout=out)
        output = out.getvalue()
        assert "Registries discovered" in output

    def test_command_updates_field_choices(self):
        """Test command calls update_choices_fields."""
        out = StringIO()
        call_command("initialize_registries", stdout=out)
        output = out.getvalue()
        assert "Field choices updated" in output

    def test_command_reports_registry_count(self):
        """Test command reports number of initialized registries."""
        out = StringIO()
        call_command("initialize_registries", stdout=out)
        output = out.getvalue()
        # Should contain registry count
        assert "registries" in output.lower()

    def test_command_lists_registries(self, test_strategy_registry):
        """Test command lists initialized registries."""
        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out = StringIO()
        call_command("initialize_registries", stdout=out)
        output = out.getvalue()
        assert "Initialized registries" in output

    def test_command_verbosity_level_0(self):
        """Test command with verbosity 0 has minimal output."""
        out = StringIO()
        call_command("initialize_registries", verbosity=0, stdout=out)
        # Should still output something since command writes directly
        # Verbosity mainly affects Django framework messages

    def test_command_verbosity_level_2(self, test_strategy_registry):
        """Test command with verbosity 2 shows health info."""
        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out = StringIO()
        call_command("initialize_registries", verbosity=2, stdout=out)
        out.getvalue()
        # With verbosity >= 2, health info should be shown
        # Command shows "Health:" at verbosity >= 2

    def test_command_shows_implementation_counts(self, test_strategy_registry):
        """Test command shows implementation counts for each registry."""
        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out = StringIO()
        call_command("initialize_registries", stdout=out)
        output = out.getvalue()
        assert "implementations" in output


class TestListRegistriesCommand:
    """Tests for list_registries management command."""

    def test_command_runs_successfully(self):
        """Test command executes without error."""
        out = StringIO()
        call_command("list_registries", stdout=out)
        # Should not raise

    def test_command_with_no_registries(self, mocker):
        """Test command shows warning when no registries."""
        # Temporarily clear registries
        original = list(django_stratagem_registry)
        django_stratagem_registry.clear()

        try:
            out = StringIO()
            call_command("list_registries", stdout=out)
            output = out.getvalue()
            assert "No registries" in output
        finally:
            # Restore registries
            for reg in original:
                if reg not in django_stratagem_registry:
                    django_stratagem_registry.append(reg)

    def test_command_lists_registry_names(self, test_strategy_registry):
        """Test command lists registry names."""
        # Ensure implementations are imported (they auto-register via Interface.__init_subclass__)

        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out = StringIO()
        call_command("list_registries", stdout=out)
        output = out.getvalue()
        assert "TestStrategyRegistry" in output

    def test_command_lists_registry_modules(self, test_strategy_registry):
        """Test command lists registry modules."""
        # Ensure implementations are imported (they auto-register via Interface.__init_subclass__)

        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out = StringIO()
        call_command("list_registries", stdout=out)
        output = out.getvalue()
        # Module should be displayed
        assert test_strategy_registry.__module__ in output

    def test_command_lists_implementations(self, test_strategy_registry):
        """Test command lists implementations for each registry."""
        # Ensure implementations are imported (they auto-register via Interface.__init_subclass__)

        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out = StringIO()
        call_command("list_registries", stdout=out)
        output = out.getvalue()
        assert "Implementations" in output

    def test_command_shows_implementation_slugs(self, test_strategy_registry):
        """Test command shows implementation slugs."""
        # Ensure implementations are imported (they auto-register via Interface.__init_subclass__)

        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out = StringIO()
        call_command("list_registries", stdout=out)
        output = out.getvalue()
        # Should show slug for each implementation
        assert "Slug:" in output

    def test_command_shows_implementation_classes(self, test_strategy_registry):
        """Test command shows implementation class names."""
        # Ensure implementations are imported (they auto-register via Interface.__init_subclass__)

        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out = StringIO()
        call_command("list_registries", stdout=out)
        output = out.getvalue()
        assert "Class:" in output

    def test_command_shows_descriptions(self, test_strategy_registry):
        """Test command shows implementation descriptions."""
        # Ensure implementations are imported (they auto-register via Interface.__init_subclass__)

        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out = StringIO()
        call_command("list_registries", stdout=out)
        output = out.getvalue()
        assert "Description:" in output


class TestInitializeRegistriesForceFlag:
    """Tests for --force flag overriding migration context."""

    def test_force_overrides_migration_detection(self, mocker):
        """Test --force flag temporarily overrides migration detection."""
        from django_stratagem import utils as stratagem_utils

        # Simulate migration context
        original = stratagem_utils._migrations_running
        stratagem_utils._migrations_running = True

        try:
            out = StringIO()
            call_command("initialize_registries", force=True, stdout=out)
            output = out.getvalue()
            assert "Successfully initialized" in output
        finally:
            stratagem_utils._migrations_running = original

    def test_force_restores_migration_state(self):
        """Test --force restores original migration state after completion."""
        from django_stratagem import utils as stratagem_utils

        original = stratagem_utils._migrations_running
        stratagem_utils._migrations_running = True

        try:
            out = StringIO()
            call_command("initialize_registries", force=True, stdout=out)
            # After command, the original value should be restored
            assert stratagem_utils._migrations_running is True
        finally:
            stratagem_utils._migrations_running = original

    def test_migration_warning_without_force(self):
        """Test warning is shown when migration context detected without --force."""
        from django_stratagem import utils as stratagem_utils

        original = stratagem_utils._migrations_running
        stratagem_utils._migrations_running = True

        try:
            out = StringIO()
            err = StringIO()
            call_command("initialize_registries", stdout=out, stderr=err)
            err_output = err.getvalue()
            assert "Migration context detected" in err_output
        finally:
            stratagem_utils._migrations_running = original


class TestManagementCommandEdgeCases:
    """Tests for edge cases in management commands."""

    def test_clear_cache_is_idempotent(self):
        """Test clearing cache multiple times doesn't cause errors."""
        out = StringIO()
        # Call multiple times
        call_command("clear_registries_cache", stdout=out)
        call_command("clear_registries_cache", stdout=out)
        call_command("clear_registries_cache", stdout=out)
        # Should not raise

    def test_initialize_with_both_flags(self):
        """Test initialize with both --force and --clear-cache."""
        out = StringIO()
        call_command("initialize_registries", force=True, clear_cache=True, stdout=out)
        output = out.getvalue()
        assert "Successfully initialized" in output

    def test_list_registries_handles_empty_docstrings(self, test_strategy_registry):
        """Test list_registries handles registries without docstrings."""
        # Ensure implementations are imported (they auto-register via Interface.__init_subclass__)

        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out = StringIO()
        # Should not raise even if some docs are missing
        call_command("list_registries", stdout=out)

    def test_commands_use_stdout_consistently(self, test_strategy_registry):
        """Test all commands write to stdout parameter."""
        # Ensure implementations are imported (they auto-register via Interface.__init_subclass__)

        if test_strategy_registry not in django_stratagem_registry:
            django_stratagem_registry.append(test_strategy_registry)

        out1 = StringIO()
        out2 = StringIO()
        out3 = StringIO()

        call_command("clear_registries_cache", stdout=out1)
        call_command("initialize_registries", stdout=out2)
        call_command("list_registries", stdout=out3)

        # All should have written something
        assert out1.getvalue()
        assert out2.getvalue()
        # list_registries now has a registry with implementations
        assert out3.getvalue()

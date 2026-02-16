"""Tests for django_stratagem AppConfig."""

from __future__ import annotations

from unittest.mock import patch

import django_stratagem
from django_stratagem.apps import DjangoStratagemAppConfig


class TestAppConfig:
    """Tests for DjangoStratagemAppConfig.ready()."""

    def _make_app_config(self):
        """Create an AppConfig instance using the real module."""
        return DjangoStratagemAppConfig("django_stratagem", django_stratagem)

    def test_ready_calls_discover_registries(self):
        """Test that ready() calls discover_registries."""
        app_config = self._make_app_config()

        with (
            patch("django_stratagem.apps.is_running_migrations", return_value=False),
            patch("django_stratagem.registry.discover_registries") as mock_discover,
            patch("django_stratagem.registry.update_choices_fields"),
        ):
            app_config.ready()
            mock_discover.assert_called_once()

    def test_ready_calls_update_choices_fields(self):
        """Test that ready() calls update_choices_fields."""
        app_config = self._make_app_config()

        with (
            patch("django_stratagem.apps.is_running_migrations", return_value=False),
            patch("django_stratagem.registry.discover_registries"),
            patch("django_stratagem.registry.update_choices_fields") as mock_update,
        ):
            app_config.ready()
            mock_update.assert_called_once()

    def test_ready_skips_during_migrations(self):
        """Test that ready() skips all operations during migrations."""
        app_config = self._make_app_config()

        with (
            patch("django_stratagem.apps.is_running_migrations", return_value=True),
            patch("django_stratagem.registry.discover_registries") as mock_discover,
            patch("django_stratagem.registry.update_choices_fields") as mock_update,
        ):
            app_config.ready()
            mock_discover.assert_not_called()
            mock_update.assert_not_called()

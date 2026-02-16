"""Tests for django_stratagem plugins module."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from django_stratagem.plugins import PluginLoader

pytestmark = pytest.mark.django_db


class MockPluginModule:
    """Mock plugin module for testing."""

    __version__ = "1.0.0"
    REGISTRY = "TestStrategyRegistry"
    IMPLEMENTATIONS = [
        "tests.registries_fixtures.EmailStrategy",
    ]


class MockPluginModuleNoVersion:
    """Mock plugin module without version."""

    REGISTRY = "TestStrategyRegistry"
    IMPLEMENTATIONS = []


class TestPluginLoaderDiscoverPlugins:
    """Tests for PluginLoader.discover_plugins method."""

    def test_discover_returns_list(self):
        """Test discover_plugins returns a list."""
        plugins = PluginLoader.discover_plugins()
        assert isinstance(plugins, list)

    def test_discover_handles_no_plugins(self):
        """Test discover_plugins handles case with no plugins."""
        with patch("importlib.metadata.entry_points") as mock_entry_points:
            mock_entry_points.return_value.select.return_value = []
            plugins = PluginLoader.discover_plugins()
            assert plugins == []

    def test_discover_loads_plugin_entry_points(self, mocker):
        """Test discover_plugins loads entry points."""
        # Create mock entry point
        mock_entry_point = MagicMock()
        mock_entry_point.name = "test_plugin"
        mock_entry_point.load.return_value = MockPluginModule

        mock_entry_points = MagicMock()
        mock_entry_points.select.return_value = [mock_entry_point]

        with patch("importlib.metadata.entry_points", return_value=mock_entry_points):
            PluginLoader.discover_plugins()

            mock_entry_point.load.assert_called_once()

    def test_discover_handles_load_exception(self, mocker):
        """Test discover_plugins handles exceptions during load."""
        mock_entry_point = MagicMock()
        mock_entry_point.name = "bad_plugin"
        mock_entry_point.load.side_effect = ImportError("Module not found")

        mock_entry_points = MagicMock()
        mock_entry_points.select.return_value = [mock_entry_point]

        with patch("importlib.metadata.entry_points", return_value=mock_entry_points):
            # Should not raise
            plugins = PluginLoader.discover_plugins()
            assert plugins == []

    def test_discover_handles_entry_points_exception(self, mocker):
        """Test discover_plugins handles exception from entry_points."""
        with patch("importlib.metadata.entry_points") as mock_entry_points:
            mock_entry_points.side_effect = TypeError("Entry points error")
            # Should not raise
            plugins = PluginLoader.discover_plugins()
            assert plugins == []


class TestPluginLoaderExtractPluginInfo:
    """Tests for PluginLoader._extract_plugin_info method."""

    def test_extract_with_full_module(self):
        """Test extraction from module with all attributes."""
        plugin_info = PluginLoader._extract_plugin_info("test_plugin", MockPluginModule)

        assert plugin_info.name == "test_plugin"
        assert plugin_info.version == "1.0.0"
        assert plugin_info.registry == "TestStrategyRegistry"
        assert plugin_info.implementations == MockPluginModule.IMPLEMENTATIONS
        assert plugin_info.enabled is True

    def test_extract_with_missing_version(self):
        """Test extraction from module without version."""
        plugin_info = PluginLoader._extract_plugin_info("test_plugin", MockPluginModuleNoVersion)

        assert plugin_info.name == "test_plugin"
        assert plugin_info.version == "0.0.0"  # Default version

    def test_extract_with_missing_registry(self):
        """Test extraction from module without REGISTRY."""

        class NoRegistry:
            __version__ = "1.0.0"
            IMPLEMENTATIONS = []

        plugin_info = PluginLoader._extract_plugin_info("test_plugin", NoRegistry)

        assert plugin_info.registry == ""  # Default empty string

    def test_extract_with_missing_implementations(self):
        """Test extraction from module without IMPLEMENTATIONS."""

        class NoImplementations:
            __version__ = "1.0.0"
            REGISTRY = "TestRegistry"

        plugin_info = PluginLoader._extract_plugin_info("test_plugin", NoImplementations)

        assert plugin_info.implementations == []  # Default empty list


class TestPluginLoaderIsPluginEnabled:
    """Tests for PluginLoader._is_plugin_enabled method."""

    @pytest.fixture
    def mock_plugin(self):
        """Create mock plugin info."""
        return SimpleNamespace(
            name="test_plugin",
            version="1.0.0",
            registry="TestRegistry",
            implementations=[],
            enabled=True,
        )

    def test_enabled_by_default(self, mock_plugin, settings):
        """Test plugin is enabled by default."""
        # Ensure no enabled/disabled lists
        if hasattr(settings, "REGISTRIES_ENABLED_PLUGINS"):
            delattr(settings, "REGISTRIES_ENABLED_PLUGINS")
        if hasattr(settings, "REGISTRIES_DISABLED_PLUGINS"):
            delattr(settings, "REGISTRIES_DISABLED_PLUGINS")

        result = PluginLoader._is_plugin_enabled(mock_plugin)
        assert result is True

    def test_enabled_when_in_enabled_list(self, mock_plugin, settings):
        """Test plugin is enabled when in enabled list."""
        settings.REGISTRIES_ENABLED_PLUGINS = ["test_plugin", "other_plugin"]

        result = PluginLoader._is_plugin_enabled(mock_plugin)
        assert result is True

    def test_disabled_when_not_in_enabled_list(self, mock_plugin, settings):
        """Test plugin is disabled when not in enabled list."""
        settings.REGISTRIES_ENABLED_PLUGINS = ["other_plugin"]

        result = PluginLoader._is_plugin_enabled(mock_plugin)
        assert result is False

    def test_disabled_when_in_disabled_list(self, mock_plugin, settings):
        """Test plugin is disabled when in disabled list."""
        if hasattr(settings, "REGISTRIES_ENABLED_PLUGINS"):
            delattr(settings, "REGISTRIES_ENABLED_PLUGINS")
        settings.REGISTRIES_DISABLED_PLUGINS = ["test_plugin"]

        result = PluginLoader._is_plugin_enabled(mock_plugin)
        assert result is False

    def test_enabled_list_takes_precedence(self, mock_plugin, settings):
        """Test enabled list takes precedence over disabled list."""
        settings.REGISTRIES_ENABLED_PLUGINS = ["test_plugin"]
        settings.REGISTRIES_DISABLED_PLUGINS = ["test_plugin"]

        result = PluginLoader._is_plugin_enabled(mock_plugin)
        # Enabled list is checked first, so plugin should be enabled
        assert result is True


class TestPluginLoaderLoadImplementations:
    """Tests for PluginLoader.load_plugin_implementations method."""

    def test_load_skips_non_matching_registry(self, test_strategy_registry, mocker):
        """Test load skips plugins for different registries."""
        mock_plugin = SimpleNamespace(
            name="other_plugin",
            version="1.0.0",
            registry="DifferentRegistry",  # Different from test_strategy_registry
            implementations=["some.module.Class"],
            enabled=True,
        )

        mocker.patch.object(PluginLoader, "discover_plugins", return_value=[mock_plugin])

        # Should not raise and should not attempt to import
        PluginLoader.load_plugin_implementations(test_strategy_registry)

    def test_load_handles_import_error(self, test_strategy_registry, mocker):
        """Test load handles import errors gracefully."""
        mock_plugin = SimpleNamespace(
            name="test_plugin",
            version="1.0.0",
            registry="TestStrategyRegistry",
            implementations=["nonexistent.module.Class"],
            enabled=True,
        )

        mocker.patch.object(PluginLoader, "discover_plugins", return_value=[mock_plugin])

        # Should not raise
        PluginLoader.load_plugin_implementations(test_strategy_registry)

    def test_load_valid_implementation(self, test_strategy_registry, mocker):
        """Test load successfully loads valid implementation."""
        mock_plugin = SimpleNamespace(
            name="test_plugin",
            version="1.0.0",
            registry="TestStrategyRegistry",
            implementations=[
                "tests.registries_fixtures.EmailStrategy",
            ],
            enabled=True,
        )

        mocker.patch.object(PluginLoader, "discover_plugins", return_value=[mock_plugin])
        mock_register = mocker.patch.object(test_strategy_registry, "register")

        PluginLoader.load_plugin_implementations(test_strategy_registry)

        # Should have attempted to register
        mock_register.assert_called_once()

    def test_load_multiple_implementations(self, test_strategy_registry, mocker):
        """Test load handles multiple implementations."""
        mock_plugin = SimpleNamespace(
            name="test_plugin",
            version="1.0.0",
            registry="TestStrategyRegistry",
            implementations=[
                "tests.registries_fixtures.EmailStrategy",
                "tests.registries_fixtures.SMSStrategy",
            ],
            enabled=True,
        )

        mocker.patch.object(PluginLoader, "discover_plugins", return_value=[mock_plugin])
        mock_register = mocker.patch.object(test_strategy_registry, "register")

        PluginLoader.load_plugin_implementations(test_strategy_registry)

        # Should have attempted to register twice
        assert mock_register.call_count == 2


class TestPluginLoaderConstants:
    """Tests for PluginLoader constants."""

    def test_entry_point_group_defined(self):
        """Test ENTRY_POINT_GROUP constant is defined."""
        assert hasattr(PluginLoader, "ENTRY_POINT_GROUP")
        assert PluginLoader.ENTRY_POINT_GROUP == "django_stratagem.plugins"

    def test_settings_methods_exist(self):
        """Test settings accessor methods exist."""
        assert hasattr(PluginLoader, "_get_enabled_plugins")
        assert hasattr(PluginLoader, "_get_disabled_plugins")


class TestPluginLoaderEdgeCases:
    """Tests for edge cases in PluginLoader."""

    def test_empty_implementation_path(self, test_strategy_registry, mocker):
        """Test handling of empty implementation path."""
        mock_plugin = SimpleNamespace(
            name="test_plugin",
            version="1.0.0",
            registry="TestStrategyRegistry",
            implementations=[""],  # Empty string
            enabled=True,
        )

        mocker.patch.object(PluginLoader, "discover_plugins", return_value=[mock_plugin])

        # Should not raise
        PluginLoader.load_plugin_implementations(test_strategy_registry)

    def test_implementation_path_no_dot(self, test_strategy_registry, mocker):
        """Test handling of implementation path without module separator."""
        mock_plugin = SimpleNamespace(
            name="test_plugin",
            version="1.0.0",
            registry="TestStrategyRegistry",
            implementations=["InvalidPath"],  # No dot separator
            enabled=True,
        )

        mocker.patch.object(PluginLoader, "discover_plugins", return_value=[mock_plugin])

        # Should not raise (will fail gracefully)
        PluginLoader.load_plugin_implementations(test_strategy_registry)

    def test_multiple_plugins_same_registry(self, test_strategy_registry, mocker):
        """Test loading from multiple plugins for same registry."""
        mock_plugins = [
            SimpleNamespace(
                name="plugin1",
                version="1.0.0",
                registry="TestStrategyRegistry",
                implementations=["tests.registries_fixtures.EmailStrategy"],
                enabled=True,
            ),
            SimpleNamespace(
                name="plugin2",
                version="2.0.0",
                registry="TestStrategyRegistry",
                implementations=["tests.registries_fixtures.SMSStrategy"],
                enabled=True,
            ),
        ]

        mocker.patch.object(PluginLoader, "discover_plugins", return_value=mock_plugins)
        mock_register = mocker.patch.object(test_strategy_registry, "register")

        PluginLoader.load_plugin_implementations(test_strategy_registry)

        # Should have registered from both plugins
        assert mock_register.call_count == 2

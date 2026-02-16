from __future__ import annotations

import importlib
import importlib.metadata
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from django.conf import settings

if TYPE_CHECKING:
    from .registry import Registry

logger = logging.getLogger(__name__)


class PluginProtocol(Protocol):
    """Protocol for registry plugins."""

    name: str
    version: str
    registry: str
    implementations: list[str]
    enabled: bool = True


@dataclass
class PluginInfo:
    """Plugin metadata container."""

    name: str
    version: str
    registry: str
    implementations: list[str]
    enabled: bool = True


class PluginLoader:
    """Loads implementations from external packages via entry points."""

    # Entry point group name
    ENTRY_POINT_GROUP = "django_stratagem.plugins"

    @classmethod
    def _get_enabled_plugins(cls) -> list[str] | None:
        """Get the enabled plugins list from settings at call time."""
        stratagem_settings = getattr(settings, "DJANGO_STRATAGEM", {})
        # Check under DJANGO_STRATAGEM first, then fall back to top-level
        return stratagem_settings.get(
            "ENABLED_PLUGINS",
            getattr(settings, "REGISTRIES_ENABLED_PLUGINS", None),
        )

    @classmethod
    def _get_disabled_plugins(cls) -> list[str]:
        """Get the disabled plugins list from settings at call time."""
        stratagem_settings = getattr(settings, "DJANGO_STRATAGEM", {})
        # Check under DJANGO_STRATAGEM first, then fall back to top-level
        return stratagem_settings.get(
            "DISABLED_PLUGINS",
            getattr(settings, "REGISTRIES_DISABLED_PLUGINS", []),
        )

    @classmethod
    def discover_plugins(cls) -> list[PluginProtocol]:
        """Discover all available plugins from installed packages."""
        plugins = []

        try:
            # Get all entry points in our group
            entry_points = importlib.metadata.entry_points()
            plugin_entries = entry_points.select(group=cls.ENTRY_POINT_GROUP)

            for entry_point in plugin_entries:
                try:
                    # Load the plugin module
                    plugin_module = entry_point.load()

                    # Extract plugin metadata
                    plugin_info = cls._extract_plugin_info(entry_point.name, plugin_module)

                    if cls._is_plugin_enabled(plugin_info):
                        plugins.append(plugin_info)
                        logger.info(
                            "Discovered plugin '%s' v%s for registry '%s'",
                            plugin_info.name,
                            plugin_info.version,
                            plugin_info.registry,
                        )

                except (ImportError, AttributeError, TypeError) as e:
                    logger.error("Failed to load plugin '%s': %s", entry_point.name, e)

        except (ImportError, TypeError) as e:
            logger.error("Failed to discover plugins: %s", e)

        return plugins

    @classmethod
    def _extract_plugin_info(cls, name: str, module: Any) -> PluginProtocol:
        """Extract plugin information from a loaded module."""
        return PluginInfo(
            name=name,
            version=getattr(module, "__version__", "0.0.0"),
            registry=getattr(module, "REGISTRY", ""),
            implementations=getattr(module, "IMPLEMENTATIONS", []),
            enabled=True,
        )

    @classmethod
    def _is_plugin_enabled(cls, plugin: PluginProtocol) -> bool:
        """Check if a plugin is enabled based on settings."""
        # Check explicit enable list
        enabled_plugins = cls._get_enabled_plugins()
        if enabled_plugins is not None:
            return plugin.name in enabled_plugins

        # Check disabled list
        disabled_plugins = cls._get_disabled_plugins()
        if plugin.name in disabled_plugins:
            return False

        return True

    @classmethod
    def load_plugin_implementations(cls, registry_cls: type[Registry]) -> None:
        """Load all implementations from plugins for a specific registry."""
        plugins = cls.discover_plugins()

        for plugin in plugins:
            if plugin.registry != registry_cls.__name__:
                continue

            for impl_path in plugin.implementations:
                try:
                    # Import the implementation class
                    module_path, class_name = impl_path.rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    impl_class = getattr(module, class_name)

                    # Register with the registry
                    registry_cls.register(impl_class)

                    logger.info("Loaded implementation '%s' from plugin '%s'", impl_class.__name__, plugin.name)

                except (ImportError, AttributeError, TypeError, ValueError) as e:
                    logger.error("Failed to load implementation '%s' from plugin '%s': %s", impl_path, plugin.name, e)

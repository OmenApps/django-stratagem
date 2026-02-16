# How to Use the Plugin System

Third-party packages can add implementations to your registries without changing your code. A plugin is a normal Python package that declares its implementations via an [entry point](https://packaging.python.org/en/latest/specifications/entry-points/) - when installed, they appear in the target registry automatically.

## Writing a Plugin

A plugin is an ordinary Python package with two things: one or more option classes and a small metadata module.

### Step 1: Write the option classes

The classes look exactly like any other option you'd write in your own app. They subclass the host app's interface and set a `slug`:

```python
# django_slack_notifications/notifications.py
from myapp.registry import NotificationInterface

class SlackNotification(NotificationInterface):
    slug = "slack"
    description = "Send notifications to a Slack channel"
    priority = 30

    def send(self, message, recipient):
        # post to Slack API...
        return True

class TeamsNotification(NotificationInterface):
    slug = "teams"
    description = "Send notifications via Microsoft Teams"
    priority = 40

    def send(self, message, recipient):
        # post to Teams API...
        return True
```

### Step 2: Create the plugin metadata module

This module tells django-stratagem which registry to add the options to and where the classes live:

```python
# django_slack_notifications/stratagem_plugin.py

__version__ = "1.0.0"

# The name of the registry class these options belong to
REGISTRY = "NotificationRegistry"

# Dotted paths to the option classes
IMPLEMENTATIONS = [
    "django_slack_notifications.notifications.SlackNotification",
    "django_slack_notifications.notifications.TeamsNotification",
]
```

### Step 3: Register the entry point

In the plugin's `pyproject.toml`, declare an entry point so django-stratagem can find the metadata module:

```toml
[project.entry-points."django_stratagem.plugins"]
slack_notifications = "django_slack_notifications.stratagem_plugin"
```

The key (`slack_notifications`) is the plugin's name used in `ENABLED_PLUGINS` / `DISABLED_PLUGINS` settings. The value is the dotted path to the metadata module from step 2.

Once installed, the Slack and Teams options show up in `NotificationRegistry` - in forms, admin, and API responses - without modifying the host app.

## Using Plugins

Plugins are loaded by default. During startup, `discover_implementations()` picks up any installed plugins that target your registry.

If you need to control which plugins are active:

```python
# settings.py
DJANGO_STRATAGEM = {
    # Allow only specific plugins (None means allow all, which is the default)
    "ENABLED_PLUGINS": ["slack_notifications", "another_plugin"],

    # Or block specific plugins while allowing everything else
    "DISABLED_PLUGINS": ["unwanted_plugin"],
}
```

## How Plugin Discovery Works

1. During app startup, each registry's `discover_implementations()` calls `PluginLoader.load_plugin_implementations()`
2. `PluginLoader` scans the `django_stratagem.plugins` entry point group using Python's `importlib.metadata`
3. Each entry point module is loaded and its `REGISTRY`, `IMPLEMENTATIONS`, and `__version__` attributes are read into a `PluginInfo` dataclass
4. The plugin is checked against `ENABLED_PLUGINS` / `DISABLED_PLUGINS` settings
5. Each implementation class path is imported and registered with the target registry, just as if it had been defined locally

## PluginProtocol and PluginInfo

For type checking, plugins conform to `PluginProtocol`:

```python
class PluginProtocol(Protocol):
    name: str              # Plugin name (from the entry point key)
    version: str           # Version string
    registry: str          # Target registry class name
    implementations: list[str]  # Dotted paths to option classes
    enabled: bool = True
```

`PluginInfo` is the concrete `@dataclass` that `PluginLoader` creates internally. You don't need to use either of these directly unless you're building tooling around the plugin system.

# AGENTS.md

This file provides guidance to AI coding agents working with code in this repository.

## Project Overview

django-stratagem is a Django library providing a registry-based plugin architecture. It allows developers to define registries of implementations that can be discovered, registered, and used dynamically. Supports hierarchical registries, conditional availability, Django admin integration, DRF serializer fields, and custom model fields.

## Project Layout

Uses a `src/` layout: the package lives at `src/django_stratagem/`. Tests are in `tests/` at project root. Documentation is in `docs/`.

## Setup

```bash
uv sync --group dev
# With DRF support:
uv sync --group dev --extra drf
```

## Running Tests

Tests use SQLite in-memory - no external database required.

```bash
# Run all nox sessions (pre-commit, pip-audit, tests)
nox

# Run tests for a specific Django/Python combination
nox -s "tests(django='5.2', python='3.13')"

# Run tests directly with pytest
uv run pytest tests/ -vv

# Run a single test file or test
uv run pytest tests/test_registry.py -vv
uv run pytest tests/test_registry.py::TestClassName::test_method -vv
```

## Linting and Formatting

```bash
ruff check src/          # lint
ruff check --fix src/    # lint and auto-fix
ruff format src/         # format
```

## Pre-commit Hooks

```bash
pre-commit run --all-files
```

## Architecture

### Registration Flow

The core lifecycle works through Python metaclasses and `__init_subclass__`:

1. A `Registry` subclass with `implementations_module` defined gets appended to the global `django_stratagem_registry` list via `Registry.__init_subclass__`.
2. An `Interface` subclass with both `registry` and `slug` class attributes auto-registers itself with its registry via `Interface.__init_subclass__` -> `Registry.register()`.
3. On app startup, `DjangoStratagemAppConfig.ready()` calls `discover_registries()` which runs `autodiscover_modules()` for each registry's `implementations_module`, triggering the auto-registration in step 2.
4. `update_choices_fields()` then populates dynamic choices on any model fields linked to registries.

### Key Modules

- `src/django_stratagem/registry.py` - `Registry` and `Interface` base classes, `RegistryMeta` metaclass
- `src/django_stratagem/fields.py` - Model fields (`RegistryClassField`, `RegistryField`, `HierarchicalRegistryField`) and descriptors
- `src/django_stratagem/conditions.py` - `Condition` classes and `ConditionalInterface`
- `src/django_stratagem/plugins.py` - `PluginLoader` for entry-point-based plugin discovery
- `src/django_stratagem/forms.py` - Form fields and widgets
- `src/django_stratagem/admin.py` - Admin mixins and dashboard views
- `src/django_stratagem/drf/` - DRF serializer fields and API views
- `src/django_stratagem/apps.py` - App config with `ready()` hook for autodiscovery
- `src/django_stratagem/utils.py` - Migration detection, import helpers

### Migration Safety

Registry operations (autodiscovery, choice population, class imports) are skipped during `migrate`/`makemigrations` via `is_running_migrations()` in `utils.py`.

## Code Style

Django coding conventions with ruff (line length 120). Git commits: present tense imperative, first line <= 72 chars.

When needing to use a dash in strings, comments, docs, or elsewhere, always use `-` rather than em-dashes or en-dashes.

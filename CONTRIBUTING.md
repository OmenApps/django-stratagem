# Contributing

## Development Setup

Clone the repository and install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/omenapps/django-stratagem.git
cd django-stratagem
uv sync --group dev
```

To include DRF support for development:

```bash
uv sync --group dev --extra drf
```

## Running Tests

Tests use SQLite in-memory, so no external database is required.

### Using nox (recommended)

nox runs pre-commit, pip-audit, and tests across multiple Django/Python combinations:

```bash
# Run all sessions
uv run nox

# Run tests for a specific Django/Python combination
uv run nox -s "tests(django='5.2', python='3.13')"
```

### Using pytest directly

```bash
# Run all tests
uv run pytest tests/ -vv

# Run a single test file
uv run pytest tests/test_registry.py -vv

# Run a specific test
uv run pytest tests/test_registry.py::TestClassName::test_method -vv
```

## Linting and Formatting

The project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Lint
uv run ruff check src/

# Lint and auto-fix
uv run ruff check --fix src/

# Format
uv run ruff format src/
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. To run them manually:

```bash
uv run pre-commit run --all-files
```

## Building Documentation

### Using nox (recommended)

```bash
uv run nox -s docs
```

### Using Sphinx directly

```bash
uv sync --group docs
uv run sphinx-build docs docs/_build/html
```

The built documentation will be available at `docs/_build/html/index.html`.

### Regenerating LLM docs

After editing any documentation files, regenerate `docs/llms-full.txt` so LLM-friendly docs stay in sync:

```bash
uv run nox -s llms-full
```

This concatenates all doc sources into a single file. The Sphinx build copies both `docs/llms.txt` and `docs/llms-full.txt` to the site root automatically via `html_extra_path`.

## Code Style

- Follow Django coding conventions
- Line length: 120 characters (enforced by ruff)
- Git commits: present tense imperative, first line 72 characters or fewer

## Project Layout

```
django-stratagem/
├── src/django_stratagem/
│   ├── __init__.py            # Public API exports
│   ├── registry.py            # Core registry classes
│   ├── interfaces.py
│   ├── conditions.py
│   ├── fields.py              # Model fields and descriptors
│   ├── forms.py
│   ├── widgets.py
│   ├── admin.py
│   ├── plugins.py
│   ├── signals.py
│   ├── validators.py
│   ├── checks.py
│   ├── lookups.py             # Custom field lookups
│   ├── utils.py
│   ├── app_settings.py
│   ├── apps.py
│   ├── templatetags/
│   │   └── stratagem.py
│   ├── management/commands/
│   │   ├── list_registries.py
│   │   ├── clear_registries_cache.py
│   │   └── initialize_registries.py
│   └── drf/                   # Optional DRF integration
│       ├── serializers.py
│       ├── views.py
│       └── urls.py
├── tests/
├── docs/
├── pyproject.toml
├── noxfile.py
└── CLAUDE.md
```

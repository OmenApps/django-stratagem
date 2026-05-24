# Changelog

All notable changes to django-stratagem are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project uses CalVer.

## [Unreleased]

### Added

- Async/ASGI support: `Condition.acheck`, `ConditionalInterface.ais_available`,
  and the `Registry` async reads `aget`, `aget_choices`, `aget_choices_for_context`,
  `aget_available_implementations`, and `aget_for_context`. Built-in compound
  conditions (`&`, `|`, `~`) propagate native async `acheck` overrides.
- Registry Inspector: a staff-only, read-only page (`registry_inspector` view,
  `django_stratagem.urls`, `INSPECTOR_URL_NAME`) listing every registry, its
  implementations, and why each is or is not available.
  `ConditionalInterface.explain_availability` powers the reasons.
- Testing toolkit (`django_stratagem.testing`): `temporary_implementation`,
  `override_availability`, and `isolate_registries` context managers for
  isolating registry state in downstream test suites.
- `startregistry` management command to scaffold a registry, interface, and
  implementations module into an app.
- Recipe gallery: runnable example apps under `examples/` (notifications,
  payments, exports) plus a `docs/recipes.md` gallery page.
- `asgiref>=3.6` is now an explicit dependency (previously transitive via Django).

### Changed

- `SettingCondition` and `EnvironmentCondition` `explain()` output now redacts
  values for settings/variables whose names look like credentials (e.g.
  `SECRET`, `PASSWORD`, `TOKEN`, `API_KEY`), so secrets are not surfaced in logs
  or the inspector.
- `get_available_implementations` now skips entries whose implementation class
  is `None`, consistent with the async path.

### Notes

- This remains a beta series (`2026.2.1bN`). When cutting the first stable
  release, bump the version, update the `Development Status` classifier, and move
  the entries above under a dated release heading.

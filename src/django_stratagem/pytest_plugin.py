"""Pytest plugin for projects that depend on django-stratagem.

Exposes opt-in fixtures for isolating the global, mutable registry state in
downstream test suites. Fixtures are deliberately NOT autouse so suites that
intentionally mutate registries are never surprised - request the fixture
explicitly where you want isolation.

Registered via the ``pytest11`` entry point, so installing django-stratagem
makes these fixtures available with no conftest wiring.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from .testing import isolate_registries


@pytest.fixture
def stratagem_isolation() -> Iterator[None]:
    """Snapshot all registry state on entry and restore it on exit.

    Wrap a test that defines or mutates registries so nothing leaks into other
    tests. Restores the global registry list, each registry's implementations
    map, and hierarchical parent/child relationships.
    """
    with isolate_registries():
        yield

# Testing code that uses registries

`django_stratagem.testing` provides context managers that keep the global,
mutable registry state isolated between tests.

## Register an implementation for one test

```python
from django_stratagem.testing import temporary_implementation

from myapp.registry import NotificationRegistry
from myapp.test_doubles import FakeChannel  # has a `slug`


def test_uses_fake_channel():
    with temporary_implementation(NotificationRegistry, FakeChannel):
        channel = NotificationRegistry.get(slug=FakeChannel.slug)
        assert channel.send("hi")
```

## Force a conditional implementation on or off

```python
from django_stratagem.testing import override_availability

from myapp.channels import WebhookChannel


def test_webhook_path():
    with override_availability(WebhookChannel, available=True):
        assert WebhookChannel.is_available({}) is True
```

## Isolate all registry state in a fixture

Wrap a fixture so any registries defined or mutated in a test are rolled back:

```python
import pytest

from django_stratagem.testing import isolate_registries


@pytest.fixture(autouse=True)
def _isolate_stratagem():
    with isolate_registries():
        yield
```

## Assert registry state

`django_stratagem.testing` ships assertion helpers so tests read clearly and
fail with useful messages:

```python
from django_stratagem.testing import (
    assert_available,
    assert_choices,
    assert_not_available,
    assert_not_registered,
    assert_registered,
)

from myapp.registry import NotificationRegistry
from myapp.channels import WebhookChannel


def test_registry_state():
    assert_registered(NotificationRegistry, "email")
    assert_not_registered(NotificationRegistry, "carrier_pigeon")
    # Choice slugs in priority order:
    assert_choices(NotificationRegistry, ["email", "sms", "push"])
    assert_available(WebhookChannel, {"user": some_user})
    assert_not_available(WebhookChannel, {})
```

A failing `assert_registered` lists the registry's currently registered slugs,
so a typo is easy to spot.

## Pytest plugin

Installing django-stratagem registers a `pytest11` plugin via its entry point,
so the `stratagem_isolation` fixture is available with no conftest wiring.
Request it in any test that defines or mutates registries:

```python
def test_with_isolated_registries(stratagem_isolation):
    class TempChannel(NotificationInterface):
        slug = "temp"

    NotificationRegistry.register(TempChannel)
    assert_registered(NotificationRegistry, "temp")
    # The registration is rolled back automatically when the test ends.
```

The fixture is opt-in (never autouse), so suites that intentionally mutate
global registry state are unaffected unless they request it. It is the shipped
equivalent of the hand-written `isolate_registries` fixture shown above.

## Notes and limitations

- `temporary_implementation` restores a registry's *implementations*, not
  registry *membership*. Defining a new `Registry` subclass adds it to the
  global list at class-creation time; use `isolate_registries` to roll that
  back.
- These helpers mutate process-global registry state and are not thread-safe.
  Use them within a single test process (the usual pytest model).

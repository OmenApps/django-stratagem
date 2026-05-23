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

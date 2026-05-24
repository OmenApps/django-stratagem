# Recipe Gallery

Each recipe is a complete, runnable example app under `examples/` in the
source tree. Copy an app into your project and adapt the slugs and logic.
All recipes are exercised by `tests/test_examples.py`, so they stay in sync
with the library.

## Notifications: conditional channels

`examples/notifications/` registers `email`, `sms`, and `webhook` channels.
The webhook channel is only available when `NOTIFICATIONS_WEBHOOK_ENABLED`
is set, demonstrating conditional availability with `SettingCondition`.

```python
from examples.notifications.registry import NotificationRegistry

channel = NotificationRegistry.get(slug="email")
channel.send("Build finished")  # "email:Build finished"
```

## Payments: a gateway stored per merchant

`examples/payments/` stores a merchant's chosen gateway in a
`RegistryClassField`. Set it by slug; read it back as the class.

```python
from examples.payments.models import Merchant

merchant = Merchant.objects.create(name="Acme", gateway="stripe")
merchant.gateway().charge(500)  # "stripe:500"
```

## Exports: a format chosen through an API

`examples/exports/` exposes the export-format registry as a
`DrfRegistryField` in a DRF serializer, validating the requested format.

```python
from examples.exports.serializers import ExportRequestSerializer

serializer = ExportRequestSerializer(data={"format": "csv", "row_count": 3})
serializer.is_valid()  # True
```

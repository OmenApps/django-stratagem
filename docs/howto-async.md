# Using registries from async code

Each context-aware read method has an `a`-prefixed async counterpart:
`aget`, `aget_choices` (cached), `aget_choices_for_context`,
`aget_available_implementations`, and `aget_for_context`. They share the sync
behavior and fall back to running sync hooks in a thread when an implementation
has not provided an async one. `aget_choices` uses Django's async cache API and
shares its cache key with the sync `get_choices`. These methods require a
running event loop (an async/ASGI context); from sync code, bridge them with
`asgiref.sync.async_to_sync`.

```python
from myapp.registry import NotificationRegistry


async def channels_view(request):
    context = {"request": request, "user": request.user}
    choices = await NotificationRegistry.aget_choices_for_context(context)
    channel = await NotificationRegistry.aget(slug="email")
    ...
```

## Native async conditions

Conditions evaluate via `acheck`. The built-in conditions wrap their sync
`is_met` automatically; compound conditions (`&`, `|`, `~`) await their
children, so a custom condition that overrides `acheck` is evaluated natively:

```python
from django_stratagem.conditions import Condition


class RemoteFlagCondition(Condition):
    def is_met(self, context):
        # sync fallback
        return False

    async def acheck(self, context):
        return await fetch_flag_from_service(context)
```

## Not yet async

The DRF serializer fields (`DrfRegistryField`, `DrfMultipleRegistryField`) do
not have async validation paths yet. Use them from synchronous serializers, or
bridge with `asgiref.sync` if you need them in an async flow.

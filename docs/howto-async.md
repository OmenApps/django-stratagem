# Using registries from async code

Each context-aware read method has an `a`-prefixed async counterpart. They
share the sync behaviour and fall back to running sync hooks in a thread when
an implementation has not provided an async one.

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

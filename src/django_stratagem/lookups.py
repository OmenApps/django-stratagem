import logging
from inspect import isclass

from django.db.models.lookups import Contains, Exact, IContains, IExact, In, Lookup

from .fields import (
    MultipleRegistryClassField,
    MultipleRegistryField,
    RegistryClassField,
    RegistryField,
)
from .utils import get_fully_qualified_name, stringify

logger = logging.getLogger(__name__)


# Lookup classes for registry fields
class RegistryFieldLookupMixin(Lookup):
    def get_prep_lookup(self) -> str | None:
        value = super().get_prep_lookup()
        if value is None:
            return None
        if isinstance(value, str):
            pass
        elif isinstance(value, (list, tuple)):
            value = stringify(value)
        elif isclass(value):
            value = get_fully_qualified_name(value)
        else:
            # Try to get the class of the instance
            value = get_fully_qualified_name(value.__class__)
        return value


class RegistryFieldContains(RegistryFieldLookupMixin, Contains):
    pass


class RegistryFieldIContains(RegistryFieldLookupMixin, IContains):
    pass


class RegistryFieldExact(RegistryFieldLookupMixin, Exact):
    pass


class RegistryFieldIExact(RegistryFieldLookupMixin, IExact):
    pass


class RegistryFieldIn(In):
    """In lookup that converts classes/instances to fully qualified name (FQN) strings."""

    def get_prep_lookup(self):
        if not hasattr(self.rhs, "__iter__"):
            raise ValueError("The QuerySet value for an 'in' lookup must be an iterable.")
        result = []
        for value in self.rhs:
            if value is None:
                result.append(None)
            elif isinstance(value, str):
                result.append(value)
            elif isclass(value):
                result.append(get_fully_qualified_name(value))
            else:
                result.append(get_fully_qualified_name(value.__class__))
        return result


# Register lookups
for field_class in [RegistryField, RegistryClassField]:
    field_class.register_lookup(RegistryFieldContains)
    field_class.register_lookup(RegistryFieldIContains)
    field_class.register_lookup(RegistryFieldExact)
    field_class.register_lookup(RegistryFieldIExact)
    field_class.register_lookup(RegistryFieldIn)

for field_class in [MultipleRegistryClassField, MultipleRegistryField]:
    field_class.register_lookup(RegistryFieldContains)
    field_class.register_lookup(RegistryFieldExact)
    field_class.register_lookup(RegistryFieldIExact)
    field_class.register_lookup(RegistryFieldIn)

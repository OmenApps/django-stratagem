from django_stratagem.interfaces import Interface
from django_stratagem.registry import Registry


class ExporterRegistry(Registry):
    implementations_module = "exporters"


class ExporterInterface(Interface):
    """Abstract base interface for Exporter implementations.

    Concrete implementations should define their own slug.
    """

    registry = ExporterRegistry

    def export(self):
        raise NotImplementedError

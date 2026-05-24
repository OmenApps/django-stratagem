"""A registry of export formats exposed through an API."""

from django_stratagem.interfaces import Interface
from django_stratagem.registry import Registry


class ExportFormatRegistry(Registry):
    """Registry of formats a record set can be exported to."""

    implementations_module = "formats"


class ExportFormat(Interface):
    """Base interface for an export format."""

    registry = ExportFormatRegistry

    content_type: str = "application/octet-stream"

    def render(self, rows: list[dict]) -> bytes:
        """Render ``rows`` to bytes in this format."""
        raise NotImplementedError

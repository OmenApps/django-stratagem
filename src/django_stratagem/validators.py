import logging
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

from .exceptions import RegistryNameError
from .utils import get_class

if TYPE_CHECKING:
    from .registry import Registry

logger = logging.getLogger(__name__)


@deconstructible
class ClassnameValidator(BaseValidator):
    """Validates that a value is a valid class name."""

    message = _("Ensure this value is valid class name (it is %(show_value)s).")
    code = "classname"

    def __call__(self, value: Any) -> None:
        cleaned = self.clean(value)
        params = {"show_value": cleaned}
        try:
            get_class(cleaned)
        except (ImportError, TypeError, RegistryNameError):
            raise ValidationError(self.message, code=self.code, params=params) from None


@deconstructible
class RegistryValidator(ClassnameValidator):
    """Validates that a value is registered in a specific registry."""

    message = _("Invalid entry `%(show_value)s`")
    message_many = _("Invalid entries `%(show_value)s`")
    code = "registry"

    def __init__(self, registry: "type[Registry]", message: str | None = None) -> None:
        super().__init__(registry, message)
        self.registry = registry

    def __call__(self, value: Any) -> None:
        cleaned = self.clean(value)
        params = {"show_value": cleaned}

        try:
            if isinstance(value, (list, tuple)):
                errs = []
                for c in cleaned:
                    if not self.registry.is_valid(c):
                        errs.append(c)

                if len(errs) == 1:
                    raise ValidationError(self.message, code=self.code, params={"show_value": errs[0]}) from None
                if len(errs) > 1:
                    raise ValidationError(
                        self.message_many, code=self.code, params={"show_value": ", ".join(errs)}
                    ) from None
            elif not self.registry.is_valid(value):
                raise ValidationError(self.message, code=self.code, params=params) from None

        except (ImportError, TypeError, RegistryNameError):
            raise ValidationError(self.message, code=self.code, params=params) from None

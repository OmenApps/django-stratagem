from django_stratagem import lookups  # noqa: F401 - registers custom lookups
from django_stratagem.conditions import (
    AllConditions,
    AnyCondition,
    AuthenticatedCondition,
    CallableCondition,
    Condition,
    DateRangeCondition,
    EnvironmentCondition,
    FeatureFlagCondition,
    GroupCondition,
    NotCondition,
    PermissionCondition,
    SettingCondition,
    StaffCondition,
    SuperuserCondition,
    TimeWindowCondition,
)
from django_stratagem.exceptions import (
    ImplementationNotFound,
    RegistryAttributeError,
    RegistryClassError,
    RegistryImportError,
    RegistryNameError,
)
from django_stratagem.fields import (
    AbstractRegistryField,
    HierarchicalRegistryField,
    MultipleHierarchicalRegistryField,
    MultipleRegistryClassField,
    MultipleRegistryField,
    RegistryClassField,
    RegistryField,
)
from django_stratagem.forms import (
    ContextAwareRegistryFormField,
    HierarchicalFormMixin,
    HierarchicalRegistryFormField,
    RegistryContextMixin,
    RegistryFormField,
    RegistryMultipleChoiceFormField,
)
from django_stratagem.interfaces import ConditionalInterface, HierarchicalInterface, Interface
from django_stratagem.plugins import PluginLoader, PluginProtocol
from django_stratagem.registry import (
    HierarchicalRegistry,
    Registry,
    RegistryRelationship,
    discover_registries,
    django_stratagem_registry,
    register,
    update_choices_fields,
)
from django_stratagem.utils import get_class, get_fully_qualified_name, import_by_name
from django_stratagem.validators import ClassnameValidator, RegistryValidator
from django_stratagem.widgets import HierarchicalRegistryWidget, RegistryWidget

__all__ = [
    # Registry classes
    "Registry",
    "HierarchicalRegistry",
    "RegistryRelationship",
    # Interfaces
    "ConditionalInterface",
    "Interface",
    "HierarchicalInterface",
    # Field classes
    "AbstractRegistryField",
    "RegistryField",
    "RegistryClassField",
    "MultipleRegistryField",
    "MultipleRegistryClassField",
    "HierarchicalRegistryField",
    "MultipleHierarchicalRegistryField",
    # Form fields
    "RegistryFormField",
    "RegistryMultipleChoiceFormField",
    "ContextAwareRegistryFormField",
    "HierarchicalRegistryFormField",
    "HierarchicalRegistryWidget",
    "RegistryWidget",
    "HierarchicalFormMixin",
    "RegistryContextMixin",
    # Conditions
    "Condition",
    "AllConditions",
    "AnyCondition",
    "NotCondition",
    "FeatureFlagCondition",
    "PermissionCondition",
    "SettingCondition",
    "CallableCondition",
    "AuthenticatedCondition",
    "StaffCondition",
    "SuperuserCondition",
    "GroupCondition",
    "TimeWindowCondition",
    "DateRangeCondition",
    "EnvironmentCondition",
    # Plugin system
    "PluginLoader",
    "PluginProtocol",
    # Validators
    "ClassnameValidator",
    "RegistryValidator",
    # Exceptions
    "ImplementationNotFound",
    "RegistryNameError",
    "RegistryClassError",
    "RegistryImportError",
    "RegistryAttributeError",
    # Functions
    "discover_registries",
    "update_choices_fields",
    "get_fully_qualified_name",
    "get_class",
    "import_by_name",
    "register",
    # Registry tracking
    "django_stratagem_registry",
]

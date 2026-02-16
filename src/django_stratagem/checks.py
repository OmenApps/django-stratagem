import logging

from django.core.checks import Error, Warning, register

logger = logging.getLogger(__name__)


@register("django_stratagem")
def check_registries(app_configs, **kwargs):
    """Validate registry configuration."""
    from .fields import AbstractRegistryField
    from .registry import HierarchicalRegistry, Registry, django_stratagem_registry

    errors = []

    # Check for duplicate slugs within registries
    for registry_cls in django_stratagem_registry:
        # Check that implementations_module is a non-empty string
        impl_module = getattr(registry_cls, "implementations_module", None)
        if not impl_module or not isinstance(impl_module, str):
            errors.append(
                Error(
                    f"Registry '{registry_cls.__name__}' has invalid implementations_module: {impl_module!r}",
                    hint="Set implementations_module to a non-empty string.",
                    id="django_stratagem.E001",
                )
            )

        # Check hierarchical parent references
        if isinstance(registry_cls, type) and issubclass(registry_cls, HierarchicalRegistry):
            parent = getattr(registry_cls, "parent_registry", None)
            if parent is not None and parent not in django_stratagem_registry:
                errors.append(
                    Warning(
                        f"Hierarchical registry '{registry_cls.__name__}' references parent "
                        f"'{parent.__name__}' which is not in the global registry.",
                        hint="Ensure the parent registry has implementations_module defined.",
                        id="django_stratagem.W001",
                    )
                )

    # Check model fields point to valid registries
    from django.apps import apps

    for model in apps.get_models():
        for field in model._meta.get_fields():
            if isinstance(field, AbstractRegistryField):
                registry = field.registry
                if registry is not None:
                    if not (isinstance(registry, type) and issubclass(registry, Registry)):
                        errors.append(
                            Error(
                                f"Field '{field.name}' on model '{model.__name__}' has invalid registry: {registry!r}",
                                hint="registry must be a Registry subclass.",
                                id="django_stratagem.E002",
                            )
                        )
                    elif registry not in django_stratagem_registry:
                        errors.append(
                            Warning(
                                f"Field '{field.name}' on model '{model.__name__}' references "
                                f"registry '{registry.__name__}' which is not in the global registry.",
                                hint="Ensure the registry has implementations_module defined.",
                                id="django_stratagem.W002",
                            )
                        )

    return errors

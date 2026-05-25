import difflib

_DOCS_URL = "https://django-stratagem.readthedocs.io/en/latest/"


def format_implementation_not_found(registry_name: str, slug: str, available_slugs: list[str]) -> str:
    """Build a friendly multi-line message for a missing registry slug.

    Includes the closest available slug (via ``difflib``), the full list of
    registered slugs, and a documentation link, so a typo or stale reference
    becomes a self-service fix instead of a dead-end lookup.
    """
    lines = [f"No implementation registered for slug '{slug}' in registry '{registry_name}'."]
    if available_slugs:
        matches = difflib.get_close_matches(slug, available_slugs, n=1)
        if matches:
            lines.append(f"Did you mean '{matches[0]}'?")
        lines.append(f"Available slugs: {', '.join(sorted(available_slugs))}.")
    else:
        lines.append("No implementations are registered in this registry yet.")
    lines.append(f"See {_DOCS_URL} for help.")
    return "\n".join(lines)


class ImplementationNotFound(KeyError):
    """Raised when an implementation is not found in the registry."""

    def __str__(self) -> str:
        # KeyError.__str__ wraps its message in repr() quotes and escapes
        # newlines, which mangles the multi-line "did you mean" guidance.
        # Return the first arg verbatim so the message renders cleanly while
        # the class stays a KeyError for existing callers/except clauses.
        if self.args:
            return str(self.args[0])
        return super().__str__()


class RegistryNameError(ValueError):
    """Raised when a registry name is invalid."""

    default_message = "Invalid value '%s': must be a valid python dotted name."

    def __init__(self, name: str, message: str | None = None) -> None:
        self.name = str(name)
        self.message = message or self.default_message
        super().__init__(self.message % self.name)

    def __repr__(self) -> str:
        return self.message % self.name


class RegistryClassError(ValueError):
    """Raised when a class reference is invalid."""

    default_message = "Invalid argument: '%s' is an invalid python name"

    def __init__(self, name: str, message: str | None = None) -> None:
        self.name = str(name)
        self.message = message or self.default_message
        super().__init__(self.message % self.name)

    def __repr__(self) -> str:
        return self.message % self.name


class RegistryImportError(ImportError):
    """Raised when importing a registry implementation fails."""


class RegistryAttributeError(AttributeError):
    """Raised when a registry attribute is not found."""

    default_message = "Unable to import %(name)s. %(module)s does not have %(class_str)s attribute"

    def __init__(self, name: str, module_path: str, class_str: str, message: str | None = None) -> None:
        self.module_path = module_path
        self.class_str = class_str
        self.message = message or self.default_message
        formatted = self.message % {"name": str(name), "module": self.module_path, "class_str": self.class_str}
        super().__init__(formatted)
        # Set self.name after super().__init__() because AttributeError.__init__() overwrites it
        self.name = str(name)

    def __repr__(self) -> str:
        return self.message % {"name": self.name, "module": self.module_path, "class_str": self.class_str}

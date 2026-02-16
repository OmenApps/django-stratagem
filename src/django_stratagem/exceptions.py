class ImplementationNotFound(KeyError):
    """Raised when an implementation is not found in the registry."""


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

from django.dispatch import Signal

# Signal arguments: registry, implementation
implementation_registered = Signal()

# Signal arguments: registry, slug
implementation_unregistered = Signal()

# Signal arguments: registry
registry_reloaded = Signal()

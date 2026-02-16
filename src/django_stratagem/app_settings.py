"""Settings for the django-stratagem package."""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_cache_timeout() -> int:
    """Return the cache timeout in seconds, reading from settings at call time."""
    return getattr(settings, "DJANGO_STRATAGEM", {}).get("CACHE_TIMEOUT", 300)


def get_skip_during_migrations() -> bool:
    """Return whether to skip registry operations during migrations."""
    return getattr(settings, "DJANGO_STRATAGEM", {}).get("SKIP_DURING_MIGRATIONS", True)

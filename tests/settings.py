from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ALLOWED_HOSTS: list[str] = []

BASE_DIR = Path(__file__).resolve().parent

DEBUG_ENV = os.environ.get("DEBUG")
DEBUG = DEBUG_ENV == "True"

DATABASE_NAME = ":memory:" if not DEBUG else BASE_DIR / "db.sqlite3"

DATABASES: dict[str, dict[str, Any]] = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASE_NAME,
    },
}

INSTALLED_APPS = [
    "django_stratagem",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local
    "tests.testapp",
    "tests.exporters",
    "tests.exporter_plugins",
]

MIDDLEWARE: list[str] = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "tests.urls"

SECRET_KEY = "NOTASECRET"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [BASE_DIR / "templates" / "django"],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

USE_TZ = True

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_URL = "/static/"

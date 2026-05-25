"""Consolidated read-only diagnostics for django-stratagem registries."""

from __future__ import annotations

import json

from django.core.checks import run_checks
from django.core.management.base import BaseCommand, CommandError

from django_stratagem.registry import django_stratagem_registry


class Command(BaseCommand):
    help = "Run read-only diagnostics across all registries and report problems."

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)",
        )

    def handle(self, *args, **kwargs):
        output_format = kwargs.get("format", "text")
        report = self._build_report()

        if output_format == "json":
            self.stdout.write(json.dumps(report, indent=2))
        else:
            self._render_text(report)

        if report["errors"]:
            # Non-zero exit for CI: BaseCommand turns CommandError into exit 1.
            raise CommandError(f"{len(report['errors'])} error(s) found. See report above.")

    def _build_report(self) -> dict:
        """Collect registry findings plus Django system checks for our tag."""
        registries = []
        errors: list[str] = []
        warnings: list[str] = []

        for registry_cls in django_stratagem_registry:
            broken = [slug for slug, meta in registry_cls.implementations.items() if meta.get("klass") is None]
            count = len(registry_cls.implementations)
            if count == 0:
                warnings.append(f"Registry '{registry_cls.__name__}' has no implementations.")
            for slug in broken:
                errors.append(f"Registry '{registry_cls.__name__}' slug '{slug}' has no implementation class.")
            registries.append(
                {
                    "name": registry_cls.__name__,
                    "module": registry_cls.__module__,
                    "implementation_count": count,
                    "slugs": list(registry_cls.implementations),
                    "broken_slugs": broken,
                }
            )

        # Reuse the registered Django system checks for django_stratagem.
        for message in run_checks(tags=["django_stratagem"]):
            text = f"[{message.id}] {message.msg}"
            if message.is_serious():
                errors.append(text)
            else:
                warnings.append(text)

        return {"registries": registries, "warnings": warnings, "errors": errors}

    def _render_text(self, report: dict) -> None:
        for reg in report["registries"]:
            header = f"{reg['name']} ({reg['module']}) - {reg['implementation_count']} implementation(s)"
            self.stdout.write(self.style.SUCCESS(header))  # type: ignore[attr-defined]
            if reg["slugs"]:
                self.stdout.write(f"  slugs: {', '.join(reg['slugs'])}")
            for slug in reg["broken_slugs"]:
                self.stdout.write(self.style.ERROR(f"  broken: slug '{slug}' has no implementation class"))  # type: ignore[attr-defined]

        for warning in report["warnings"]:
            self.stdout.write(self.style.WARNING(f"WARNING: {warning}"))  # type: ignore[attr-defined]

        if report["errors"]:
            for error in report["errors"]:
                self.stdout.write(self.style.ERROR(f"ERROR: {error}"))  # type: ignore[attr-defined]
        else:
            self.stdout.write(self.style.SUCCESS("No errors found."))  # type: ignore[attr-defined]

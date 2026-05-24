"""Concrete export formats for the exports example."""

import csv
import io
import json

from .registry import ExportFormat


class CsvFormat(ExportFormat):
    slug = "csv"
    description = "Comma-separated values"
    content_type = "text/csv"
    priority = 10

    def render(self, rows: list[dict]) -> bytes:
        buffer = io.StringIO()
        if rows:
            writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return buffer.getvalue().encode("utf-8")


class JsonFormat(ExportFormat):
    slug = "json"
    description = "JSON array"
    content_type = "application/json"
    priority = 20

    def render(self, rows: list[dict]) -> bytes:
        return json.dumps(rows).encode("utf-8")

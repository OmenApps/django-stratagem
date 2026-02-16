from tests.exporters.registry import ExporterInterface


class CsvExporter(ExporterInterface):
    slug = "csv"

    def export(self):
        return "exported"

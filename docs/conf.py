"""Sphinx configuration for django-stratagem documentation."""

from datetime import datetime

project = "django-stratagem"
author = "Jack Linke"
copyright = f"{datetime.now().year}, {author}"

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_togglebutton",
    "sphinxcontrib.mermaid",
    "sphinx.ext.intersphinx",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "html_image",
    "smartquotes",
    "replacements",
    "substitution",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": ("https://docs.djangoproject.com/en/5.2/", None),
}

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# MyST warns about file.md#anchor cross-references even though it renders them
# correctly as working HTML links (e.g. usage.html#model-fields). This is a
# known limitation of MyST's cross-reference validator - the links work fine.
suppress_warnings = ["myst.xref_missing"]

html_theme = "furo"
html_extra_path = ["llms.txt", "llms-full.txt"]

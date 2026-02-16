"""Nox sessions for django-stratagem."""

import sys

import nox

DJANGO_STABLE_VERSION = "5.2"
DJANGO_VERSIONS = ["4.2", "5.1", "5.2", "6.0"]
PYTHON_STABLE_VERSION = "3.14"
PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]
PACKAGE = "django_stratagem"

nox.options.default_venv_backend = "uv"
nox.options.sessions = ["pre-commit", "pip-audit", "tests"]


@nox.session(name="pre-commit", python=PYTHON_STABLE_VERSION)
def precommit(session: nox.Session) -> None:
    """Run pre-commit hooks on all files."""
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files")


@nox.session(name="pip-audit", python=PYTHON_STABLE_VERSION)
def pip_audit(session: nox.Session) -> None:
    """Scan dependencies for known vulnerabilities."""
    pyproject = nox.project.load_toml("pyproject.toml")
    deps = nox.project.dependency_groups(pyproject, "dev")
    session.install(".", *deps)
    session.install("pip-audit")
    session.run("pip-audit")


@nox.session(
    python=PYTHON_VERSIONS,
    tags=["tests"],
)
@nox.parametrize("django", DJANGO_VERSIONS)
def tests(session: nox.Session, django: str) -> None:
    """Run the test suite across Python and Django versions."""
    # Django 4.2 supports only Python 3.11-3.12
    if django == "4.2" and session.python in ("3.13", "3.14"):
        session.skip("Django 4.2 supports only Python 3.11-3.12")
    # Django 5.1 supports only Python 3.11-3.13
    if django == "5.1" and session.python == "3.14":
        session.skip("Django 5.1 supports only Python 3.11-3.13")
    # Django 6.0 requires Python 3.12+
    if django == "6.0" and session.python == "3.11":
        session.skip("Django 6.0 requires Python 3.12+")

    pyproject = nox.project.load_toml("pyproject.toml")
    deps = nox.project.dependency_groups(pyproject, "dev")
    session.install(".[drf]", *deps)
    session.install(f"django~={django}.0")
    session.run(
        "coverage",
        "run",
        "-m",
        "pytest",
        "-vv",
        *session.posargs,
    )

    if sys.stdin.isatty():
        session.notify("coverage")


@nox.session(python=PYTHON_STABLE_VERSION)
def coverage(session: nox.Session) -> None:
    """Combine and report coverage."""
    session.install("coverage[toml]")
    session.run("coverage", "combine", success_codes=[0, 1])
    session.run("coverage", "report")


@nox.session(name="llms-full", python=False)
def llms_full(session: nox.Session) -> None:
    """Generate docs/llms-full.txt from documentation source files."""
    from pathlib import Path

    files = [
        "docs/quickstart.md",
        "docs/tutorial.md",
        "docs/tutorial-construction.md",
        "docs/howto-fields.md",
        "docs/howto-forms-admin.md",
        "docs/howto-templates.md",
        "docs/howto-conditions.md",
        "docs/howto-hierarchies.md",
        "docs/howto-drf.md",
        "docs/howto-plugins.md",
        "docs/explanation.md",
        "docs/hooks.md",
        "docs/api.md",
    ]

    header = (
        "# django-stratagem - Complete Documentation\n"
        "\n"
        "> Registry-based plugin architecture for Django. Define registries of\n"
        "> implementations that are auto-discovered at startup, stored in model fields,\n"
        "> and exposed through forms, admin, DRF, and template tags. Supports\n"
        "> conditional availability, hierarchical registries, and third-party plugins.\n"
        "\n"
    )

    outfile = Path("docs/llms-full.txt")
    with outfile.open("w") as out:
        out.write(header)
        for f in files:
            out.write("---\n\n")
            out.write(f"<!-- source: {f} -->\n\n")
            out.write(Path(f).read_text())
            out.write("\n")

    session.log(f"Generated {outfile}")


@nox.session(name="docs", python=PYTHON_STABLE_VERSION)
def docs(session: nox.Session) -> None:
    """Build the Sphinx documentation."""
    pyproject = nox.project.load_toml("pyproject.toml")
    deps = nox.project.dependency_groups(pyproject, "docs")
    session.install(".", *deps)
    session.run("sphinx-build", "-W", "-E", "-b", "html", "docs", "docs/_build/html", *session.posargs)

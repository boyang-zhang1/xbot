"""xbot package: modern toolkit for X scraping, translation, and publishing."""

from importlib import metadata


def get_version() -> str:
    """Return the package version as defined in pyproject.toml."""
    try:
        return metadata.version("xbot")
    except metadata.PackageNotFoundError:  # pragma: no cover - during local dev without install
        return "0.0.0"

__all__ = ["get_version"]

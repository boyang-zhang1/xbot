"""twitter_bot package: modern toolkit for Twitter scraping, translation, and publishing."""

from importlib import metadata

def get_version() -> str:
    """Return the package version as defined in pyproject.toml."""
    try:
        return metadata.version("twitter-bot")
    except metadata.PackageNotFoundError:  # pragma: no cover - during local dev without install
        return "0.0.0"

__all__ = ["get_version"]

"""Structured logging configuration for the toolkit."""

from __future__ import annotations

import logging
import logging.config
from functools import lru_cache
from pathlib import Path
from typing import Any

try:  # pragma: no cover - structure depends on optional dependency
    import structlog
except ImportError:  # pragma: no cover - fallback for constrained envs
    structlog = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from pythonjsonlogger import jsonlogger
except ImportError:  # pragma: no cover - fallback
    jsonlogger = None  # type: ignore[assignment]

from xbot.config.settings import Settings, get_settings

DEFAULT_LOG_LEVEL = "INFO"


@lru_cache()
def configure_logging(settings: Settings | None = None) -> structlog.BoundLogger:
    """Configure structlog + standard logging and return a bound logger.

    The configuration writes JSON-formatted logs to ``settings.log_root`` while
    keeping a human-friendly console sink. Idempotent so libraries can call it
    without fighting over global state.
    """

    settings = settings or get_settings()
    log_dir = settings.log_root
    log_dir.mkdir(parents=True, exist_ok=True)
    file_path = log_dir / "xbot.log"

    logging.config.dictConfig(_build_logging_config(file_path))

    if structlog is None:
        return logging.getLogger("xbot")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.EventRenamer("message"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(DEFAULT_LOG_LEVEL)),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()


def _build_logging_config(log_path: Path) -> dict[str, Any]:
    formatter_config: dict[str, Any]
    if jsonlogger is not None:
        formatter_config = {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    else:
        formatter_config = {
            "class": "logging.Formatter",
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "class": "logging.Formatter",
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            },
            "json": formatter_config,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "level": DEFAULT_LOG_LEVEL,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": str(log_path),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 5,
                "level": DEFAULT_LOG_LEVEL,
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": DEFAULT_LOG_LEVEL,
        },
    }


__all__ = ["configure_logging"]

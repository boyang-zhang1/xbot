"""Shared Pydantic base classes for domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class ModelBase(PydanticBaseModel):
    """Base model with useful defaults for all domain entities."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    @staticmethod
    def ensure_utc(dt: datetime) -> datetime:
        """Return a timezone-aware UTC datetime."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def from_timestamp(timestamp: int | float) -> datetime:
        """Convert a Unix timestamp into a UTC datetime."""
        return datetime.fromtimestamp(float(timestamp), tz=timezone.utc)


__all__ = ["ModelBase"]

"""Domain models for translated tweet content."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field, field_validator, model_validator

from .base import ModelBase


class TranslationStatus(str, Enum):
    """Lifecycle state for a translation."""

    DRAFT = "draft"
    READY = "ready"
    PUBLISHED = "published"


class TranslationSegment(ModelBase):
    """Translated text paired with the original tweet identifier."""

    tweet_id: str
    text: str
    has_media: bool = False


class TranslationRecord(ModelBase):
    """Translated view of a thread."""

    author_handle: str
    root_tweet_id: str
    segments: tuple[TranslationSegment, ...]
    titles: tuple[str, ...] = Field(default_factory=tuple)
    status: TranslationStatus = Field(default=TranslationStatus.DRAFT)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    manual_override: bool = False

    @model_validator(mode="after")
    def _ensure_segments(self) -> TranslationRecord:
        if not self.segments:
            raise ValueError("Translation requires at least one segment")
        return self

    @property
    def root(self) -> TranslationSegment:
        return self.segments[0]

    @field_validator("titles", mode="before")
    @classmethod
    def _normalize_titles(cls, value: tuple[str, ...] | str | None) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split("||") if part.strip())
        return tuple(value)

    def mark_updated(self) -> TranslationRecord:
        return self.model_copy(update={"updated_at": datetime.now(tz=UTC)})

    def mark_published(self) -> TranslationRecord:
        """Return a copy flagged as published and refresh timestamps."""

        return self.model_copy(
            update={
                "status": TranslationStatus.PUBLISHED,
                "updated_at": datetime.now(tz=UTC),
            }
        )


__all__ = [
    "TranslationRecord",
    "TranslationSegment",
    "TranslationStatus",
]

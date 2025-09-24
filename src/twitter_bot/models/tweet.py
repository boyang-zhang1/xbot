"""Domain models for tweets and threads."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Tuple

from pydantic import Field, field_validator, model_validator

from .base import ModelBase


class MediaType(str, Enum):
    """Supported media categories for a tweet."""

    PHOTO = "photo"
    VIDEO = "video"


class MediaAsset(ModelBase):
    """Metadata for a media item associated with a tweet."""

    media_id: str = Field(alias="ID")
    url: str = Field(alias="URL")
    preview_url: str | None = Field(default=None, alias="Preview")
    media_type: MediaType = Field(default=MediaType.PHOTO)

    @field_validator("media_type", mode="before")
    @classmethod
    def _coerce_media_type(cls, value: Any) -> MediaType:
        if isinstance(value, MediaType):
            return value
        if isinstance(value, str):
            return MediaType(value.lower())
        raise ValueError("Unsupported media type")


class TweetSegment(ModelBase):
    """Single tweet within a thread."""

    tweet_id: str = Field(alias="ID")
    text: str = Field(alias="Text")
    timestamp: datetime = Field(alias="Timestamp")
    media: Tuple[MediaAsset, ...] = Field(default_factory=tuple)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _coerce_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, (int, float)):
            return ModelBase.from_timestamp(value)
        if isinstance(value, str) and value.isdigit():
            return ModelBase.from_timestamp(float(value))
        if isinstance(value, datetime):
            return ModelBase.ensure_utc(value)
        raise ValueError("Unsupported timestamp value")

    @field_validator("media", mode="before")
    @classmethod
    def _coerce_media(cls, value: Any) -> Tuple[MediaAsset, ...]:
        if value is None:
            return tuple()
        if isinstance(value, Iterable):
            assets = []
            for item in value:
                if isinstance(item, MediaAsset):
                    assets.append(item)
                elif isinstance(item, dict):
                    inferred_type = item.get("media_type") or item.get("type")
                    if not inferred_type:
                        inferred_type = MediaType.PHOTO.value
                    asset = MediaAsset(
                        media_id=item.get("ID") or item.get("media_id"),
                        url=item.get("URL") or item.get("url"),
                        preview_url=item.get("Preview") or item.get("preview_url"),
                        media_type=MediaType(inferred_type.lower()),
                    )
                    assets.append(asset)
                else:
                    raise ValueError("Unsupported media payload")
            return tuple(assets)
        raise ValueError("Unsupported media payload")


class TweetThread(ModelBase):
    """Full thread captured for a given author."""

    author_handle: str
    tweets: Tuple[TweetSegment, ...]
    collected_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    source: str = Field(default="twitter")

    @model_validator(mode="after")
    def _ensure_tweets(self) -> "TweetThread":
        if not self.tweets:
            raise ValueError("A thread must contain at least one tweet segment")
        return self

    @property
    def root(self) -> TweetSegment:
        return self.tweets[0]

    @property
    def root_id(self) -> str:
        return self.root.tweet_id

    @property
    def tweet_ids(self) -> Tuple[str, ...]:
        return tuple(segment.tweet_id for segment in self.tweets)

    @classmethod
    def from_legacy(cls, author_handle: str, legacy_record: dict[str, Any]) -> "TweetThread":
        """Create a thread from the legacy JSON schema."""

        def build_media(items: list[dict[str, Any]], media_type: MediaType) -> Tuple[MediaAsset, ...]:
            return tuple(
                MediaAsset(
                    media_id=item.get("ID", ""),
                    url=item.get("URL", ""),
                    preview_url=item.get("Preview"),
                    media_type=media_type,
                )
                for item in items or []
            )

        def build_segment(payload: dict[str, Any]) -> TweetSegment:
            photos = build_media(payload.get("Photos", []), MediaType.PHOTO)
            videos = build_media(payload.get("Videos", []), MediaType.VIDEO)
            media = photos + videos
            return TweetSegment(
                ID=payload.get("ID", ""),
                Text=payload.get("Text", ""),
                Timestamp=payload.get("Timestamp", 0),
                media=media,
            )

        segments = [build_segment(legacy_record)]
        for child in legacy_record.get("Thread", []) or []:
            segments.append(build_segment(child))

        collected_reference = legacy_record.get("Timestamp", 0)
        collected_at = ModelBase.from_timestamp(collected_reference) if collected_reference else datetime.now(tz=timezone.utc)

        return cls(author_handle=author_handle, tweets=tuple(segments), collected_at=collected_at)


LegacyThreadPayload = dict[str, Any]

__all__ = [
    "MediaAsset",
    "MediaType",
    "TweetSegment",
    "TweetThread",
    "LegacyThreadPayload",
]

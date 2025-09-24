"""Helpers to convert legacy JSON payloads into modern domain models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Tuple

from twitter_bot.models import (
    LegacyThreadPayload,
    TranslationRecord,
    TranslationSegment,
    TranslationStatus,
    TweetThread,
)


def load_legacy_threads(path: Path) -> Iterator[Tuple[str, TweetThread]]:
    """Yield author handle and converted threads from the legacy tweets file."""

    payload = _load_json(path)
    for author_handle, threads in payload.items():
        for record in threads:
            yield author_handle, TweetThread.from_legacy(author_handle, record)


def load_legacy_translations(path: Path) -> Iterator[Tuple[str, TranslationRecord]]:
    """Yield author handle and translation records from the legacy translations file."""

    payload = _load_json(path)
    for author_handle, translations in payload.items():
        for record in translations:
            yield author_handle, translation_from_legacy(author_handle, record)


def translation_from_legacy(author_handle: str, record: LegacyThreadPayload) -> TranslationRecord:
    """Convert a legacy translation payload into a `TranslationRecord`."""

    segments = [
        TranslationSegment(
            tweet_id=record.get("ID", ""),
            text=record.get("Text", ""),
            has_media=_has_media(record),
        )
    ]

    for child in record.get("Thread", []) or []:
        segments.append(
            TranslationSegment(
                tweet_id=child.get("ID", ""),
                text=child.get("Text", ""),
                has_media=_has_media(child),
            )
        )

    timestamp = record.get("Timestamp", 0)
    created_at = datetime.now(tz=timezone.utc)
    if timestamp:
        created_at = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)

    titles = tuple(record.get("Titles", []) or [])

    return TranslationRecord(
        author_handle=author_handle,
        root_tweet_id=record.get("ID", ""),
        segments=tuple(segments),
        titles=titles,
        status=TranslationStatus.READY,
        created_at=created_at,
        updated_at=created_at,
    )


def _has_media(payload: LegacyThreadPayload) -> bool:
    return bool(payload.get("Photos") or payload.get("Videos"))


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


__all__ = ["load_legacy_threads", "load_legacy_translations", "translation_from_legacy"]

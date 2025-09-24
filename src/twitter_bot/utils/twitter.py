"""Utility helpers related to Twitter constraints."""

from __future__ import annotations

import re

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
MAX_TWEET_LENGTH = 280
MEDIA_LINK_RESERVATION = 23


def approximate_length(text: str) -> int:
    """Approximate tweet length accounting for URL contractions."""

    length = 0
    remaining = text
    for match in URL_PATTERN.finditer(text):
        length += MEDIA_LINK_RESERVATION
        start, end = match.span()
        remaining = remaining.replace(match.group(), "", 1)
    length += len(remaining)
    return length


def ensure_within_limit(text: str) -> None:
    """Raise ValueError if *text* exceeds tweet length constraints."""

    if approximate_length(text) > MAX_TWEET_LENGTH:
        raise ValueError("Tweet text exceeds Twitter length limit")


__all__ = ["approximate_length", "ensure_within_limit", "MAX_TWEET_LENGTH"]

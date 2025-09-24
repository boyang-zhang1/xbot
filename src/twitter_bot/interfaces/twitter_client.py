"""Twitter client abstractions for scraping and publishing."""

from __future__ import annotations

from typing import Protocol, Sequence

from twitter_bot.models import TweetThread


class ScraperClient(Protocol):
    """Client capable of fetching tweet threads for a given handle."""

    def fetch_threads(self, author_handle: str, limit: int = 40) -> Sequence[TweetThread]:
        ...


__all__ = ["ScraperClient"]

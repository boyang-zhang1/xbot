"""X client abstractions for scraping and publishing."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from xbot.models import TweetThread


class ScraperClient(Protocol):
    """Client capable of fetching tweet threads for a given handle."""

    def fetch_threads(self, author_handle: str, limit: int = 40) -> Sequence[TweetThread]:
        ...


class PublisherClient(Protocol):
    """Client capable of publishing tweets and threads."""

    def post_tweet(
        self,
        text: str,
        media_urls: Sequence[str] | None = None,
        in_reply_to: str | None = None,
    ) -> str:
        ...


__all__ = ["ScraperClient", "PublisherClient"]

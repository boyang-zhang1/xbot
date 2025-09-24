"""High-level orchestration for scraping tweets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from twitter_bot.config.settings import Settings, get_settings
from twitter_bot.interfaces.storage import TweetRepository
from twitter_bot.interfaces.twitter_client import ScraperClient
from twitter_bot.models import TweetThread


@dataclass(frozen=True)
class ScrapeResult:
    handle: str
    fetched: int
    stored: int


@dataclass(frozen=True)
class ScrapeSummary:
    results: Sequence[ScrapeResult]

    @property
    def total_fetched(self) -> int:
        return sum(result.fetched for result in self.results)

    @property
    def total_stored(self) -> int:
        return sum(result.stored for result in self.results)


class ScraperService:
    """Coordinate fetching threads and persisting them via a repository."""

    def __init__(
        self,
        repository: TweetRepository,
        client: ScraperClient,
        settings: Settings | None = None,
    ) -> None:
        self._repository = repository
        self._client = client
        self._settings = settings or get_settings()

    def sync_handle(self, handle: str, limit: int = 40) -> ScrapeResult:
        threads = self._client.fetch_threads(handle, limit=limit)
        stored = 0
        for thread in threads:
            existing = self._repository.get(thread.root_id)
            self._repository.upsert(thread)
            if existing is None:
                stored += 1
        return ScrapeResult(handle=handle, fetched=len(threads), stored=stored)

    def sync_all(self, limit: int = 40) -> ScrapeSummary:
        results: List[ScrapeResult] = []
        for handle in self._settings.scraper.handles:
            result = self.sync_handle(handle, limit=limit)
            results.append(result)
        return ScrapeSummary(results=tuple(results))


__all__ = ["ScraperService", "ScrapeResult", "ScrapeSummary"]

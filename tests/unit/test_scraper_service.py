from collections.abc import Sequence
from dataclasses import dataclass

from xbot.interfaces.storage import TweetRepository
from xbot.interfaces.x_client import ScraperClient
from xbot.models import TweetSegment, TweetThread
from xbot.services.scraping import ScraperService


class InMemoryTweetRepository(TweetRepository):
    def __init__(self) -> None:
        self._store: dict[str, TweetThread] = {}

    def upsert(self, thread: TweetThread) -> None:
        self._store[thread.root_id] = thread

    def get(self, root_tweet_id: str) -> TweetThread | None:
        return self._store.get(root_tweet_id)

    def list_all(self) -> Sequence[TweetThread]:
        return list(self._store.values())

    def list_for_handle(self, author_handle: str) -> Sequence[TweetThread]:
        return [thread for thread in self._store.values() if thread.author_handle == author_handle]

    def delete(self, root_tweet_id: str) -> None:
        self._store.pop(root_tweet_id, None)


@dataclass
class StaticScraperClient(ScraperClient):
    threads: dict[str, list[TweetThread]]

    def fetch_threads(self, author_handle: str, limit: int = 40) -> Sequence[TweetThread]:
        return self.threads.get(author_handle, [])[:limit]


def make_thread(root_id: str, handle: str) -> TweetThread:
    return TweetThread(
        author_handle=handle,
        tweets=(
            TweetSegment(ID=root_id, Text="Root", Timestamp=1_700_000_000, media=[]),
            TweetSegment(ID=f"{root_id}-1", Text="Child", Timestamp=1_700_000_100, media=[]),
        ),
    )


def test_scraper_service_sync_handle(monkeypatch):
    threads = {"handle": [make_thread("600", "handle"), make_thread("601", "handle")]}
    repo = InMemoryTweetRepository()
    client = StaticScraperClient(threads=threads)

    monkeypatch.setenv("TWITTER_SCRAPER_HANDLES", "handle")
    from xbot.config import settings as settings_module

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    service = ScraperService(repository=repo, client=client)

    result = service.sync_handle("handle")

    assert result.fetched == 2
    assert result.stored == 2
    assert repo.get("600") is not None


def test_scraper_service_sync_all(monkeypatch):
    threads = {
        "alpha": [make_thread("700", "alpha")],
        "beta": [make_thread("701", "beta")],
    }
    repo = InMemoryTweetRepository()
    client = StaticScraperClient(threads=threads)

    monkeypatch.setenv("TWITTER_SCRAPER_HANDLES", "alpha,beta")
    from xbot.config import settings as settings_module

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    service = ScraperService(repository=repo, client=client)

    summary = service.sync_all()

    assert summary.total_fetched == 2
    assert summary.total_stored == 2
    assert repo.get("700") is not None
    assert repo.get("701") is not None

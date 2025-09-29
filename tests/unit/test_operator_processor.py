from dataclasses import dataclass

from xbot.services.operator import CommandContext, CommandProcessor


@dataclass
class StubResult:
    fetched: int
    stored: int


class StubScraper:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []
        self._store: list[str] = []

    def sync_handle(self, handle: str, limit: int = 40) -> StubResult:
        self.calls.append((handle, limit))
        self._store.append(handle)
        return StubResult(fetched=limit, stored=1)


class StubTranslator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool, object | None]] = []
        self._store: list[str] = []

    def translate_thread(self, tweet_id: str, *, force: bool = False, include_titles=None):
        self.calls.append((tweet_id, force, include_titles))
        self._store.append(tweet_id)

        class Result:
            created = True

        return Result()


class StubPublisher:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def publish(
        self,
        tweet_id: str,
        *,
        profile_name: str = "default",
        title_index=None,
        dry_run: bool = False,
        force: bool = False,
    ):
        self.calls.append(
            {
                "tweet_id": tweet_id,
                "profile": profile_name,
                "title_index": title_index,
                "dry_run": dry_run,
                "force": force,
            }
        )

        class Report:
            posted_tweet_ids = ("1", "2")
            plan = type("Plan", (), {"items": (1, 2)})

        return Report()


@dataclass
class FakeJob:
    job_id: str
    name: str


class StubScheduler:
    def __init__(self) -> None:
        self.enqueued: list[str] = []

    def enqueue(self, name: str, *, payload=None, run_at=None):
        self.enqueued.append(name)
        return FakeJob(job_id="job-1", name=name)


class StubRepo:
    def __init__(self, items):
        self._items = items

    def list_all(self):
        return self._items

    def list_pending(self):
        return [FakeJob(job_id="1", name="test")]


def make_processor(with_scheduler: bool = True) -> tuple[CommandProcessor, StubScraper, StubTranslator, StubPublisher, StubScheduler | None]:
    scraper = StubScraper()
    translator = StubTranslator()
    publisher = StubPublisher()
    scheduler = StubScheduler() if with_scheduler else None
    tweets_repo = StubRepo(["t1"])
    translations_repo = StubRepo(["x"])
    jobs_repo = StubRepo([])

    context = CommandContext(
        scraper=scraper,
        translator=translator,
        publisher=publisher,
        scheduler=scheduler,
        tweet_repository=tweets_repo,
        translation_repository=translations_repo,
        job_repository=jobs_repo,
    )
    processor = CommandProcessor(context)
    return processor, scraper, translator, publisher, scheduler


def test_help_command():
    processor, *_ = make_processor()
    response = processor.handle("/help")
    assert "Available commands" in response


def test_scrape_command():
    processor, scraper, *_ = make_processor()
    response = processor.handle("/scrape handle 5")
    assert "Scraped" in response
    assert scraper.calls == [("handle", 5)]


def test_translate_command_flags():
    processor, _, translator, _, _ = make_processor()
    processor.handle("/translate 123 --force --no-titles")
    assert translator.calls == [("123", True, False)]


def test_publish_command():
    processor, _, _, publisher, _ = make_processor()
    response = processor.handle("/publish 321 --profile alt --dry-run --title 2")
    assert "Dry run" in response
    assert publisher.calls[0]["profile"] == "alt"
    assert publisher.calls[0]["dry_run"] is True
    assert publisher.calls[0]["title_index"] == 2


def test_queue_without_scheduler():
    processor, *_ = make_processor(with_scheduler=False)
    response = processor.handle("/queue scrape handle")
    assert response == "Scheduler is not configured."


def test_queue_with_scheduler():
    processor, *_scraper, scheduler = make_processor()
    response = processor.handle("/queue scrape handle")
    assert "Queued job" in response
    assert scheduler.enqueued == ["scrape-handle"]


def test_status_command():
    processor, *_ = make_processor()
    response = processor.handle("/status")
    assert "Stored tweets" in response

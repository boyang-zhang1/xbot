from collections.abc import Sequence
from dataclasses import dataclass

from xbot.interfaces.storage import TranslationRepository, TweetRepository
from xbot.interfaces.translation_provider import TranslationProvider
from xbot.models import TranslationRecord, TranslationSegment, TweetSegment, TweetThread
from xbot.services.translation import TranslationResult, TranslationService


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


class InMemoryTranslationRepository(TranslationRepository):
    def __init__(self) -> None:
        self._store: dict[str, TranslationRecord] = {}

    def upsert(self, record: TranslationRecord) -> None:
        self._store[record.root_tweet_id] = record

    def get(self, root_tweet_id: str) -> TranslationRecord | None:
        return self._store.get(root_tweet_id)

    def list_all(self) -> Sequence[TranslationRecord]:
        return list(self._store.values())

    def list_for_handle(self, author_handle: str) -> Sequence[TranslationRecord]:
        return [record for record in self._store.values() if record.author_handle == author_handle]

    def delete(self, root_tweet_id: str) -> None:
        self._store.pop(root_tweet_id, None)


@dataclass
class FakeProvider(TranslationProvider):
    generated: dict[str, Sequence[str]]
    titles_requested: list[int]

    def translate_segments(self, thread: TweetThread) -> Sequence[str]:
        output = tuple(f"translated:{segment.text}" for segment in thread.tweets)
        self.generated[thread.root_id] = output
        return output

    def generate_titles(
        self, thread: TweetThread, translated_segments: Sequence[str], count: int
    ) -> Sequence[str]:
        self.titles_requested.append(count)
        return tuple(f"title-{i}" for i in range(count))

    def build_manual_prompt(self, thread: TweetThread) -> str:
        return f"prompt:{thread.root_id}"


def make_thread(root_id: str, handle: str) -> TweetThread:
    return TweetThread(
        author_handle=handle,
        tweets=(
            TweetSegment(ID=root_id, Text="Root", Timestamp=1_700_000_000, media=[]),
            TweetSegment(ID=f"{root_id}-1", Text="Child", Timestamp=1_700_000_100, media=[]),
        ),
    )


def test_translate_thread_creates_record(monkeypatch):
    tweet_repo = InMemoryTweetRepository()
    translation_repo = InMemoryTranslationRepository()
    provider = FakeProvider(generated={}, titles_requested=[])

    tweet_repo.upsert(make_thread("800", "handle"))

    monkeypatch.setenv("ENABLE_TRANSLATION_TITLES", "true")
    from xbot.config import settings as settings_module

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    service = TranslationService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        provider=provider,
    )

    result = service.translate_thread("800")

    assert isinstance(result, TranslationResult)
    assert result.created is True
    assert translation_repo.get("800") is not None
    assert provider.titles_requested == [5]

    # Second call should read existing record without re-translation
    second = service.translate_thread("800")
    assert second.created is False


def test_manual_prompts(monkeypatch):
    tweet_repo = InMemoryTweetRepository()
    translation_repo = InMemoryTranslationRepository()
    provider = FakeProvider(generated={}, titles_requested=[])

    tweet_repo.upsert(make_thread("900", "handle"))

    monkeypatch.setenv("ENABLE_TRANSLATION_TITLES", "false")
    from xbot.config import settings as settings_module

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    service = TranslationService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        provider=provider,
    )

    prompt = service.manual_translation_prompt("900")
    assert prompt == "prompt:900"

    title_prompt = service.manual_title_prompt("900", count=3)
    assert "Create 3 alternate titles" in title_prompt


def test_translate_pending(monkeypatch):
    tweet_repo = InMemoryTweetRepository()
    translation_repo = InMemoryTranslationRepository()
    provider = FakeProvider(generated={}, titles_requested=[])

    tweet_repo.upsert(make_thread("910", "handle"))
    tweet_repo.upsert(make_thread("911", "handle"))

    monkeypatch.setenv("ENABLE_TRANSLATION_TITLES", "false")
    from xbot.config import settings as settings_module

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    service = TranslationService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        provider=provider,
    )

    results = service.translate_pending()
    assert len(results) == 2
    assert translation_repo.get("910") is not None
    assert translation_repo.get("911") is not None


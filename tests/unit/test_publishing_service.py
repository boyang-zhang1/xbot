from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import pytest

from xbot.config import settings as settings_module
from xbot.interfaces.storage import TranslationRepository, TweetRepository
from xbot.models import (
    MediaAsset,
    MediaType,
    TranslationRecord,
    TranslationSegment,
    TranslationStatus,
    TweetSegment,
    TweetThread,
)
from xbot.services.publishing import PublishReport, PublisherService


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
class FakePublisherClient:
    posts: list[dict]

    def post_tweet(
        self,
        text: str,
        media_urls: Sequence[str] | None = None,
        in_reply_to: str | None = None,
    ) -> str:
        identifier = f"posted-{len(self.posts) + 1}"
        self.posts.append({"text": text, "media": tuple(media_urls or ()), "reply_to": in_reply_to})
        return identifier


def make_thread() -> TweetThread:
    return TweetThread(
        author_handle="handle",
        tweets=(
            TweetSegment(
                ID="1000",
                Text="Root",
                Timestamp=1_700_000_000,
                media=(MediaAsset(media_id="p1", url="https://example.com/p1.jpg", media_type=MediaType.PHOTO),),
            ),
            TweetSegment(
                ID="1001",
                Text="Child",
                Timestamp=1_700_000_100,
                media=(),
            ),
        ),
    )


def make_translation(
    *,
    status: TranslationStatus = TranslationStatus.READY,
    segments: Iterable[TranslationSegment] | None = None,
) -> TranslationRecord:
    default_segments = (
        TranslationSegment(tweet_id="1000", text="Translated root", has_media=True),
        TranslationSegment(tweet_id="1001", text="Translated child", has_media=False),
    )
    return TranslationRecord(
        author_handle="handle",
        root_tweet_id="1000",
        segments=tuple(segments or default_segments),
        titles=("Sample Title",),
        status=status,
    )


def test_publish_service_build_plan_and_publish(monkeypatch):
    tweet_repo = InMemoryTweetRepository()
    translation_repo = InMemoryTranslationRepository()
    tweet_repo.upsert(make_thread())
    translation_repo.upsert(make_translation())

    monkeypatch.setenv("TWITTER_CONSUMER_KEYS", "ck")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRETS", "cs")
    monkeypatch.setenv("TWITTER_ACCESS_TOKENS", "at")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRETS", "ats")
    monkeypatch.setenv("TWITTER_PUBLISH_PROFILES", "default")
    monkeypatch.setenv("TWITTER_FINAL_MESSAGES", "Closing message")

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    client = FakePublisherClient(posts=[])

    service = PublisherService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        client_factory=lambda profile: client,
    )

    plan = service.build_plan("1000", title_index=1)
    assert plan.items[0].text.startswith("[Sample Title]")
    assert plan.closing_message == "Closing message"

    report = service.publish("1000", title_index=1)
    assert isinstance(report, PublishReport)
    assert len(client.posts) == 3  # two segments + closing
    assert client.posts[0]["media"] == ("https://example.com/p1.jpg",)
    assert client.posts[1]["reply_to"] == "posted-1"
    assert client.posts[2]["reply_to"] == "posted-2"

    stored_translation = translation_repo.get("1000")
    assert stored_translation is not None
    assert stored_translation.status is TranslationStatus.PUBLISHED


def test_publish_service_dry_run(monkeypatch):
    tweet_repo = InMemoryTweetRepository()
    translation_repo = InMemoryTranslationRepository()
    tweet_repo.upsert(make_thread())
    translation_repo.upsert(make_translation())

    monkeypatch.setenv("TWITTER_CONSUMER_KEYS", "ck")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRETS", "cs")
    monkeypatch.setenv("TWITTER_ACCESS_TOKENS", "at")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRETS", "ats")
    monkeypatch.setenv("TWITTER_PUBLISH_PROFILES", "default")
    monkeypatch.setenv("TWITTER_FINAL_MESSAGES", "Closing message")

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    client = FakePublisherClient(posts=[])
    service = PublisherService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        client_factory=lambda profile: client,
    )

    report = service.publish("1000", title_index=1, dry_run=True)
    assert isinstance(report, PublishReport)
    assert len(client.posts) == 0

    stored_translation = translation_repo.get("1000")
    assert stored_translation is not None
    assert stored_translation.status is TranslationStatus.READY


def test_publish_service_prevents_duplicate_publish(monkeypatch):
    tweet_repo = InMemoryTweetRepository()
    translation_repo = InMemoryTranslationRepository()
    tweet_repo.upsert(make_thread())
    translation_repo.upsert(make_translation(status=TranslationStatus.PUBLISHED))

    monkeypatch.setenv("TWITTER_CONSUMER_KEYS", "ck")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRETS", "cs")
    monkeypatch.setenv("TWITTER_ACCESS_TOKENS", "at")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRETS", "ats")
    monkeypatch.setenv("TWITTER_PUBLISH_PROFILES", "default")
    monkeypatch.setenv("TWITTER_FINAL_MESSAGES", "Closing message")

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    client = FakePublisherClient(posts=[])
    service = PublisherService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        client_factory=lambda profile: client,
    )

    with pytest.raises(ValueError):
        service.publish("1000", title_index=1)

    assert len(client.posts) == 0


def test_publish_service_force_allows_republish(monkeypatch):
    tweet_repo = InMemoryTweetRepository()
    translation_repo = InMemoryTranslationRepository()
    tweet_repo.upsert(make_thread())
    translation_repo.upsert(make_translation(status=TranslationStatus.PUBLISHED))

    monkeypatch.setenv("TWITTER_CONSUMER_KEYS", "ck")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRETS", "cs")
    monkeypatch.setenv("TWITTER_ACCESS_TOKENS", "at")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRETS", "ats")
    monkeypatch.setenv("TWITTER_PUBLISH_PROFILES", "default")
    monkeypatch.setenv("TWITTER_FINAL_MESSAGES", "Closing message")

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    client = FakePublisherClient(posts=[])
    service = PublisherService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        client_factory=lambda profile: client,
    )

    report = service.publish("1000", title_index=1, force=True)
    assert len(client.posts) == 3
    assert isinstance(report, PublishReport)

    stored_translation = translation_repo.get("1000")
    assert stored_translation is not None
    assert stored_translation.status is TranslationStatus.PUBLISHED


def test_build_plan_requires_complete_translation(monkeypatch):
    tweet_repo = InMemoryTweetRepository()
    translation_repo = InMemoryTranslationRepository()
    tweet_repo.upsert(make_thread())
    translation_repo.upsert(
        make_translation(
            segments=(
                TranslationSegment(tweet_id="1000", text="Translated root", has_media=True),
            )
        )
    )

    monkeypatch.setenv("TWITTER_CONSUMER_KEYS", "ck")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRETS", "cs")
    monkeypatch.setenv("TWITTER_ACCESS_TOKENS", "at")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRETS", "ats")
    monkeypatch.setenv("TWITTER_PUBLISH_PROFILES", "default")
    monkeypatch.setenv("TWITTER_FINAL_MESSAGES", "Closing message")

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    client = FakePublisherClient(posts=[])
    service = PublisherService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        client_factory=lambda profile: client,
    )

    with pytest.raises(ValueError):
        service.build_plan("1000")


def test_build_plan_rejects_unknown_translation_segments(monkeypatch):
    tweet_repo = InMemoryTweetRepository()
    translation_repo = InMemoryTranslationRepository()
    tweet_repo.upsert(make_thread())
    translation_repo.upsert(
        make_translation(
            segments=(
                TranslationSegment(tweet_id="1000", text="Translated root", has_media=True),
                TranslationSegment(tweet_id="9999", text="Unexpected", has_media=False),
            )
        )
    )

    monkeypatch.setenv("TWITTER_CONSUMER_KEYS", "ck")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRETS", "cs")
    monkeypatch.setenv("TWITTER_ACCESS_TOKENS", "at")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRETS", "ats")
    monkeypatch.setenv("TWITTER_PUBLISH_PROFILES", "default")
    monkeypatch.setenv("TWITTER_FINAL_MESSAGES", "Closing message")

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    client = FakePublisherClient(posts=[])
    service = PublisherService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        client_factory=lambda profile: client,
    )

    with pytest.raises(ValueError):
        service.build_plan("1000")

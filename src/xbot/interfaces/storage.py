"""Storage layer interfaces for tweets, translations, and tasks."""

from __future__ import annotations

from typing import Iterable, Protocol, Sequence

from xbot.models import ScheduledJob, TranslationRecord, TweetThread


class TweetRepository(Protocol):
    """Persistence operations for tweet threads."""

    def upsert(self, thread: TweetThread) -> None:
        ...

    def get(self, root_tweet_id: str) -> TweetThread | None:
        ...

    def list_all(self) -> Sequence[TweetThread]:
        ...

    def list_for_handle(self, author_handle: str) -> Sequence[TweetThread]:
        ...

    def delete(self, root_tweet_id: str) -> None:
        ...


class TranslationRepository(Protocol):
    """Persistence operations for translated threads."""

    def upsert(self, record: TranslationRecord) -> None:
        ...

    def get(self, root_tweet_id: str) -> TranslationRecord | None:
        ...

    def list_all(self) -> Sequence[TranslationRecord]:
        ...

    def list_for_handle(self, author_handle: str) -> Sequence[TranslationRecord]:
        ...

    def delete(self, root_tweet_id: str) -> None:
        ...


class JobRepository(Protocol):
    """Persistence operations for scheduled jobs."""

    def enqueue(self, job: ScheduledJob) -> None:
        ...

    def get(self, job_id: str) -> ScheduledJob | None:
        ...

    def list_pending(self) -> Sequence[ScheduledJob]:
        ...

    def update(self, job: ScheduledJob) -> None:
        ...


def bulk_upsert(repository: TweetRepository, threads: Iterable[TweetThread]) -> None:
    """Persist a collection of threads using the provided repository."""

    for thread in threads:
        repository.upsert(thread)


__all__ = [
    "TweetRepository",
    "TranslationRepository",
    "JobRepository",
    "bulk_upsert",
]

"""Service layer for translating tweet threads."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from xbot.config.settings import Settings, get_settings
from xbot.interfaces.storage import TranslationRepository, TweetRepository
from xbot.interfaces.translation_provider import TranslationProvider
from xbot.models import TranslationRecord, TranslationSegment, TranslationStatus, TweetThread


@dataclass(frozen=True)
class TranslationResult:
    record: TranslationRecord
    created: bool


class TranslationService:
    """Coordinates translation requests and persistence."""

    def __init__(
        self,
        tweet_repository: TweetRepository,
        translation_repository: TranslationRepository,
        provider: TranslationProvider,
        settings: Settings | None = None,
        title_count: int = 5,
    ) -> None:
        self._tweet_repository = tweet_repository
        self._translation_repository = translation_repository
        self._provider = provider
        self._settings = settings or get_settings()
        self._title_count = title_count

    def translate_thread(
        self,
        tweet_id: str,
        *,
        include_titles: bool | None = None,
        force: bool = False,
    ) -> TranslationResult:
        thread = self._get_thread(tweet_id)
        existing = self._translation_repository.get(thread.root_id)
        if existing and not force:
            return TranslationResult(record=existing, created=False)

        translations = list(self._provider.translate_segments(thread))
        if len(translations) != len(thread.tweets):
            raise ValueError("Translation length mismatch; aborting")

        segments: list[TranslationSegment] = []
        for segment, translated in zip(thread.tweets, translations):
            segments.append(
                TranslationSegment(
                    tweet_id=segment.tweet_id,
                    text=translated,
                    has_media=bool(segment.media),
                )
            )

        titles: Sequence[str] = ()
        if self._should_include_titles(include_titles):
            titles = self._provider.generate_titles(
                thread, translations, self._title_count
            )

        record = TranslationRecord(
            author_handle=thread.author_handle,
            root_tweet_id=thread.root_id,
            segments=tuple(segments),
            titles=tuple(titles),
            status=TranslationStatus.READY,
        )

        self._translation_repository.upsert(record)
        return TranslationResult(record=record, created=True)

    def translate_pending(
        self, *, include_titles: bool | None = None, force: bool = False
    ) -> Sequence[TranslationResult]:
        results: list[TranslationResult] = []
        for thread in self._tweet_repository.list_all():
            if not force and self._translation_repository.get(thread.root_id):
                continue
            results.append(
                self.translate_thread(
                    thread.root_id, include_titles=include_titles, force=force
                )
            )
        return results

    def manual_translation_prompt(self, tweet_id: str) -> str:
        thread = self._get_thread(tweet_id)
        return self._provider.build_manual_prompt(thread)

    def manual_title_prompt(self, tweet_id: str, count: int | None = None) -> str:
        thread = self._get_thread(tweet_id)
        count = count or self._title_count
        translations = [segment.text for segment in thread.tweets]
        summary = "\n".join(translations)
        return (
            f"Create {count} alternate titles for the following thread."
            " Return one title per line.\n"
            f"Thread:\n{summary}"
        )

    def _get_thread(self, tweet_id: str) -> TweetThread:
        thread = self._tweet_repository.get(tweet_id)
        if thread is None:
            raise ValueError(f"Thread {tweet_id} not found in repository")
        return thread

    def _should_include_titles(self, include_titles: bool | None) -> bool:
        if include_titles is not None:
            return include_titles
        return self._settings.features.enable_translation_titles


__all__ = ["TranslationService", "TranslationResult"]

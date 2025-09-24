"""Service layer for publishing translated threads to Twitter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence

from twitter_bot.config.settings import Settings, get_settings
from twitter_bot.interfaces.storage import TranslationRepository, TweetRepository
from twitter_bot.interfaces.twitter_client import PublisherClient
from twitter_bot.models import (
    TranslationRecord,
    TranslationSegment,
    TranslationStatus,
    TweetThread,
)
from twitter_bot.utils.twitter import ensure_within_limit


@dataclass(frozen=True)
class PublishingProfile:
    name: str
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str
    closing_message: str | None


@dataclass(frozen=True)
class PublishItem:
    text: str
    media_urls: Sequence[str]
    source_tweet_id: str


@dataclass(frozen=True)
class PublishPlan:
    root_tweet_id: str
    items: Sequence[PublishItem]
    closing_message: str | None


@dataclass(frozen=True)
class PublishReport:
    root_tweet_id: str
    posted_tweet_ids: Sequence[str]
    plan: PublishPlan


class PublisherService:
    """Coordinates publishing of translated threads."""

    def __init__(
        self,
        tweet_repository: TweetRepository,
        translation_repository: TranslationRepository,
        client_factory: Callable[[PublishingProfile], PublisherClient],
        settings: Settings | None = None,
    ) -> None:
        self._tweet_repository = tweet_repository
        self._translation_repository = translation_repository
        self._client_factory = client_factory
        self._settings = settings or get_settings()

    def build_plan(
        self,
        tweet_id: str,
        *,
        profile_name: str = "default",
        title_index: int | None = None,
        include_closing: bool = True,
    ) -> PublishPlan:
        thread = self._get_thread(tweet_id)
        translation = self._get_translation(tweet_id)
        profile = self._resolve_profile(profile_name)
        return self._create_plan(
            thread,
            translation,
            profile,
            title_index=title_index,
            include_closing=include_closing,
        )

    def publish(
        self,
        tweet_id: str,
        *,
        profile_name: str = "default",
        title_index: int | None = None,
        include_closing: bool = True,
        dry_run: bool = False,
        force: bool = False,
    ) -> PublishReport:
        thread = self._get_thread(tweet_id)
        translation = self._get_translation(tweet_id)
        if translation.status is TranslationStatus.PUBLISHED and not force:
            raise ValueError(
                f"Translation {tweet_id} has already been published; use force=True to repost"
            )
        profile = self._resolve_profile(profile_name)
        plan = self._create_plan(
            thread,
            translation,
            profile,
            title_index=title_index,
            include_closing=include_closing,
        )
        if dry_run:
            return PublishReport(root_tweet_id=tweet_id, posted_tweet_ids=(), plan=plan)

        client = self._client_factory(profile)

        posted_ids: List[str] = []
        reply_to: str | None = None
        for item in plan.items:
            posted_id = client.post_tweet(
                text=item.text,
                media_urls=item.media_urls,
                in_reply_to=reply_to,
            )
            posted_ids.append(posted_id)
            reply_to = posted_id

        if plan.closing_message:
            closing_id = client.post_tweet(
                text=plan.closing_message,
                media_urls=(),
                in_reply_to=reply_to,
            )
            posted_ids.append(closing_id)

        updated_translation = translation.mark_published()
        self._translation_repository.upsert(updated_translation)

        return PublishReport(
            root_tweet_id=tweet_id,
            posted_tweet_ids=tuple(posted_ids),
            plan=plan,
        )

    def _select_title(self, translation: TranslationRecord, title_index: int) -> str:
        if not translation.titles:
            raise ValueError("No titles available for this translation")
        index = title_index - 1
        if index < 0 or index >= len(translation.titles):
            raise ValueError("Title index is out of range")
        return translation.titles[index]

    def _resolve_profile(self, profile_name: str) -> PublishingProfile:
        publisher = self._settings.publisher
        profiles = list(publisher.profiles)
        if profile_name not in profiles:
            raise ValueError(f"Profile {profile_name} is not defined")
        idx = profiles.index(profile_name)
        try:
            return PublishingProfile(
                name=profile_name,
                consumer_key=publisher.consumer_keys[idx],
                consumer_secret=publisher.consumer_secrets[idx],
                access_token=publisher.access_tokens[idx],
                access_token_secret=publisher.access_token_secrets[idx],
                closing_message=publisher.final_messages[idx]
                if idx < len(publisher.final_messages)
                else None,
            )
        except IndexError as exc:  # pragma: no cover - configuration errors
            raise ValueError("Publisher credentials are misconfigured") from exc

    def _get_thread(self, tweet_id: str) -> TweetThread:
        thread = self._tweet_repository.get(tweet_id)
        if thread is None:
            raise ValueError(f"Thread {tweet_id} not found")
        return thread

    def _get_translation(self, tweet_id: str) -> TranslationRecord:
        translation = self._translation_repository.get(tweet_id)
        if translation is None:
            raise ValueError(f"Translation {tweet_id} not found")
        return translation

    def _create_plan(
        self,
        thread: TweetThread,
        translation: TranslationRecord,
        profile: PublishingProfile,
        *,
        title_index: int | None,
        include_closing: bool,
    ) -> PublishPlan:
        translation_map: Dict[str, TranslationSegment] = {}
        for segment in translation.segments:
            if segment.tweet_id in translation_map:
                raise ValueError(
                    f"Duplicate translation detected for tweet {segment.tweet_id}"
                )
            translation_map[segment.tweet_id] = segment

        missing = [
            segment.tweet_id for segment in thread.tweets if segment.tweet_id not in translation_map
        ]
        if missing:
            missing_ids = ", ".join(missing)
            raise ValueError(f"Missing translations for tweets: {missing_ids}")

        thread_ids = set(thread.tweet_ids)
        extras = [
            segment_id for segment_id in translation_map if segment_id not in thread_ids
        ]
        if extras:
            extra_ids = ", ".join(extras)
            raise ValueError(f"Translations reference unknown tweets: {extra_ids}")

        items: List[PublishItem] = []
        for idx, segment in enumerate(thread.tweets):
            translation_segment = translation_map[segment.tweet_id]
            text = translation_segment.text
            if idx == 0 and title_index is not None:
                title = self._select_title(translation, title_index)
                text = f"[{title}]\n\n{text}"
            ensure_within_limit(text)
            media_urls = tuple(asset.url for asset in segment.media)
            items.append(
                PublishItem(
                    text=text,
                    media_urls=media_urls,
                    source_tweet_id=segment.tweet_id,
                )
            )

        closing_message = None
        if include_closing and profile.closing_message:
            ensure_within_limit(profile.closing_message)
            closing_message = profile.closing_message

        return PublishPlan(
            root_tweet_id=thread.root_id,
            items=tuple(items),
            closing_message=closing_message,
        )


__all__ = [
    "PublisherService",
    "PublishingProfile",
    "PublishPlan",
    "PublishItem",
    "PublishReport",
]

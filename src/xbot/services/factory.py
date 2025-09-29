"""Service factory helpers centralising common wiring."""

from __future__ import annotations

from typing import Any

from xbot.config.settings import Settings
from xbot.infra.clients.openai_client import OpenAITranslationClient
from xbot.infra.clients.x_publisher import TweepyPublisherClient
from xbot.infra.clients.x_scraper import TweetyScraperClient
from xbot.infra.repositories.json_store import (
    JSONJobRepository,
    JSONTranslationRepository,
    JSONTweetRepository,
)
from xbot.models import ScheduledJob
from xbot.services.publishing import PublisherService
from xbot.services.scheduling import SchedulerService
from xbot.services.scraping import ScraperService
from xbot.services.translation import TranslationService


def tweet_repository(settings: Settings) -> JSONTweetRepository:
    return JSONTweetRepository(settings.storage_root / "tweets.json")


def translation_repository(settings: Settings) -> JSONTranslationRepository:
    return JSONTranslationRepository(settings.storage_root / "translations.json")


def job_repository(settings: Settings) -> JSONJobRepository:
    return JSONJobRepository(settings.storage_root / "jobs.json")


def build_scraper_service(settings: Settings) -> ScraperService:
    client = TweetyScraperClient(
        usernames=settings.scraper.usernames,
        password=settings.scraper.password,
        session_dir=settings.scraper.session_dir,
    )
    return ScraperService(
        repository=tweet_repository(settings),
        client=client,
        settings=settings,
    )


def build_translation_service(settings: Settings) -> TranslationService:
    provider = OpenAITranslationClient(
        api_key=settings.openai.api_key,
        translation_model=settings.openai.translation_model,
        summary_model=settings.openai.summary_model,
        timeout=settings.openai.request_timeout,
    )
    return TranslationService(
        tweet_repository=tweet_repository(settings),
        translation_repository=translation_repository(settings),
        provider=provider,
        settings=settings,
    )


def build_publisher_service(settings: Settings) -> PublisherService:
    def factory(profile: Any) -> TweepyPublisherClient:
        return TweepyPublisherClient(
            consumer_key=profile.consumer_key,
            consumer_secret=profile.consumer_secret,
            access_token=profile.access_token,
            access_token_secret=profile.access_token_secret,
        )

    return PublisherService(
        tweet_repository=tweet_repository(settings),
        translation_repository=translation_repository(settings),
        client_factory=factory,
        settings=settings,
    )


def build_scheduler_service(settings: Settings) -> SchedulerService:
    scheduler = SchedulerService(repository=job_repository(settings), settings=settings)

    def scraper_lookup() -> ScraperService:
        return build_scraper_service(settings)

    def translation_lookup() -> TranslationService:
        return build_translation_service(settings)

    def publisher_lookup() -> PublisherService:
        return build_publisher_service(settings)

    def handle_scrape(job: ScheduledJob) -> None:
        handle = str(job.payload.get("handle", ""))
        limit = int(job.payload.get("limit", 40))
        scraper_lookup().sync_handle(handle, limit=limit)

    def handle_translate(job: ScheduledJob) -> None:
        tweet_id = str(job.payload.get("tweet_id", ""))
        include_titles = job.payload.get("include_titles")
        force = bool(job.payload.get("force", False))
        translation_lookup().translate_thread(
            tweet_id,
            include_titles=include_titles,
            force=force,
        )

    def handle_publish(job: ScheduledJob) -> None:
        tweet_id = str(job.payload.get("tweet_id", ""))
        profile_name = str(job.payload.get("profile", "default"))
        title_index = job.payload.get("title_index")
        include_closing = bool(job.payload.get("include_closing", True))
        dry_run = bool(job.payload.get("dry_run", False))
        force = bool(job.payload.get("force", False))
        publisher_lookup().publish(
            tweet_id,
            profile_name=profile_name,
            title_index=title_index,
            include_closing=include_closing,
            dry_run=dry_run,
            force=force,
        )

    scheduler.register_handler("scrape-handle", handle_scrape)
    scheduler.register_handler("translate-thread", handle_translate)
    scheduler.register_handler("publish-thread", handle_publish)
    return scheduler


__all__ = [
    "build_scraper_service",
    "build_translation_service",
    "build_publisher_service",
    "build_scheduler_service",
    "tweet_repository",
    "translation_repository",
    "job_repository",
]

"""Run the Telegram operator bot."""

from __future__ import annotations

import typer

from twitter_bot.config.settings import get_settings
from twitter_bot.infra.telegram.bot import TelegramOperatorBot
from twitter_bot.infra.clients.openai_client import OpenAITranslationClient
from twitter_bot.infra.clients.twitter_publisher import TweepyPublisherClient
from twitter_bot.infra.clients.twitter_scraper import TweetyScraperClient
from twitter_bot.infra.repositories.json_store import (
    JSONTranslationRepository,
    JSONTweetRepository,
)
from twitter_bot.services.operator import CommandContext
from twitter_bot.services.publishing import PublisherService
from twitter_bot.services.scraping import ScraperService
from twitter_bot.services.translation import TranslationService

app = typer.Typer(help="Launch and manage the Telegram operator bot.")


@app.command("run")
def run_bot() -> None:
    settings = get_settings()
    tweet_repo = JSONTweetRepository(settings.storage_root / "tweets.json")
    translation_repo = JSONTranslationRepository(settings.storage_root / "translations.json")

    scraper = ScraperService(
        repository=tweet_repo,
        client=TweetyScraperClient(
            usernames=settings.scraper.usernames,
            password=settings.scraper.password,
            session_dir=settings.scraper.session_dir,
        ),
        settings=settings,
    )

    translator = TranslationService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        provider=OpenAITranslationClient(
            api_key=settings.openai.api_key,
            translation_model=settings.openai.translation_model,
            summary_model=settings.openai.summary_model,
            timeout=settings.openai.request_timeout,
        ),
        settings=settings,
    )

    def publisher_factory(profile):
        return TweepyPublisherClient(
            consumer_key=profile.consumer_key,
            consumer_secret=profile.consumer_secret,
            access_token=profile.access_token,
            access_token_secret=profile.access_token_secret,
        )

    publisher = PublisherService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        client_factory=publisher_factory,
        settings=settings,
    )

    context = CommandContext(
        scraper=scraper,
        translator=translator,
        publisher=publisher,
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
    )

    bot = TelegramOperatorBot(settings=settings, context=context)
    bot.run_blocking()


__all__ = ["app", "run_bot"]

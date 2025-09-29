"""Translation workflow commands."""

from __future__ import annotations

import typer

from xbot.config.settings import get_settings
from xbot.infra.clients.openai_client import OpenAITranslationClient
from xbot.infra.repositories.json_store import (
    JSONTranslationRepository,
    JSONTweetRepository,
)
from xbot.services.translation import TranslationService

app = typer.Typer(help="Translate stored threads using OpenAI.")


def _build_service() -> TranslationService:
    settings = get_settings()
    tweet_repo = JSONTweetRepository(settings.storage_root / "tweets.json")
    translation_repo = JSONTranslationRepository(settings.storage_root / "translations.json")
    provider = OpenAITranslationClient(
        api_key=settings.openai.api_key,
        translation_model=settings.openai.translation_model,
        summary_model=settings.openai.summary_model,
        timeout=settings.openai.request_timeout,
    )
    return TranslationService(
        tweet_repository=tweet_repo,
        translation_repository=translation_repo,
        provider=provider,
        settings=settings,
    )


@app.command("tweet")
def translate_tweet(
    tweet_id: str,
    force: bool = typer.Option(False, help="Re-generate even if a translation exists."),
    include_titles: bool | None = typer.Option(
        None, help="Override default title generation behaviour."
    ),
) -> None:
    """Translate a single tweet thread stored in the repository."""

    service = _build_service()
    result = service.translate_thread(
        tweet_id, include_titles=include_titles, force=force
    )
    status = "created" if result.created else "skipped"
    typer.echo(f"Translation {status} for {tweet_id}.")


@app.command("pending")
def translate_pending(
    force: bool = typer.Option(False, help="Re-translate all threads."),
    include_titles: bool | None = typer.Option(
        None, help="Override default title generation behaviour."
    ),
) -> None:
    """Translate all threads without an existing translation."""

    service = _build_service()
    results = service.translate_pending(include_titles=include_titles, force=force)
    created = sum(1 for result in results if result.created)
    typer.echo(f"Processed {len(results)} threads; created {created} translations.")


@app.command("manual-prompt")
def manual_prompt(tweet_id: str) -> None:
    """Print the manual translation prompt for the given tweet ID."""

    service = _build_service()
    typer.echo(service.manual_translation_prompt(tweet_id))


__all__ = ["app", "translate_tweet", "translate_pending", "manual_prompt"]

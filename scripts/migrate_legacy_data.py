"""Utilities to migrate legacy JSON exports into the new storage layout."""

from __future__ import annotations

from pathlib import Path

import typer

from twitter_bot.config.settings import get_settings
from twitter_bot.infra.repositories.json_store import (
    JSONTranslationRepository,
    JSONTweetRepository,
)
from twitter_bot.utils.legacy import load_legacy_threads, load_legacy_translations

app = typer.Typer(help="Migration helpers for legacy data exports.")


@app.command("from-legacy")
def migrate_from_legacy(
    source: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, readable=True),
    tweets_filename: str = typer.Option("complete_tweets.json", help="Legacy tweets file name."),
    translations_filename: str = typer.Option(
        "translated_tweets_sorted.json", help="Legacy translations file name."
    ),
    include_translations: bool = typer.Option(
        True, help="Import translated threads if the legacy file is present."
    ),
) -> None:
    """Migrate legacy JSON exports located under *source* into the current storage layout."""

    settings = get_settings()
    tweet_repo = JSONTweetRepository(settings.storage_root / "tweets.json")
    translation_repo = JSONTranslationRepository(settings.storage_root / "translations.json")

    tweets_path = source / tweets_filename
    translations_path = source / translations_filename

    imported_threads = 0
    for _, thread in load_legacy_threads(tweets_path):
        tweet_repo.upsert(thread)
        imported_threads += 1

    typer.echo(f"Imported {imported_threads} threads from {tweets_path}.")

    if include_translations and translations_path.exists():
        imported_translations = 0
        for _, translation in load_legacy_translations(translations_path):
            translation_repo.upsert(translation)
            imported_translations += 1
        typer.echo(f"Imported {imported_translations} translations from {translations_path}.")
    elif include_translations:
        typer.echo(f"Translations file not found at {translations_path}; skipped import.")


if __name__ == "__main__":
    app()

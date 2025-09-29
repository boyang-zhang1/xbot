"""Operator review commands for inspecting stored data."""

from __future__ import annotations

from pathlib import Path

import typer

from xbot.config.settings import get_settings
from xbot.models import TranslationStatus
from xbot.services.factory import (
    translation_repository,
    tweet_repository,
)

app = typer.Typer(help="Inspect stored tweets and translations.")


@app.command("translations")
def list_translations(
    status: TranslationStatus | None = typer.Option(
        None, help="Filter by translation status."
    )
) -> None:
    settings = get_settings()
    repo = translation_repository(settings)
    records = repo.list_all()
    for record in records:
        if status and record.status is not status:
            continue
        typer.echo(
            f"{record.root_tweet_id} | {record.author_handle} | {record.status.value}"
        )
    typer.echo(f"Total: {len(records)} records")


@app.command("show")
def show_translation(tweet_id: str) -> None:
    settings = get_settings()
    repo = translation_repository(settings)
    record = repo.get(tweet_id)
    if record is None:
        raise typer.BadParameter(f"No translation found for {tweet_id}")
    typer.echo(f"Author: {record.author_handle}\nStatus: {record.status.value}\n")
    for idx, segment in enumerate(record.segments, start=1):
        typer.echo(f"Segment {idx} ({segment.tweet_id}):\n{segment.text}\n")
    if record.titles:
        typer.echo("Titles:")
        for title in record.titles:
            typer.echo(f"- {title}")


@app.command("export")
def export_translation(tweet_id: str, output: Path) -> None:
    settings = get_settings()
    repo = translation_repository(settings)
    record = repo.get(tweet_id)
    if record is None:
        raise typer.BadParameter(f"No translation found for {tweet_id}")
    payload = {
        "tweet_id": record.root_tweet_id,
        "author": record.author_handle,
        "status": record.status.value,
        "titles": list(record.titles),
        "segments": [segment.text for segment in record.segments],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n\n".join(payload["segments"]),
        encoding="utf-8",
    )
    typer.echo(f"Exported translation to {output}")


@app.command("threads")
def list_threads(author: str | None = typer.Option(None, help="Filter by author handle.")) -> None:
    settings = get_settings()
    repo = tweet_repository(settings)
    threads = repo.list_all()
    for thread in threads:
        if author and thread.author_handle.lower() != author.lower():
            continue
        typer.echo(
            f"{thread.root_id} | {thread.author_handle} | {len(thread.tweets)} tweets"
        )
    typer.echo(f"Total threads: {len(threads)}")


__all__ = ["app", "list_translations", "show_translation", "export_translation", "list_threads"]

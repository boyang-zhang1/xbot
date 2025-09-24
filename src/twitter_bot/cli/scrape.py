"""Scraping-related CLI commands."""

from __future__ import annotations

import typer

from twitter_bot.config.settings import get_settings
from twitter_bot.infra.clients.twitter_scraper import TweetyScraperClient
from twitter_bot.infra.repositories.json_store import JSONTweetRepository
from twitter_bot.services.scraping import ScraperService

app = typer.Typer(help="Fetch recent threads from watched accounts.")


def _build_service() -> ScraperService:
    settings = get_settings()
    repository = JSONTweetRepository(settings.storage_root / "tweets.json")
    client = TweetyScraperClient(
        usernames=settings.scraper.usernames,
        password=settings.scraper.password,
        session_dir=settings.scraper.session_dir,
    )
    return ScraperService(repository=repository, client=client, settings=settings)


@app.command("handle")
def scrape_handle(handle: str, limit: int = typer.Option(40, help="Maximum threads to fetch.")) -> None:
    """Fetch and persist threads for a specific handle."""

    service = _build_service()
    result = service.sync_handle(handle, limit=limit)
    typer.echo(f"Fetched {result.fetched} threads for {handle}; stored {result.stored}.")


@app.command("all")
def scrape_all(limit: int = typer.Option(40, help="Maximum threads per handle.")) -> None:
    """Fetch threads for all configured handles."""

    service = _build_service()
    summary = service.sync_all(limit=limit)
    for result in summary.results:
        typer.echo(f"{result.handle}: fetched {result.fetched}, stored {result.stored}")
    typer.echo(
        f"Total fetched {summary.total_fetched}; total stored {summary.total_stored}."
    )


__all__ = ["app", "scrape_all", "scrape_handle"]

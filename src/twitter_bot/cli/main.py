"""Primary CLI entrypoint for the twitter_bot toolkit."""

from __future__ import annotations

import typer

from twitter_bot.cli import migrate, scrape

app = typer.Typer(help="Twitter bot automation toolkit.")
app.add_typer(migrate.app, name="migrate")
app.add_typer(scrape.app, name="scrape")


__all__ = ["app"]

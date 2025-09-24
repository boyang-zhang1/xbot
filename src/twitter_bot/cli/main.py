"""Primary CLI entrypoint for the twitter_bot toolkit."""

from __future__ import annotations

import typer

from twitter_bot.cli import migrate, publish, scrape, translate

app = typer.Typer(help="Twitter bot automation toolkit.")
app.add_typer(migrate.app, name="migrate")
app.add_typer(scrape.app, name="scrape")
app.add_typer(translate.app, name="translate")
app.add_typer(publish.app, name="publish")


__all__ = ["app"]

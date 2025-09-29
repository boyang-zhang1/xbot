"""Primary CLI entrypoint for the xbot toolkit."""

from __future__ import annotations

import typer

from xbot.cli import migrate, publish, scrape, telegram, translate

app = typer.Typer(help="X bot automation toolkit.")
app.add_typer(migrate.app, name="migrate")
app.add_typer(scrape.app, name="scrape")
app.add_typer(translate.app, name="translate")
app.add_typer(publish.app, name="publish")
app.add_typer(telegram.app, name="telegram")


__all__ = ["app"]

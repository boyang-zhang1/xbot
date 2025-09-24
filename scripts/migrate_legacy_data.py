"""Entry point for migrating legacy data via `python -m` or scripts."""

from twitter_bot.cli.migrate import app

if __name__ == "__main__":
    app()

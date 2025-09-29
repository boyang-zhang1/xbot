"""Command processing logic for the Telegram operator bot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from xbot.services.publishing import PublisherService
from xbot.services.scraping import ScraperService
from xbot.services.translation import TranslationService

if TYPE_CHECKING:  # pragma: no cover
    from xbot.services.scheduling import SchedulerService


@dataclass
class CommandContext:
    scraper: ScraperService
    translator: TranslationService
    publisher: PublisherService
    scheduler: SchedulerService | None = None
    tweet_repository: object | None = None
    translation_repository: object | None = None
    job_repository: object | None = None


class CommandProcessor:
    """Parse operator commands and invoke the corresponding services."""

    def __init__(self, context: CommandContext) -> None:
        self._context = context

    def handle(self, command: str) -> str:
        tokens = command.strip().split()
        if not tokens:
            return self._help()

        head, *args = tokens
        if head in {"/start", "/help"}:
            return self._help()
        if head == "/scrape":
            return self._scrape(args)
        if head == "/translate":
            return self._translate(args)
        if head == "/publish":
            return self._publish(args)
        if head == "/queue" and args:
            return self._queue(args)
        if head == "/status":
            return self._status()
        return f"Unknown command '{head}'. Try /help"

    def _help(self) -> str:
        return (
            "Available commands:\n"
            "/scrape <handle> [limit] - Fetch latest threads.\n"
            "/translate <tweet_id> [--force] [--no-titles] - Translate thread.\n"
            "/publish <tweet_id> [--profile default] [--dry-run] [--force] - Publish translation.\n"
            "/queue <scrape|translate|publish> ... - Enqueue jobs for later execution.\n"
            "/status - Summaries of stored tweets/translations/jobs."
        )

    def _scrape(self, args: list[str]) -> str:
        if not args:
            return "Usage: /scrape <handle> [limit]"
        handle = args[0]
        limit = int(args[1]) if len(args) > 1 else 40
        result = self._context.scraper.sync_handle(handle, limit=limit)
        return f"Scraped {result.fetched} threads for {handle}; stored {result.stored}."

    def _translate(self, args: list[str]) -> str:
        if not args:
            return "Usage: /translate <tweet_id> [--force] [--no-titles]"
        tweet_id = args[0]
        force = "--force" in args
        include_titles: bool | None = None
        if "--no-titles" in args:
            include_titles = False
        result = self._context.translator.translate_thread(
            tweet_id, force=force, include_titles=include_titles
        )
        state = "created" if result.created else "existing"
        return f"Translation {state} for {tweet_id}."

    def _publish(self, args: list[str]) -> str:
        if not args:
            return "Usage: /publish <tweet_id> [--profile default] [--dry-run] [--force]"
        tweet_id = args[0]
        profile = self._extract_option(args, "--profile", default="default")
        profile_name = profile or "default"
        dry_run = "--dry-run" in args
        force = "--force" in args
        title_index = self._extract_option(args, "--title", default=None)
        title_index_value = int(title_index) if title_index is not None else None
        report = self._context.publisher.publish(
            tweet_id,
            profile_name=profile_name,
            title_index=title_index_value,
            dry_run=dry_run,
            force=force,
        )
        if dry_run:
            return f"Dry run: {len(report.plan.items)} tweets would be posted."
        return f"Published {len(report.posted_tweet_ids)} tweets for {tweet_id}."

    def _queue(self, args: list[str]) -> str:
        if not self._context.scheduler:
            return "Scheduler is not configured."
        if not args:
            return "Usage: /queue <scrape|translate|publish> ..."
        action, *rest = args
        payload: dict[str, object]
        if action == "scrape":
            if not rest:
                return "Usage: /queue scrape <handle> [limit]"
            payload = {"handle": rest[0]}
            if len(rest) > 1:
                payload["limit"] = int(rest[1])
            job = self._context.scheduler.enqueue("scrape-handle", payload=payload)
        elif action == "translate":
            if not rest:
                return "Usage: /queue translate <tweet_id>"
            payload = {"tweet_id": rest[0]}
            job = self._context.scheduler.enqueue("translate-thread", payload=payload)
        elif action == "publish":
            if not rest:
                return "Usage: /queue publish <tweet_id>"
            payload = {"tweet_id": rest[0]}
            job = self._context.scheduler.enqueue("publish-thread", payload=payload)
        else:
            return "Unknown queue action; use scrape, translate, or publish."
        return f"Queued job {job.job_id} ({action})."

    def _status(self) -> str:
        tweets = 0
        if self._context.tweet_repository:
            tweets = len(self._context.tweet_repository.list_all())  # type: ignore[attr-defined]
        translations = 0
        if self._context.translation_repository:
            translations = len(self._context.translation_repository.list_all())  # type: ignore[attr-defined]
        jobs = 0
        if self._context.job_repository:
            jobs = len(self._context.job_repository.list_pending())  # type: ignore[attr-defined]
        return (
            f"Stored tweets: {tweets}\n"
            f"Stored translations: {translations}\n"
            f"Queued jobs: {jobs}"
        )

    @staticmethod
    def _extract_option(args: list[str], flag: str, default: str | None) -> str | None:
        if flag not in args:
            return default
        index = args.index(flag)
        if index + 1 >= len(args):
            return default
        return args[index + 1]


__all__ = ["CommandProcessor", "CommandContext"]

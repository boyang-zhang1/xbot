"""Scheduler commands for background orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import typer

from xbot.config.settings import get_settings
from xbot.services.factory import build_scheduler_service
from xbot.services.scheduling import SchedulerService

app = typer.Typer(help="Manage scheduled jobs and run pending tasks.")


def _build_scheduler() -> SchedulerService:
    settings = get_settings()
    return build_scheduler_service(settings)


@app.command("run")
def run_pending() -> None:
    """Execute all due jobs."""

    scheduler = _build_scheduler()
    results = scheduler.run_pending(now=datetime.now(tz=UTC))
    for result in results:
        status = "success" if result.success else f"failed: {result.error}"
        typer.echo(f"Job {result.job.job_id} ({result.job.name}) -> {status}")
    if not results:
        typer.echo("No jobs ready to run.")


def _schedule_job(name: str, payload: dict[str, Any], run_at: datetime | None) -> None:
    scheduler = _build_scheduler()
    job = scheduler.enqueue(name, payload=payload, run_at=run_at)
    typer.echo(f"Enqueued job {job.job_id} for {job.run_at.isoformat()}")


@app.command("enqueue-scrape")
def enqueue_scrape(
    handle: str,
    limit: int = typer.Option(40, help="Maximum number of threads to fetch."),
    run_at: datetime | None = typer.Option(None, help="ISO timestamp for execution."),
) -> None:
    payload = {"handle": handle, "limit": limit}
    parsed = _parse_datetime(run_at)
    _schedule_job("scrape-handle", payload, parsed)


@app.command("enqueue-translate")
def enqueue_translate(
    tweet_id: str,
    force: bool = typer.Option(False, help="Re-translate even if a record exists."),
    include_titles: bool | None = typer.Option(None, help="Override default title policy."),
    run_at: datetime | None = typer.Option(None, help="ISO timestamp for execution."),
) -> None:
    payload = {"tweet_id": tweet_id, "force": force}
    if include_titles is not None:
        payload["include_titles"] = include_titles
    _schedule_job("translate-thread", payload, _parse_datetime(run_at))


@app.command("enqueue-publish")
def enqueue_publish(
    tweet_id: str,
    profile: str = typer.Option("default", help="Publishing profile."),
    title_index: int | None = typer.Option(None, help="Optional title index."),
    include_closing: bool = typer.Option(True, help="Include closing message."),
    dry_run: bool = typer.Option(False, help="Dry run without posting."),
    force: bool = typer.Option(False, help="Force re-publish if already sent."),
    run_at: datetime | None = typer.Option(None, help="ISO timestamp for execution."),
) -> None:
    payload: dict[str, Any] = {
        "tweet_id": tweet_id,
        "profile": profile,
        "include_closing": include_closing,
        "dry_run": dry_run,
        "force": force,
    }
    if title_index is not None:
        payload["title_index"] = title_index
    _schedule_job("publish-thread", payload, _parse_datetime(run_at))


def _parse_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    raise typer.BadParameter("Expected ISO 8601 datetime")


__all__ = [
    "app",
    "run_pending",
    "enqueue_scrape",
    "enqueue_translate",
    "enqueue_publish",
]

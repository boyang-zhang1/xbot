"""Publishing commands."""

from __future__ import annotations

import typer

from xbot.config.settings import get_settings
from xbot.services.factory import build_publisher_service
from xbot.services.publishing import PublisherService

app = typer.Typer(help="Publish translated threads to X.")


def _build_service() -> PublisherService:
    settings = get_settings()
    return build_publisher_service(settings)


@app.command("tweet")
def publish_tweet(
    tweet_id: str,
    profile: str = typer.Option("default", help="Publishing profile name."),
    title_index: int | None = typer.Option(None, help="Optional 1-based title index."),
    include_closing: bool = typer.Option(True, help="Append profile closing message."),
    dry_run: bool = typer.Option(False, help="Build the plan without posting."),
    force: bool = typer.Option(False, help="Allow republishing already published translations."),
) -> None:
    """Publish a translated thread."""

    service = _build_service()
    report = service.publish(
        tweet_id,
        profile_name=profile,
        title_index=title_index,
        include_closing=include_closing,
        dry_run=dry_run,
        force=force,
    )
    if dry_run:
        typer.echo("Dry run - no tweets posted.")
    else:
        typer.echo(f"Posted {len(report.posted_tweet_ids)} tweets: {', '.join(report.posted_tweet_ids)}")


@app.command("plan")
def show_plan(
    tweet_id: str,
    profile: str = typer.Option("default", help="Publishing profile name."),
    title_index: int | None = typer.Option(None, help="Optional 1-based title index."),
    include_closing: bool = typer.Option(True, help="Append profile closing message."),
) -> None:
    """Display the publish plan for inspection."""

    service = _build_service()
    plan = service.build_plan(
        tweet_id,
        profile_name=profile,
        title_index=title_index,
        include_closing=include_closing,
    )
    typer.echo(f"Root tweet: {plan.root_tweet_id}")
    for idx, item in enumerate(plan.items, start=1):
        typer.echo(f"\nSegment {idx} ({item.source_tweet_id}):\n{item.text}")
        if item.media_urls:
            typer.echo(f"Media: {', '.join(item.media_urls)}")
    if plan.closing_message:
        typer.echo(f"\nClosing:\n{plan.closing_message}")


__all__ = ["app", "publish_tweet", "show_plan"]

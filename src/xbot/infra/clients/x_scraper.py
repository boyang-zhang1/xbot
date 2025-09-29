"""Tweety-based scraper client implementation for X."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from xbot.interfaces.x_client import ScraperClient
from xbot.models import MediaType, TweetThread

try:  # pragma: no cover - optional dependency
    from tweety import Twitter
except ImportError:  # pragma: no cover - optional dependency
    Twitter = cast(Any, None)


class TweetyScraperClient(ScraperClient):
    """Scraper client that leverages the tweety library to collect posts."""

    def __init__(
        self,
        usernames: Sequence[str],
        password: str,
        session_dir: Path,
        pages_per_request: int = 5,
    ) -> None:
        if not usernames:
            raise ValueError("At least one username is required for scraping")
        if Twitter is None:
            raise RuntimeError("tweety library is not installed; install it to enable scraping")

        self._usernames = list(usernames)
        self._password = password
        self._session_dir = session_dir
        self._pages_per_request = max(1, pages_per_request)
        self._sessions: dict[str, Twitter] = {}
        self._cursor = 0

    def fetch_threads(self, author_handle: str, limit: int = 40) -> Sequence[TweetThread]:
        errors: list[Exception] = []
        for _ in range(len(self._usernames)):
            username = self._select_username()
            client = self._get_session(username)
            try:
                tweets = self._fetch_with_client(client, author_handle, limit)
                if tweets:
                    return tweets
            except Exception as exc:  # pragma: no cover - network failures
                errors.append(exc)
                self._invalidate_session(username)
                continue
        if errors:
            raise RuntimeError(f"Failed to scrape {author_handle}: {errors[-1]}")
        return []

    def _fetch_with_client(self, client: Any, author_handle: str, limit: int) -> list[TweetThread]:
        raw = client.get_tweets(username=author_handle, pages=self._pages_per_request)
        tweets = []
        for item in getattr(raw, "tweets", []):
            thread = self._convert_item(author_handle, item)
            if thread:
                tweets.append(thread)
            if len(tweets) >= limit:
                break
        return tweets

    def _select_username(self) -> str:
        username = self._usernames[self._cursor]
        self._cursor = (self._cursor + 1) % len(self._usernames)
        return username

    def _session_path(self, username: str) -> Path:
        return self._session_dir / f"x_session_{username}.json"

    def _get_session(self, username: str) -> Any:  # pragma: no cover - network
        if username in self._sessions:
            return self._sessions[username]

        session_path = self._session_path(username)
        profile_name = session_path.stem
        if session_path.exists():
            client = Twitter(profile_name)
            client.connect()
        else:
            client = Twitter(profile_name)
            client.sign_in(username, self._password)
            session_path.parent.mkdir(parents=True, exist_ok=True)
            client.save_session(session_path)
        self._sessions[username] = client
        return client

    def _invalidate_session(self, username: str) -> None:
        self._sessions.pop(username, None)

    def _convert_item(self, author_handle: str, item: object) -> TweetThread | None:
        payload = _build_legacy_payload(item)
        if payload is None:
            return None
        return TweetThread.from_legacy(author_handle, payload)


def _build_legacy_payload(item: Any) -> dict[str, Any] | None:
    """Transform tweety tweet objects into the legacy payload expected by TweetThread."""

    tweet_id = getattr(item, "id", None)
    text = getattr(item, "text", None)
    timestamp = getattr(item, "timestamp", 0)
    if not tweet_id or text is None:
        return None

    def serialise_media(collection: Any, media_type: MediaType) -> list[dict[str, Any]]:
        serialised: list[dict[str, Any]] = []
        for media in collection or []:
            media_id = getattr(media, "id", "")
            url = getattr(media, "url", "")
            preview = getattr(media, "preview", None)
            serialised.append({"ID": media_id, "URL": url, "Preview": preview, "media_type": media_type.value})
        return serialised

    def to_timestamp(value: Any) -> float:
        if hasattr(value, "timestamp"):
            return float(value.timestamp())
        return float(value)

    root_payload = {
        "ID": tweet_id,
        "Text": text,
        "Timestamp": to_timestamp(timestamp),
        "Photos": serialise_media(getattr(item, "photos", []), MediaType.PHOTO),
        "Videos": serialise_media(getattr(item, "videos", []), MediaType.VIDEO),
        "Thread": [],
    }

    thread_items = getattr(item, "thread", []) or []
    for child in thread_items:
        child_timestamp = getattr(child, "timestamp", 0)
        payload = {
            "ID": getattr(child, "id", ""),
            "Text": getattr(child, "text", ""),
            "Timestamp": to_timestamp(child_timestamp),
            "Photos": serialise_media(getattr(child, "photos", []), MediaType.PHOTO),
            "Videos": serialise_media(getattr(child, "videos", []), MediaType.VIDEO),
            "Thread": [],
        }
        root_payload["Thread"].append(payload)

    return root_payload


__all__ = ["TweetyScraperClient"]

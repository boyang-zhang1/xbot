"""X publishing client based on Tweepy and the v2 tweets endpoint."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

try:  # pragma: no cover - optional dependency
    import httpx
except ImportError:  # pragma: no cover - fallback for offline environments
    httpx = cast(Any, None)

try:  # pragma: no cover - optional dependency
    import tweepy
except ImportError:  # pragma: no cover - raise when attempting to use
    tweepy = cast(Any, None)

try:  # pragma: no cover - optional dependency
    from requests_oauthlib import OAuth1Session
except ImportError:  # pragma: no cover
    OAuth1Session = cast(Any, None)

from xbot.interfaces.x_client import PublisherClient


class TweepyPublisherClient(PublisherClient):
    """Publish posts using Tweepy for media uploads and OAuth1 for posting."""

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
    ) -> None:
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._access_token = access_token
        self._access_token_secret = access_token_secret
        if OAuth1Session is None:
            raise RuntimeError("requests-oauthlib is not installed")
        self._oauth = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )
        if tweepy is None:
            raise RuntimeError("tweepy is not installed")
        auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
        self._api = tweepy.API(auth)

    def post_tweet(
        self,
        text: str,
        media_urls: Sequence[str] | None = None,
        in_reply_to: str | None = None,
    ) -> str:
        media_ids = self._upload_media(media_urls or [])
        payload: dict[str, Any] = {"text": text}
        if in_reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": in_reply_to}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}

        response = self._oauth.post("https://api.twitter.com/2/tweets", json=payload)
        response.raise_for_status()
        data = cast(dict[str, Any], response.json())
        result = cast(dict[str, Any], data.get("data", {}))
        return str(result.get("id", ""))

    def _upload_media(self, media_urls: Sequence[str]) -> Sequence[str]:
        media_ids: list[str] = []
        for url in media_urls:
            path = self._download_to_temp(url)
            try:
                media = self._api.media_upload(filename=str(path))
                media_ids.append(media.media_id_string)
            finally:
                if path.exists():
                    path.unlink()
        return tuple(media_ids)

    def _download_to_temp(self, url: str) -> Path:
        if httpx is None:  # pragma: no cover - executed when dependency missing
            raise RuntimeError("httpx is not installed")
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        descriptor, tmp_path = tempfile.mkstemp(suffix=Path(url).suffix or ".bin")
        with os.fdopen(descriptor, "wb") as fh:
            fh.write(response.content)
        return Path(tmp_path)


__all__ = ["TweepyPublisherClient"]

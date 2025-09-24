"""JSON-backed repository implementations."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, List

from twitter_bot.interfaces.storage import TranslationRepository, TweetRepository
from twitter_bot.models import TranslationRecord, TweetThread
from twitter_bot.utils.io import read_json_file, write_json_atomic


class _BaseJSONRepository:
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._lock = threading.Lock()
        self._cache: Dict[str, dict] | None = None

    def _load(self) -> Dict[str, dict]:
        if self._cache is None:
            self._cache = read_json_file(self._storage_path, default={})
        return self._cache

    def _persist(self) -> None:
        if self._cache is None:
            return
        write_json_atomic(self._storage_path, self._cache)


class JSONTweetRepository(_BaseJSONRepository, TweetRepository):
    """Store threads in a JSON file keyed by the root tweet ID."""

    def upsert(self, thread: TweetThread) -> None:
        with self._lock:
            data = self._load()
            data[thread.root_id] = thread.model_dump(mode="json")
            self._persist()

    def get(self, root_tweet_id: str) -> TweetThread | None:
        with self._lock:
            data = self._load()
            payload = data.get(root_tweet_id)
            if payload is None:
                return None
            return TweetThread.model_validate(payload)

    def list_all(self) -> List[TweetThread]:
        with self._lock:
            data = self._load()
            return [TweetThread.model_validate(item) for item in data.values()]

    def list_for_handle(self, author_handle: str) -> List[TweetThread]:
        return [
            thread
            for thread in self.list_all()
            if thread.author_handle.lower() == author_handle.lower()
        ]

    def delete(self, root_tweet_id: str) -> None:
        with self._lock:
            data = self._load()
            if root_tweet_id in data:
                del data[root_tweet_id]
                self._persist()


class JSONTranslationRepository(_BaseJSONRepository, TranslationRepository):
    """Store translation records in a JSON file keyed by the root tweet ID."""

    def upsert(self, record: TranslationRecord) -> None:
        with self._lock:
            data = self._load()
            data[record.root_tweet_id] = record.model_dump(mode="json")
            self._persist()

    def get(self, root_tweet_id: str) -> TranslationRecord | None:
        with self._lock:
            data = self._load()
            payload = data.get(root_tweet_id)
            if payload is None:
                return None
            return TranslationRecord.model_validate(payload)

    def list_all(self) -> List[TranslationRecord]:
        with self._lock:
            data = self._load()
            return [TranslationRecord.model_validate(item) for item in data.values()]

    def list_for_handle(self, author_handle: str) -> List[TranslationRecord]:
        return [
            record
            for record in self.list_all()
            if record.author_handle.lower() == author_handle.lower()
        ]

    def delete(self, root_tweet_id: str) -> None:
        with self._lock:
            data = self._load()
            if root_tweet_id in data:
                del data[root_tweet_id]
                self._persist()


__all__ = ["JSONTweetRepository", "JSONTranslationRepository"]

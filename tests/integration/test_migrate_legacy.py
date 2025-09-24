import json
from pathlib import Path

import importlib

from twitter_bot.config import settings as settings_module
from twitter_bot.infra.repositories.json_store import (
    JSONTranslationRepository,
    JSONTweetRepository,
)
from twitter_bot.models import TranslationRecord, TweetThread


def write_legacy_payload(tmp_path: Path) -> Path:
    source = tmp_path / "legacy"
    source.mkdir()

    tweets_payload = {
        "sample_handle": [
            {
                "ID": "500",
                "Text": "Root",
                "Timestamp": 1_700_000_000,
                "Photos": [],
                "Videos": [],
                "Thread": [
                    {
                        "ID": "501",
                        "Text": "Child",
                        "Timestamp": 1_700_000_100,
                        "Photos": [],
                        "Videos": [],
                        "Thread": [],
                    }
                ],
            }
        ]
    }

    translations_payload = {
        "sample_handle": [
            {
                "ID": "500",
                "Text": "Root translated",
                "Timestamp": 1_700_000_000,
                "Photos": [],
                "Videos": [],
                "Thread": [
                    {
                        "ID": "501",
                        "Text": "Child translated",
                        "Timestamp": 1_700_000_100,
                        "Photos": [],
                        "Videos": [],
                        "Thread": [],
                    }
                ],
                "Titles": ["Title 1", "Title 2"],
            }
        ]
    }

    (source / "complete_tweets.json").write_text(json.dumps(tweets_payload))
    (source / "translated_tweets_sorted.json").write_text(json.dumps(translations_payload))
    return source


def test_migrate_from_legacy(tmp_path, monkeypatch):
    source = write_legacy_payload(tmp_path)

    data_dir = tmp_path / "data"
    log_dir = tmp_path / "logs"

    monkeypatch.setenv("APP_DATA_DIR", str(data_dir))
    monkeypatch.setenv("APP_LOG_DIR", str(log_dir))

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]

    module = importlib.import_module("scripts.migrate_legacy_data")
    module.migrate_from_legacy.callback(source=source)  # type: ignore[attr-defined]

    tweet_repo = JSONTweetRepository(data_dir / "tweets.json")
    translation_repo = JSONTranslationRepository(data_dir / "translations.json")

    thread = tweet_repo.get("500")
    translation = translation_repo.get("500")

    assert isinstance(thread, TweetThread)
    assert isinstance(translation, TranslationRecord)
    assert translation.titles == ("Title 1", "Title 2")



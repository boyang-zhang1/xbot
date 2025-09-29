from pathlib import Path

from xbot.infra.repositories.json_store import (
    JSONTranslationRepository,
    JSONTweetRepository,
)
from xbot.models import TranslationRecord, TranslationSegment, TweetSegment, TweetThread


def build_thread(root_id: str = "200") -> TweetThread:
    return TweetThread(
        author_handle="handle",
        tweets=(
            TweetSegment(ID=root_id, Text="Root", Timestamp=1_700_000_000, media=[]),
            TweetSegment(ID=f"{root_id}1", Text="Child", Timestamp=1_700_000_100, media=[]),
        ),
    )


def build_translation(root_id: str = "200") -> TranslationRecord:
    return TranslationRecord(
        author_handle="handle",
        root_tweet_id=root_id,
        segments=(
            TranslationSegment(tweet_id=root_id, text="Root translated"),
            TranslationSegment(tweet_id=f"{root_id}1", text="Child translated"),
        ),
        titles=("Title A", "Title B"),
    )


def test_tweet_repository_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "tweets.json"
    repo = JSONTweetRepository(path)

    thread = build_thread("300")
    repo.upsert(thread)

    loaded = repo.get("300")
    assert loaded is not None
    assert loaded.root_id == "300"
    assert len(repo.list_all()) == 1

    repo.delete("300")
    assert repo.get("300") is None


def test_translation_repository_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "translations.json"
    repo = JSONTranslationRepository(path)

    record = build_translation("400")
    repo.upsert(record)

    loaded = repo.get("400")
    assert loaded is not None
    assert loaded.root_tweet_id == "400"
    assert len(repo.list_for_handle("handle")) == 1

    repo.delete("400")
    assert repo.get("400") is None


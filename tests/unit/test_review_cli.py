from pathlib import Path

from typer.testing import CliRunner
from xbot.cli import review
from xbot.config import settings as settings_module
from xbot.models import (
    TranslationRecord,
    TranslationSegment,
    TranslationStatus,
    TweetSegment,
    TweetThread,
)
from xbot.services.factory import translation_repository, tweet_repository

runner = CliRunner()


def setup_repositories(tmp_path: Path) -> None:
    thread = TweetThread(
        author_handle="alice",
        tweets=(
            TweetSegment(ID="1", Text="Hello", Timestamp=1_700_000_000),
            TweetSegment(ID="2", Text="World", Timestamp=1_700_000_100),
        ),
    )
    translation = TranslationRecord(
        author_handle="alice",
        root_tweet_id="1",
        segments=(
            TranslationSegment(tweet_id="1", text="你好", has_media=False),
            TranslationSegment(tweet_id="2", text="世界", has_media=False),
        ),
        titles=("标题",),
        status=TranslationStatus.READY,
    )

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]
    settings = settings_module.get_settings()

    tweet_repo = tweet_repository(settings)
    translation_repo = translation_repository(settings)

    tweet_repo.upsert(thread)
    translation_repo.upsert(translation)


def test_review_commands(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("APP_LOG_DIR", str(tmp_path / "logs"))
    setup_repositories(tmp_path)

    result = runner.invoke(review.app, ["translations"])
    assert result.exit_code == 0
    assert "alice" in result.stdout

    result = runner.invoke(review.app, ["show", "1"])
    assert result.exit_code == 0
    assert "你好" in result.stdout

    output_path = tmp_path / "export.txt"
    result = runner.invoke(review.app, ["export", "1", str(output_path)])
    assert result.exit_code == 0
    assert output_path.exists()

    result = runner.invoke(review.app, ["threads"])
    assert result.exit_code == 0
    assert "alice" in result.stdout

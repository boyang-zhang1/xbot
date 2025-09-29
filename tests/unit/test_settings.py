from xbot.config import settings as settings_module


def test_settings_parses_environment(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    log_dir = tmp_path / "logs"
    session_dir = tmp_path / "sessions"

    monkeypatch.setenv("APP_DATA_DIR", str(data_dir))
    monkeypatch.setenv("APP_LOG_DIR", str(log_dir))

    monkeypatch.setenv("TWITTER_SCRAPER_HANDLES", "alpha,beta")
    monkeypatch.setenv("TWITTER_SCRAPER_USERNAMES", "scraper_a, scraper_b")
    monkeypatch.setenv("TWITTER_SCRAPER_PASSWORD", "secret")
    monkeypatch.setenv("TWITTER_SCRAPER_SESSION_DIR", str(session_dir))
    monkeypatch.setenv("TWITTER_SCRAPER_INTERVAL_SECONDS", "123")

    monkeypatch.setenv("TWITTER_CONSUMER_KEYS", "key1,key2")
    monkeypatch.setenv("TWITTER_CONSUMER_SECRETS", "secret1,secret2")
    monkeypatch.setenv("TWITTER_ACCESS_TOKENS", "token1,token2")
    monkeypatch.setenv("TWITTER_ACCESS_TOKEN_SECRETS", "toksec1,toksec2")
    monkeypatch.setenv("TWITTER_PUBLISH_PROFILES", "primary,backup")
    monkeypatch.setenv("TWITTER_FINAL_MESSAGES", "one,two")

    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_TRANSLATION_MODEL", "translator")
    monkeypatch.setenv("OPENAI_SUMMARY_MODEL", "summarizer")
    monkeypatch.setenv("OPENAI_REQUEST_TIMEOUT", "42")

    monkeypatch.setenv("TELEGRAM_API_ID", "1234")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("TELEGRAM_OPERATOR_CHAT_ID", "-99")

    monkeypatch.setenv("ENABLE_TRANSLATION_TITLES", "false")

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]
    settings = settings_module.get_settings()

    assert settings.storage_root == data_dir
    assert settings.log_root == log_dir
    assert settings.scraper.handles == ("alpha", "beta")
    assert settings.scraper.usernames == ("scraper_a", "scraper_b")
    assert settings.scraper.password == "secret"
    assert settings.scraper.interval_seconds == 123
    assert settings.scraper.session_dir == session_dir

    assert settings.publisher.consumer_keys == ("key1", "key2")
    assert settings.publisher.consumer_secrets == ("secret1", "secret2")
    assert settings.publisher.access_tokens == ("token1", "token2")
    assert settings.publisher.access_token_secrets == ("toksec1", "toksec2")
    assert settings.publisher.profiles == ("primary", "backup")
    assert settings.publisher.final_messages == ("one", "two")

    assert settings.openai.api_key == "openai-key"
    assert settings.openai.translation_model == "translator"
    assert settings.openai.summary_model == "summarizer"
    assert settings.openai.request_timeout == 42

    assert settings.telegram.api_id == 1234
    assert settings.telegram.api_hash == "hash"
    assert settings.telegram.bot_token == "bot-token"
    assert settings.telegram.operator_chat_id == -99

    assert settings.features.enable_translation_titles is False

    assert data_dir.exists()
    assert log_dir.exists()
    assert session_dir.exists()



def test_settings_cached(monkeypatch):
    monkeypatch.delenv("APP_DATA_DIR", raising=False)
    monkeypatch.delenv("APP_LOG_DIR", raising=False)

    settings_module.get_settings.cache_clear()  # type: ignore[attr-defined]
    first = settings_module.get_settings()
    second = settings_module.get_settings()
    assert first is second

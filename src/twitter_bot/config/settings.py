"""Application configuration powered by Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable, Tuple

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str | Iterable[str] | None) -> Tuple[str, ...]:
    """Normalise comma-separated values into a tuple of strings."""
    if value is None:
        return tuple()
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
    else:
        parts = [str(part).strip() for part in value if str(part).strip()]
    return tuple(parts)


class PathsSettings(BaseSettings):
    """Filesystem paths used by the application."""

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", env_file_encoding="utf-8")

    data_dir: Path = Field(default=Path("var/data"))
    log_dir: Path = Field(default=Path("var/logs"))

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


class ScraperSettings(BaseSettings):
    """Settings for the Twitter scraping workflow."""

    model_config = SettingsConfigDict(env_prefix="TWITTER_SCRAPER_", env_file=".env", env_file_encoding="utf-8")

    handles: Tuple[str, ...] = Field(default=tuple(), alias="handles")
    usernames: Tuple[str, ...] = Field(default=tuple(), alias="usernames")
    password: str = Field(default="", alias="password")
    session_dir: Path = Field(default=Path("var/twitter_sessions"), alias="session_dir")
    interval_seconds: int = Field(default=7200, alias="interval_seconds")

    @field_validator("handles", "usernames", mode="before")
    @classmethod
    def _split_values(cls, value: str | Iterable[str] | None) -> Tuple[str, ...]:
        return _split_csv(value)

    def ensure_directories(self) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)


class PublisherProfileSettings(BaseSettings):
    """OAuth credentials for a single publisher profile."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str


class PublisherSettings(BaseSettings):
    """Settings for publishing translated content to Twitter."""

    model_config = SettingsConfigDict(env_prefix="TWITTER_", env_file=".env", env_file_encoding="utf-8")

    consumer_keys: Tuple[str, ...] = Field(default=tuple(), alias="CONSUMER_KEYS")
    consumer_secrets: Tuple[str, ...] = Field(default=tuple(), alias="CONSUMER_SECRETS")
    access_tokens: Tuple[str, ...] = Field(default=tuple(), alias="ACCESS_TOKENS")
    access_token_secrets: Tuple[str, ...] = Field(default=tuple(), alias="ACCESS_TOKEN_SECRETS")
    profiles: Tuple[str, ...] = Field(default=("default",), alias="PUBLISH_PROFILES")
    final_messages: Tuple[str, ...] = Field(default=tuple(), alias="FINAL_MESSAGES")

    @field_validator("consumer_keys", "consumer_secrets", "access_tokens", "access_token_secrets", "profiles", "final_messages", mode="before")
    @classmethod
    def _split_values(cls, value: str | Iterable[str] | None) -> Tuple[str, ...]:
        return _split_csv(value)


class OpenAISettings(BaseSettings):
    """Configuration for OpenAI-powered translation and summarisation."""

    model_config = SettingsConfigDict(env_prefix="OPENAI_", env_file=".env", env_file_encoding="utf-8")

    api_key: str = Field(default="")
    translation_model: str = Field(default="gpt-4o-mini")
    summary_model: str = Field(default="gpt-4o")
    request_timeout: int = Field(default=60)


class TelegramSettings(BaseSettings):
    """Credentials for the Telegram operator bot."""

    model_config = SettingsConfigDict(env_prefix="TELEGRAM_", env_file=".env", env_file_encoding="utf-8")

    api_id: int = Field(default=0)
    api_hash: str = Field(default="")
    bot_token: str = Field(default="")
    operator_chat_id: int = Field(default=0)


class FeatureToggleSettings(BaseSettings):
    """Optional feature toggles used across the application."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    enable_translation_titles: bool = Field(default=True, alias="ENABLE_TRANSLATION_TITLES")


class Settings:
    """Aggregated application settings with helpers for runtime setup."""

    def __init__(self) -> None:
        self.paths = PathsSettings()
        self.scraper = ScraperSettings()
        self.publisher = PublisherSettings()
        self.openai = OpenAISettings()
        self.telegram = TelegramSettings()
        self.features = FeatureToggleSettings()

        self.paths.ensure_directories()
        self.scraper.ensure_directories()

    @property
    def storage_root(self) -> Path:
        return self.paths.data_dir

    @property
    def log_root(self) -> Path:
        return self.paths.log_dir


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()


__all__ = [
    "Settings",
    "get_settings",
    "OpenAISettings",
    "PublisherSettings",
    "ScraperSettings",
    "TelegramSettings",
    "PathsSettings",
    "FeatureToggleSettings",
]

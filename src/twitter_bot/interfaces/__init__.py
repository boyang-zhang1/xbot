"""Interface exports for the twitter_bot package."""

from .storage import TranslationRepository, TweetRepository, bulk_upsert
from .twitter_client import PublisherClient, ScraperClient
from .translation_provider import TranslationProvider

__all__ = [
    "TweetRepository",
    "TranslationRepository",
    "bulk_upsert",
    "ScraperClient",
    "PublisherClient",
    "TranslationProvider",
]

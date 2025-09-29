"""Protocols for translation backends."""

from __future__ import annotations

from typing import Protocol, Sequence

from xbot.models import TweetThread


class TranslationProvider(Protocol):
    """Interface for translating tweet threads and generating titles."""

    def translate_segments(self, thread: TweetThread) -> Sequence[str]:
        ...

    def generate_titles(self, thread: TweetThread, translated_segments: Sequence[str], count: int) -> Sequence[str]:
        ...

    def build_manual_prompt(self, thread: TweetThread) -> str:
        ...


__all__ = ["TranslationProvider"]

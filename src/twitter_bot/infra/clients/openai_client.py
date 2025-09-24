"""OpenAI-powered translation provider."""

from __future__ import annotations

from typing import Sequence

from openai import OpenAI
from openai.types.chat import ChatCompletion

from twitter_bot.interfaces.translation_provider import TranslationProvider
from twitter_bot.models import TweetThread

TRANSLATION_SYSTEM_PROMPT = (
    "You specialise in translating knowledge-dense Twitter threads into Simplified Chinese while"
    " preserving nuance, keeping URLs intact, and retaining the '-|' ordering markers for each"
    " tweet."
)

TITLE_SYSTEM_PROMPT = (
    "You craft concise, high-signal Simplified Chinese titles for translated Twitter threads."
    " Produce catchy phrasing suitable for social media."
)


class OpenAITranslationClient(TranslationProvider):
    """Wrapper around the OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: str,
        translation_model: str,
        summary_model: str,
        timeout: int,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self._client = OpenAI(api_key=api_key, timeout=timeout)
        self._translation_model = translation_model
        self._summary_model = summary_model
        self._timeout = timeout

    def translate_segments(self, thread: TweetThread) -> Sequence[str]:
        content = _thread_to_prompt(thread)
        completion = self._client.chat.completions.create(
            model=self._translation_model,
            messages=[
                {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            timeout=self._timeout,
        )
        return _parse_translation_payload(completion, expected=len(thread.tweets))

    def generate_titles(
        self, thread: TweetThread, translated_segments: Sequence[str], count: int
    ) -> Sequence[str]:
        body = _titles_prompt(thread, translated_segments, count)
        completion = self._client.chat.completions.create(
            model=self._summary_model,
            messages=[
                {"role": "system", "content": TITLE_SYSTEM_PROMPT},
                {"role": "user", "content": body},
            ],
            timeout=self._timeout,
        )
        content = _extract_content(completion)
        titles = [line.strip() for line in content.splitlines() if line.strip()]
        return titles[:count]

    def build_manual_prompt(self, thread: TweetThread) -> str:
        return _thread_to_prompt(thread)


def _thread_to_prompt(thread: TweetThread) -> str:
    lines = ["Please translate each tweet. Keep '-|' prefixes on every line."]
    for segment in thread.tweets:
        lines.append(f"-|{segment.text}")
    return "\n".join(lines)


def _titles_prompt(thread: TweetThread, translated_segments: Sequence[str], count: int) -> str:
    joined = "\n".join(translated_segments)
    return (
        f"Create {count} standalone titles for the following translated thread."
        " Return one title per line.\n"
        f"Thread:\n{joined}"
    )


def _extract_content(completion: ChatCompletion) -> str:
    message = completion.choices[0].message
    return message.content or ""


def _parse_translation_payload(completion: ChatCompletion, expected: int) -> Sequence[str]:
    content = _extract_content(completion)
    parts = [part.strip() for part in content.split("-|") if part.strip()]
    if len(parts) != expected:
        raise ValueError(
            f"Expected {expected} segments from translator, received {len(parts)}"
        )
    return parts


__all__ = ["OpenAITranslationClient"]

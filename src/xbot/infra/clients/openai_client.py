"""OpenAI-powered translation provider."""

from __future__ import annotations

import time
from collections.abc import Sequence

try:  # pragma: no cover - optional dependency
    from openai import APIError, OpenAI
    from openai import RateLimitError as OpenAIRateLimitError
    from openai.types.chat import ChatCompletion
except ImportError:  # pragma: no cover - fallback used in tests/offline
    class APIError(Exception):
        pass

    OpenAIRateLimitError = None

    class OpenAI:  # type: ignore[no-redef]
        def __init__(self, *_, **__):
            raise RuntimeError("openai package is not installed")

    class ChatCompletion:  # minimal stub for typing
        def __init__(self, choices):
            self.choices = choices


class RateLimitError(Exception):
    """Compatibility wrapper mirroring the legacy OpenAI RateLimitError signature."""

    def __init__(self, message: str, request=None, response=None) -> None:
        super().__init__(message)
        self.message = message
        self.request = request
        self.response = response


RATE_LIMIT_EXCEPTIONS: tuple[type[Exception], ...]
if OpenAIRateLimitError is not None:
    RATE_LIMIT_EXCEPTIONS = (RateLimitError, OpenAIRateLimitError)
else:
    RATE_LIMIT_EXCEPTIONS = (RateLimitError,)

from xbot.interfaces.translation_provider import TranslationProvider
from xbot.models import TweetThread

TRANSLATION_SYSTEM_PROMPT = (
    "You specialise in translating knowledge-dense X threads into Simplified Chinese while"
    " preserving nuance, keeping URLs intact, and retaining the '-|' ordering markers for each"
    " post."
)

TITLE_SYSTEM_PROMPT = (
    "You craft concise, high-signal Simplified Chinese titles for translated X threads."
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
        *,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self._client = OpenAI(api_key=api_key, timeout=timeout)
        self._translation_model = translation_model
        self._summary_model = summary_model
        self._timeout = timeout
        self._max_retries = max(1, max_retries)
        self._retry_delay = max(0.5, retry_delay)

    def translate_segments(self, thread: TweetThread) -> Sequence[str]:
        content = _thread_to_prompt(thread)
        completion = self._invoke_chat_completion(
            model=self._translation_model,
            messages=[
                {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        )
        return _parse_translation_payload(completion, expected=len(thread.tweets))

    def generate_titles(
        self, thread: TweetThread, translated_segments: Sequence[str], count: int
    ) -> Sequence[str]:
        body = _titles_prompt(thread, translated_segments, count)
        completion = self._invoke_chat_completion(
            model=self._summary_model,
            messages=[
                {"role": "system", "content": TITLE_SYSTEM_PROMPT},
                {"role": "user", "content": body},
            ],
        )
        content = _extract_content(completion)
        titles = [line.strip() for line in content.splitlines() if line.strip()]
        return titles[:count]

    def build_manual_prompt(self, thread: TweetThread) -> str:
        return _thread_to_prompt(thread)

    def _invoke_chat_completion(self, **payload) -> ChatCompletion:
        delay = self._retry_delay
        for attempt in range(1, self._max_retries + 1):
            try:
                return self._client.chat.completions.create(
                    timeout=self._timeout, **payload
                )
            except RATE_LIMIT_EXCEPTIONS:
                if attempt == self._max_retries:
                    raise
                time.sleep(delay)
                delay *= 2
            except APIError:
                if attempt == self._max_retries:
                    raise
                time.sleep(delay)
        raise RuntimeError("Failed to invoke OpenAI completion")


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

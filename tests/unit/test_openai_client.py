import types

import pytest

from xbot.infra.clients import openai_client
from xbot.infra.clients.openai_client import OpenAITranslationClient
from xbot.models import TweetSegment, TweetThread


class DummyCompletion:
    def __init__(self, content: str) -> None:
        message = types.SimpleNamespace(content=content)
        choice = types.SimpleNamespace(message=message)
        self.choices = [choice]


class DummyChat:
    def __init__(self, responses):
        self._responses = iter(responses)

    def create(self, **_kwargs):
        handler = next(self._responses)
        if isinstance(handler, Exception):
            raise handler
        return handler


class DummyOpenAI:
    def __init__(self, *, translation_responses, title_responses, **_kwargs):
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(
                create=DummyChat(translation_responses + title_responses).create
            )
        )


def make_thread() -> TweetThread:
    return TweetThread(
        author_handle="handle",
        tweets=(
            TweetSegment(ID="1", Text="First", Timestamp=1_700_000_000),
            TweetSegment(ID="2", Text="Second", Timestamp=1_700_000_100),
        ),
    )


def test_openai_client_success(monkeypatch):
    thread = make_thread()

    dummy = DummyOpenAI(
        translation_responses=[DummyCompletion("-|one\n-|two")],
        title_responses=[DummyCompletion("Title A\nTitle B")],
    )
    monkeypatch.setattr(openai_client, "OpenAI", lambda **kwargs: dummy)

    client = OpenAITranslationClient(
        api_key="key",
        translation_model="gpt",
        summary_model="gpt",
        timeout=10,
    )

    segments = client.translate_segments(thread)
    assert segments == ["one", "two"]
    titles = client.generate_titles(thread, segments, 1)
    assert titles == ["Title A"]


def test_openai_client_retries(monkeypatch):
    thread = make_thread()

    rate_error = openai_client.RateLimitError(message="limit", request=None, response=None)
    dummy = DummyOpenAI(
        translation_responses=[rate_error, DummyCompletion("-|one\n-|two")],
        title_responses=[DummyCompletion("Title A")],
    )
    monkeypatch.setattr(openai_client, "OpenAI", lambda **kwargs: dummy)

    client = OpenAITranslationClient(
        api_key="key",
        translation_model="gpt",
        summary_model="gpt",
        timeout=5,
        max_retries=2,
        retry_delay=0.01,
    )

    segments = client.translate_segments(thread)
    assert segments == ["one", "two"]


def test_openai_client_exhausts_retries(monkeypatch):
    thread = make_thread()

    error = openai_client.RateLimitError(message="limit", request=None, response=None)
    dummy = DummyOpenAI(
        translation_responses=[error, error],
        title_responses=[],
    )
    monkeypatch.setattr(openai_client, "OpenAI", lambda **kwargs: dummy)

    client = OpenAITranslationClient(
        api_key="key",
        translation_model="gpt",
        summary_model="gpt",
        timeout=5,
        max_retries=2,
        retry_delay=0.01,
    )

    with pytest.raises(openai_client.RateLimitError):
        client.translate_segments(thread)

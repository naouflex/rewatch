"""Tests for assistant LLM streaming activity events."""

from types import SimpleNamespace

from rewatch.assistant import llm_client


class _FakeStream:
    def __init__(self, events):
        self._events = events

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __iter__(self):
        yield from self._events


def _tool_block_start(index=0, block_id="toolu_1", name="run_query"):
    return SimpleNamespace(
        type="content_block_start",
        index=index,
        content_block=SimpleNamespace(type="tool_use", id=block_id, name=name),
    )


def _tool_args_delta(index=0, partial_json='{"query_id":'):
    return SimpleNamespace(
        type="content_block_delta",
        index=index,
        delta=SimpleNamespace(type="input_json_delta", partial_json=partial_json),
    )


def _text_delta(text="Hello"):
    return SimpleNamespace(
        type="content_block_delta",
        index=0,
        delta=SimpleNamespace(type="text_delta", text=text),
    )


def test_anthropic_stream_emits_tool_activity_during_stream(monkeypatch):
    events = []

    class FakeMessages:
        def stream(self, **_kwargs):
            return _FakeStream(
                [
                    _tool_block_start(),
                    _tool_args_delta(),
                    _tool_args_delta(partial_json=" 15}"),
                ]
            )

    fake_client = SimpleNamespace(messages=FakeMessages())
    monkeypatch.setattr(llm_client, "create_anthropic_client", lambda: fake_client)
    monkeypatch.setattr(llm_client, "anthropic_call_with_retry", lambda operation, **_kwargs: operation())
    monkeypatch.setattr(llm_client, "effective_assistant_provider", lambda: "anthropic")
    monkeypatch.setattr(llm_client, "assistant_max_tokens", lambda: 1024)

    result = llm_client.stream_completion(
        [{"role": "user", "content": "Run query 15"}],
        events.append,
    )

    assert result["tool_calls"] == [{"id": "toolu_1", "name": "run_query", "arguments": '{"query_id": 15}'}]
    assert {"type": "status", "message": "Consulting Claude…"} in events
    assert any(
        event.get("type") == "tool_start" and event.get("tool") == "run_query" for event in events
    )
    assert any(
        event.get("type") == "status" and "arguments" in event.get("message", "") for event in events
    )


def test_anthropic_stream_emits_reply_delta_for_text(monkeypatch):
    events = []

    class FakeMessages:
        def stream(self, **_kwargs):
            return _FakeStream(
                [
                    SimpleNamespace(
                        type="content_block_start",
                        index=0,
                        content_block=SimpleNamespace(type="text", text=""),
                    ),
                    _text_delta("Hi "),
                    _text_delta("there"),
                ]
            )

    fake_client = SimpleNamespace(messages=FakeMessages())
    monkeypatch.setattr(llm_client, "create_anthropic_client", lambda: fake_client)
    monkeypatch.setattr(llm_client, "anthropic_call_with_retry", lambda operation, **_kwargs: operation())
    monkeypatch.setattr(llm_client, "effective_assistant_provider", lambda: "anthropic")
    monkeypatch.setattr(llm_client, "assistant_max_tokens", lambda: 1024)

    result = llm_client.stream_completion(
        [{"role": "user", "content": "Say hi"}],
        events.append,
    )

    assert result["content"] == "Hi there"
    assert any(event.get("type") == "reply_delta" for event in events)
    assert any(
        event.get("type") == "status" and event.get("message") == "Composing reply…" for event in events
    )

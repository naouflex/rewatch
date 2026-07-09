"""Provider-agnostic LLM client for the Rewatch assistant."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from rewatch import settings
from rewatch.assistant.anthropic_retry import call_with_retry as anthropic_call_with_retry
from rewatch.assistant.anthropic_retry import create_anthropic_client
from rewatch.assistant.llm_config import assistant_model, assistant_provider, effective_assistant_provider
from rewatch.assistant.openai_retry import call_with_retry as openai_call_with_retry
from rewatch.assistant.openai_retry import create_openai_client
from rewatch.assistant.tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

ActivityCallback = Callable[[dict[str, Any]], None]


def openai_tools_to_anthropic(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for tool in tools:
        fn = tool.get("function") or {}
        converted.append(
            {
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
            }
        )
    return converted


def split_system_messages(conversation: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    other: list[dict[str, Any]] = []
    for message in conversation:
        if message.get("role") == "system":
            content = message.get("content")
            if content:
                system_parts.append(str(content))
        else:
            other.append(message)
    return "\n\n".join(system_parts), other


def openai_messages_to_anthropic(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI-style chat history to Anthropic Messages API format."""
    converted: list[dict[str, Any]] = []
    index = 0
    while index < len(messages):
        message = messages[index]
        role = message.get("role")

        if role == "user":
            converted.append({"role": "user", "content": message.get("content") or ""})
            index += 1
            continue

        if role == "assistant":
            blocks: list[dict[str, Any]] = []
            content = message.get("content")
            if content:
                blocks.append({"type": "text", "text": content})

            for tool_call in message.get("tool_calls") or []:
                fn = tool_call.get("function") or {}
                raw_args = fn.get("arguments") or "{}"
                try:
                    parsed_args = json.loads(raw_args)
                except json.JSONDecodeError:
                    parsed_args = {}
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tool_call.get("id") or "",
                        "name": fn.get("name") or "",
                        "input": parsed_args,
                    }
                )

            converted.append({"role": "assistant", "content": blocks or ""})
            index += 1

            tool_results: list[dict[str, Any]] = []
            while index < len(messages) and messages[index].get("role") == "tool":
                tool_message = messages[index]
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_message.get("tool_call_id") or "",
                        "content": tool_message.get("content") or "",
                    }
                )
                index += 1
            if tool_results:
                converted.append({"role": "user", "content": tool_results})
            continue

        if role == "tool":
            converted.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": message.get("tool_call_id") or "",
                            "content": message.get("content") or "",
                        }
                    ],
                }
            )
            index += 1
            continue

        index += 1

    return converted


def _emit(on_activity: Optional[ActivityCallback], event: dict[str, Any]) -> None:
    if on_activity:
        on_activity(event)


def _openai_stream_completion(
    conversation: list[dict[str, Any]],
    on_activity: Optional[ActivityCallback],
    *,
    tool_choice: str = "auto",
) -> dict[str, Any]:
    client = create_openai_client()
    kwargs: dict[str, Any] = {
        "model": assistant_model(),
        "messages": conversation,
        "tools": TOOL_DEFINITIONS,
        "tool_choice": tool_choice,
        "stream": True,
    }
    if settings.OPENAI_REASONING_EFFORT:
        kwargs["reasoning_effort"] = settings.OPENAI_REASONING_EFFORT

    emitted_any_delta = False

    def _consume_stream() -> dict[str, Any]:
        nonlocal emitted_any_delta
        emitted_any_delta = False
        content_parts: list[str] = []
        tool_calls: dict[int, dict[str, str]] = {}
        stream = client.chat.completions.create(**kwargs)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue
            if delta.content:
                content_parts.append(delta.content)
                emitted_any_delta = True
                _emit(on_activity, {"type": "reply_delta", "text": delta.content})
            for tc in delta.tool_calls or []:
                entry = tool_calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    entry["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        entry["name"] = tc.function.name
                    if tc.function.arguments:
                        entry["arguments"] += tc.function.arguments
        return {
            "content": "".join(content_parts),
            "tool_calls": [tool_calls[i] for i in sorted(tool_calls)],
        }

    return openai_call_with_retry(
        _consume_stream,
        on_status=on_activity,
        can_retry=lambda: not emitted_any_delta,
        log_label="Assistant OpenAI",
    )


def _anthropic_stream_completion(
    conversation: list[dict[str, Any]],
    on_activity: Optional[ActivityCallback],
    *,
    tool_choice: str = "auto",
) -> dict[str, Any]:
    client = create_anthropic_client()
    system_content, messages = split_system_messages(conversation)
    anthropic_messages = openai_messages_to_anthropic(messages)

    kwargs: dict[str, Any] = {
        "model": assistant_model(),
        "max_tokens": settings.ASSISTANT_MAX_TOKENS,
        "messages": anthropic_messages,
    }
    if system_content:
        kwargs["system"] = system_content
    if tool_choice != "none":
        kwargs["tools"] = openai_tools_to_anthropic(TOOL_DEFINITIONS)
        kwargs["tool_choice"] = {"type": "auto"}

    emitted_any_delta = False

    def _consume_stream() -> dict[str, Any]:
        nonlocal emitted_any_delta
        emitted_any_delta = False
        content_parts: list[str] = []
        tool_calls: dict[int, dict[str, str]] = {}

        with client.messages.stream(**kwargs) as stream:
            for event in stream:
                event_type = getattr(event, "type", None)
                if event_type == "content_block_start":
                    block = getattr(event, "content_block", None)
                    if block is not None and getattr(block, "type", None) == "tool_use":
                        tool_calls[event.index] = {
                            "id": block.id,
                            "name": block.name,
                            "arguments": "",
                        }
                elif event_type == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    if delta is None:
                        continue
                    delta_type = getattr(delta, "type", None)
                    if delta_type == "text_delta":
                        text = getattr(delta, "text", "") or ""
                        if text:
                            content_parts.append(text)
                            emitted_any_delta = True
                            _emit(on_activity, {"type": "reply_delta", "text": text})
                    elif delta_type == "input_json_delta":
                        entry = tool_calls.get(event.index)
                        if entry is not None:
                            entry["arguments"] += getattr(delta, "partial_json", "") or ""

        return {
            "content": "".join(content_parts),
            "tool_calls": [tool_calls[i] for i in sorted(tool_calls)],
        }

    return anthropic_call_with_retry(
        _consume_stream,
        on_status=on_activity,
        can_retry=lambda: not emitted_any_delta,
        log_label="Assistant Anthropic",
    )


def stream_completion(
    conversation: list[dict[str, Any]],
    on_activity: Optional[ActivityCallback],
    *,
    tool_choice: str = "auto",
) -> dict[str, Any]:
    """Stream one completion from the configured assistant provider."""
    if effective_assistant_provider() == "anthropic":
        return _anthropic_stream_completion(conversation, on_activity, tool_choice=tool_choice)
    return _openai_stream_completion(conversation, on_activity, tool_choice=tool_choice)


def complete_text(
    messages: list[dict[str, Any]],
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    log_label: str = "LLM completion",
) -> str:
    """Non-streaming text completion for query generation and similar tasks."""
    resolved_model = model or assistant_model()

    if effective_assistant_provider() == "anthropic":
        client = create_anthropic_client()
        system_content, other_messages = split_system_messages(messages)
        anthropic_messages = openai_messages_to_anthropic(other_messages)
        kwargs: dict[str, Any] = {
            "model": resolved_model,
            "max_tokens": settings.ASSISTANT_MAX_TOKENS,
            "messages": anthropic_messages,
        }
        if system_content:
            kwargs["system"] = system_content

        def _generate() -> str:
            response = client.messages.create(**kwargs)
            parts: list[str] = []
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    parts.append(block.text)
            return "".join(parts)

        return anthropic_call_with_retry(_generate, log_label=log_label)

    client = create_openai_client()
    kwargs = {
        "model": resolved_model,
        "messages": messages,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if settings.OPENAI_REASONING_EFFORT:
        kwargs["reasoning_effort"] = settings.OPENAI_REASONING_EFFORT

    def _generate() -> str:
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    return openai_call_with_retry(_generate, log_label=log_label)

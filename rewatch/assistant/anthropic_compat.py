"""Anthropic-specific adapters for tool schemas and chat history."""

from __future__ import annotations

import json
from typing import Any

# JSON Schema keys that Anthropic rejects or mishandles in tool input_schema.
_UNSUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "default",
        "additionalProperties",
        "patternProperties",
        "anyOf",
        "allOf",
        "oneOf",
        "$ref",
        "$defs",
        "definitions",
        "minimum",
        "maximum",
        "minLength",
        "maxLength",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "pattern",
        "format",
        "const",
        "minItems",
        "maxItems",
        "uniqueItems",
    }
)


def sanitize_json_schema(schema: Any) -> Any:
    """Return a Claude-compatible JSON Schema subset for tool input_schema."""
    if isinstance(schema, list):
        return [sanitize_json_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema

    cleaned: dict[str, Any] = {}
    for key, value in schema.items():
        if key in _UNSUPPORTED_SCHEMA_KEYS:
            continue
        cleaned[key] = sanitize_json_schema(value)

    if cleaned.get("type") == "object" and "properties" not in cleaned:
        cleaned["properties"] = {}

    return cleaned


def _stringify_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list)):
        return json.dumps(content)
    return str(content)


def _merge_user_contents(left: Any, right: Any) -> Any:
    """Merge consecutive user turns into one Anthropic user message."""
    if isinstance(left, str) and isinstance(right, str):
        if not left:
            return right
        if not right:
            return left
        return f"{left}\n\n{right}"

    def _to_blocks(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [block for block in value if isinstance(block, dict)]
        text = _stringify_content(value).strip()
        return [{"type": "text", "text": text}] if text else []

    merged_blocks = _to_blocks(left) + _to_blocks(right)
    if not merged_blocks:
        return ""
    if len(merged_blocks) == 1 and merged_blocks[0].get("type") == "text":
        return merged_blocks[0]["text"]
    return merged_blocks


def normalize_anthropic_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure alternating roles and Claude-friendly content shapes."""
    normalized: list[dict[str, Any]] = []

    for message in messages:
        role = message.get("role")
        if role not in ("user", "assistant"):
            continue

        content = message.get("content")
        if role == "assistant":
            if isinstance(content, list):
                blocks = [block for block in content if isinstance(block, dict)]
                if not blocks:
                    continue
                if len(blocks) == 1 and blocks[0].get("type") == "text":
                    entry = {"role": "assistant", "content": blocks[0].get("text") or ""}
                else:
                    entry = {"role": "assistant", "content": blocks}
            else:
                text = _stringify_content(content).strip()
                if not text:
                    continue
                entry = {"role": "assistant", "content": text}
        else:
            if isinstance(content, list):
                blocks = [block for block in content if isinstance(block, dict)]
                if not blocks:
                    continue
                entry = {"role": "user", "content": blocks if len(blocks) > 1 or blocks[0].get("type") != "text" else blocks[0].get("text", "")}
            else:
                text = _stringify_content(content).strip()
                if not text:
                    continue
                entry = {"role": "user", "content": text}

        if normalized and normalized[-1]["role"] == entry["role"]:
            normalized[-1]["content"] = _merge_user_contents(normalized[-1]["content"], entry["content"])
        else:
            normalized.append(entry)

    if normalized and normalized[0]["role"] != "user":
        normalized.insert(0, {"role": "user", "content": "Continue the conversation."})

    return normalized

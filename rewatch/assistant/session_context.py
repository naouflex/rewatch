"""Compact prior-turn tool memory for the assistant LLM context."""

from __future__ import annotations

from typing import Any, Optional

MAX_SESSION_CONTEXT_CHARS = 16000
MAX_TURNS = 8
MAX_TOOLS_PER_TURN = 24

_ID_KEYS = (
    "query_id",
    "dashboard_id",
    "visualization_id",
    "alert_id",
    "destination_id",
    "model_id",
    "indexer_id",
    "data_source_id",
    "widget_id",
    "subscription_id",
)


def _format_tool_line(node: dict[str, Any]) -> str:
    tool = node.get("tool") or "tool"
    args = node.get("arguments") or {}
    arg_bits: list[str] = []
    for key in _ID_KEYS:
        if args.get(key) is not None:
            arg_bits.append(f"{key}={args[key]}")
    if args.get("name"):
        arg_bits.append(f"name={args['name']!r}")
    if args.get("q"):
        arg_bits.append(f"q={args['q']!r}")
    arg_text = f" ({', '.join(arg_bits)})" if arg_bits else ""

    if node.get("error"):
        return f"- {tool}{arg_text}: ERROR — {node['error']}"
    summary = (node.get("result_summary") or "").strip()
    if summary:
        return f"- {tool}{arg_text}: {summary}"
    return f"- {tool}{arg_text}"


def _collect_resource_ids(messages: list[dict[str, Any]]) -> dict[str, set[int]]:
    buckets: dict[str, set[int]] = {key: set() for key in _ID_KEYS}
    for message in messages:
        if message.get("role") != "assistant":
            continue
        for node in (message.get("decision_graph") or {}).get("nodes") or []:
            if node.get("type") != "tool":
                continue
            args = node.get("arguments") or {}
            for key in _ID_KEYS:
                value = args.get(key)
                if isinstance(value, int):
                    buckets[key].add(value)
            payload_ids = node.get("resource_ids") or {}
            for key, value in payload_ids.items():
                if key in buckets and isinstance(value, int):
                    buckets[key].add(value)
    return buckets


def format_session_context(messages: list[dict[str, Any]]) -> Optional[str]:
    """Build a compact summary of tool work from prior turns."""
    assistant_turns: list[tuple[str, list[str]]] = []
    turn_index = 0

    for message in messages:
        if message.get("role") == "user":
            turn_index += 1
            continue
        if message.get("role") != "assistant":
            continue

        tool_lines: list[str] = []
        for node in (message.get("decision_graph") or {}).get("nodes") or []:
            if node.get("type") != "tool":
                continue
            tool_lines.append(_format_tool_line(node))
            if len(tool_lines) >= MAX_TOOLS_PER_TURN:
                break

        if tool_lines:
            assistant_turns.append((f"Turn {turn_index}", tool_lines))

    if not assistant_turns:
        return None

    recent_turns = assistant_turns[-MAX_TURNS:]
    lines = [
        "## Prior tool activity (from earlier turns in this thread)",
        "Use these resource IDs and outcomes when the user refers to earlier work "
        '("that dashboard", "the query we created", etc.). Re-fetch with get_* tools if unsure.',
        "",
    ]

    for label, tool_lines in recent_turns:
        lines.append(f"### {label}")
        lines.extend(tool_lines)
        lines.append("")

    resource_ids = _collect_resource_ids(messages)
    id_lines = []
    for key in _ID_KEYS:
        values = sorted(resource_ids[key])
        if values:
            id_lines.append(f"- {key}: {', '.join(str(v) for v in values[-20:])}")
    if id_lines:
        lines.append("### Known resource IDs in this thread")
        lines.extend(id_lines)
        lines.append("")

    text = "\n".join(lines).strip()
    if len(text) > MAX_SESSION_CONTEXT_CHARS:
        text = text[: MAX_SESSION_CONTEXT_CHARS - 3] + "..."
    return text


def extract_resource_ids_from_payload(payload: Any) -> dict[str, int]:
    """Pull stable resource ids from a tool result for decision-graph persistence."""
    if not isinstance(payload, dict):
        return {}
    found: dict[str, int] = {}
    for key in _ID_KEYS:
        value = payload.get(key)
        if isinstance(value, int):
            found[key] = value
    for nested_key in ("query", "dashboard", "alert", "destination", "visualization"):
        nested = payload.get(nested_key)
        if isinstance(nested, dict):
            nested_id = nested.get("id")
            if isinstance(nested_id, int):
                found[f"{nested_key}_id"] = nested_id
    return found
